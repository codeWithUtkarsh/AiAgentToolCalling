#!/usr/bin/env python3
"""
Dependency Analyzer Agent

Analyzes a repository to identify its package manager, locate dependency files,
and identify outdated dependencies.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

from src.config import DEFAULT_LLM_MODEL, language_map as LanguageMap

# Import caching module
from src.services.cache import get_cache


def _get_nested(obj, path, default="N/A"):
    """Get nested value from dict using dot notation (e.g., 'Update.Version')."""
    for key in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return default
        if obj is None:
            return default
    return obj


def _parse_text_outdated(stdout: str, package_manager: str = "") -> list:
    """Parse text-format outdated output into structured list locally (no LLM needed)."""
    results = []
    lines = stdout.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith(("-", "=", "Package", "Name", "#")):
            continue

        # pip: "package  current  latest  type"
        # npm (text): "package  current  wanted  latest  location"
        # gem: "package (newest N, installed M)"
        parts = line.split()
        if len(parts) >= 3:
            name = parts[0]
            # Skip table separator rows
            if all(c in "-|+" for c in name):
                continue
            current = parts[1].strip("()")
            latest = parts[2].strip("()")
            # npm text has 4+ columns: name current wanted latest
            if len(parts) >= 4 and package_manager in ("npm", "yarn", "pnpm"):
                latest = parts[3]
            results.append({"name": name, "current": current, "latest": latest})

    return results


# Load environment variables from .env file
load_dotenv()


@tool
def clone_repository(repo_url: str) -> str:
    """
    Clone a git repository to a temporary directory with caching support.

    Args:
        repo_url: The URL of the git repository to clone (e.g., https://github.com/owner/repo)

    Returns:
        JSON string with status and repository path
    """
    try:
        cache = get_cache()

        # Check if the repository is already cached
        cached_path = cache.get_cached_repository(repo_url)
        if cached_path:
            # Copy cached repo to temp directory
            temp_dir = tempfile.mkdtemp(prefix="dep_analyzer_")
            shutil.copytree(cached_path, temp_dir, dirs_exist_ok=True)

            return json.dumps(
                {
                    "status": "success",
                    "repo_path": temp_dir,
                    "message": f"Repository loaded from cache to {temp_dir}",
                    "from_cache": True,
                }
            )

        # Clone fresh repository
        temp_dir = tempfile.mkdtemp(prefix="dep_analyzer_")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to clone repository: {result.stderr}",
                }
            )

        # Cache the cloned repository
        try:
            cache.cache_repository(repo_url, temp_dir)
        except Exception as cache_error:
            # Don't fail if caching fails
            print(f"Warning: Failed to cache repository: {cache_error}")

        return json.dumps(
            {
                "status": "success",
                "repo_path": temp_dir,
                "message": f"Repository cloned successfully to {temp_dir}",
                "from_cache": False,
            }
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error cloning repository: {str(e)}"}
        )


@tool
def detect_package_manager(repo_path: Path) -> str:
    """
    Detect language, package manager, build command, and outdated dependency command for a repository.

    Returns:
        JSON string with keys:
        - language
        - package_manager
        - build_command
        - outdated_command
        - output_format
        - field_map
        - skip_when
    """
    language_map = LanguageMap.LANGUAGE_PACKAGE_BUILD_MAP
    repo_files = {p.name for p in repo_path.rglob("*") if p.is_file()}

    for language, lang_cfg in language_map.items():
        # 1. Detect language
        detect_files = lang_cfg.get("detect_files", [])
        language_detected = False

        for f in detect_files:
            if f in repo_files or any(Path(p).match(f) for p in repo_files):
                language_detected = True
                break

        if not language_detected:
            continue

        # 2. Detect package manager (lockfile priority)
        for pm_name, pm_cfg in lang_cfg["package_managers"].items():
            lock_files = pm_cfg.get("lock_files", [])

            if not lock_files:
                return json.dumps(
                    {
                        "language": language,
                        "package_manager": pm_name,
                        "build_command": pm_cfg.get("build"),
                        "outdated_command": pm_cfg.get("outdated_cmd"),
                        "output_format": pm_cfg.get("output_format", "text"),
                        "field_map": pm_cfg.get("field_map", {}),
                        "skip_when": pm_cfg.get("skip_when", {}),
                    }
                )

            for lock in lock_files:
                if lock in repo_files:
                    return json.dumps(
                        {
                            "language": language,
                            "package_manager": pm_name,
                            "build_command": pm_cfg.get("build"),
                            "outdated_command": pm_cfg.get("outdated_cmd"),
                            "output_format": pm_cfg.get("output_format", "text"),
                            "field_map": pm_cfg.get("field_map", {}),
                            "skip_when": pm_cfg.get("skip_when", {}),
                        }
                    )

        # 3. Fallback to first package manager
        pm_name, pm_cfg = next(iter(lang_cfg["package_managers"].items()))
        return json.dumps(
            {
                "language": language,
                "package_manager": pm_name,
                "build_command": pm_cfg.get("build"),
                "outdated_command": pm_cfg.get("outdated_cmd"),
                "output_format": pm_cfg.get("output_format", "text"),
                "field_map": pm_cfg.get("field_map", {}),
                "skip_when": pm_cfg.get("skip_when", {}),
            }
        )

    return json.dumps(
        {
            "language": None,
            "package_manager": None,
            "build_command": None,
            "outdated_command": None,
            "output_format": "text",
            "field_map": {},
            "skip_when": {},
        }
    )


@tool
def read_dependency_file(repo_path: str, file_path: str) -> str:
    """
    Read the contents of a dependency file.

    Args:
        repo_path: Path to the repository
        file_path: Relative path to the dependency file

    Returns:
        File contents
    """
    try:
        full_path = os.path.join(repo_path, file_path)
        with open(full_path, "r") as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def check_outdated_dependencies(
    repo_path: str, repo_url: str = "", detected_info: dict = None
) -> str:
    """
    Check outdated dependencies for a repo using the previously detected package manager.

    Args:
        repo_path: Path to the repository
        repo_url: Repository URL for caching (optional)
        detected_info: Dict returned from detect_repo_build_info_json function
                       Should contain: language, package_manager, outdated_command

    Returns:
        JSON string with outdated packages info
    """
    if not detected_info:
        return json.dumps({"status": "error", "message": "Detected info not provided"})

    outdated_cmd = detected_info.get("outdated_command")
    package_manager = detected_info.get("package_manager")
    language = detected_info.get("language")

    if not outdated_cmd:
        return json.dumps(
            {
                "status": "error",
                "message": f"No outdated command defined for {package_manager}",
            }
        )

    repo_path = Path(repo_path).resolve()
    original_dir = os.getcwd()
    os.chdir(repo_path)

    try:
        # Check cache first if repo_url provided
        cache = get_cache()
        if repo_url:
            cached = cache.get_cached_outdated(repo_url)
            if cached:
                cached["from_cache"] = True
                return json.dumps(cached)

        # Run outdated command
        result = subprocess.run(
            outdated_cmd.split(), capture_output=True, text=True, timeout=120
        )

        stdout = result.stdout.strip()
        outdated_list = []

        if stdout:
            output_format = detected_info.get("output_format", "text")
            field_map = detected_info.get("field_map", {})

            try:
                if output_format == "json_dict":
                    data = json.loads(stdout)
                    for pkg_key, info in data.items():
                        name_field = field_map.get("name", "name")
                        outdated_list.append(
                            {
                                "name": pkg_key
                                if name_field == "_key"
                                else info.get(name_field, pkg_key),
                                "current": info.get(
                                    field_map.get("current", "current"), "N/A"
                                ),
                                "latest": info.get(
                                    field_map.get("latest", "latest"), "N/A"
                                ),
                            }
                        )

                elif output_format == "json_array":
                    data = json.loads(stdout)
                    for item in data:
                        outdated_list.append(
                            {
                                "name": item.get(field_map.get("name", "name"), "N/A"),
                                "current": item.get(
                                    field_map.get("current", "current"), "N/A"
                                ),
                                "latest": item.get(
                                    field_map.get("latest", "latest"), "N/A"
                                ),
                            }
                        )

                elif output_format == "ndjson":
                    skip_when = detected_info.get("skip_when", {})
                    decoder = json.JSONDecoder()
                    pos = 0
                    while pos < len(stdout):
                        while pos < len(stdout) and stdout[pos] in " \t\n\r":
                            pos += 1
                        if pos >= len(stdout):
                            break
                        try:
                            obj, end_pos = decoder.raw_decode(stdout, pos)
                            pos = end_pos
                        except json.JSONDecodeError:
                            break

                        # Apply skip rules from language map
                        skip = False
                        for key, val in skip_when.items():
                            if val is None and key not in obj:
                                skip = True
                            elif val is not None and obj.get(key) == val:
                                skip = True
                        if skip:
                            continue

                        outdated_list.append(
                            {
                                "name": _get_nested(obj, field_map.get("name", "name")),
                                "current": _get_nested(
                                    obj, field_map.get("current", "current")
                                ),
                                "latest": _get_nested(
                                    obj, field_map.get("latest", "latest")
                                ),
                            }
                        )

                else:  # "text" format — parse locally instead of sending to LLM
                    outdated_list.extend(_parse_text_outdated(stdout, package_manager))

            except json.JSONDecodeError:
                outdated_list.extend(_parse_text_outdated(stdout, package_manager))

        result_data = {
            "status": "success",
            "language": language,
            "package_manager": package_manager,
            "outdated_count": len(outdated_list),
            "outdated_packages": outdated_list,
            "from_cache": False,
        }

        # Cache results if repo_url provided
        if repo_url:
            try:
                cache.cache_outdated(repo_url, result_data)
            except Exception:
                pass  # ignore caching errors

        return json.dumps(result_data)

    except subprocess.TimeoutExpired:
        return json.dumps({"status": "error", "message": "Outdated command timed out"})
    except Exception as e:
        return json.dumps(
            {
                "status": "error",
                "message": f"Error checking outdated dependencies: {str(e)}",
            }
        )
    finally:
        os.chdir(original_dir)


@tool
def cleanup_repository(repo_path: str) -> str:
    """
    Clean up the cloned repository.

    Args:
        repo_path: Path to the repository to remove

    Returns:
        Confirmation message
    """
    try:
        if os.path.exists(repo_path) and (
            repo_path.startswith("/tmp/dep_analyzer_")
            or repo_path.startswith("/tmp/repo_check_")
        ):
            shutil.rmtree(repo_path)
            return json.dumps(
                {"status": "success", "message": f"Cleaned up {repo_path}"}
            )
        return json.dumps(
            {"status": "error", "message": "Invalid path or path doesn't exist"}
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error during cleanup: {str(e)}"}
        )


def create_dependency_analyzer_agent():
    """
    Create the dependency analyzer agent.
    """
    tools = [
        clone_repository,
        detect_package_manager,
        read_dependency_file,
        check_outdated_dependencies,
    ]

    system_message = """You are a dependency analysis agent. Your job: clone a repo, detect its package manager, and check for outdated dependencies.

Execute these steps IN ORDER. Do NOT skip steps or add extra steps.

STEP 1: Clone the repository using clone_repository.
STEP 2: Detect the package manager using detect_package_manager with the repo_path from step 1.
STEP 3: Check outdated dependencies using check_outdated_dependencies with the repo_path and detected_info from step 2.
STEP 4: Return a SHORT JSON summary. Do NOT write a long report.

IMPORTANT RULES:
- Do NOT clean up or delete the repository. It will be used by the next agent.
- Do NOT call read_dependency_file unless check_outdated_dependencies fails.
- Keep ALL your text responses under 50 words. No explanations, no analysis, no commentary.
- Your final response MUST be ONLY this JSON and nothing else:
{"repo_path": "...", "package_manager": "...", "outdated_count": N, "outdated_packages": [...]}"""

    llm = ChatAnthropic(model=os.getenv("LLM_MODEL_NAME", DEFAULT_LLM_MODEL), temperature=0)

    agent_executor = create_agent(llm, tools, system_prompt=system_message)

    return agent_executor
