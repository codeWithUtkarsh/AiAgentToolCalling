#!/usr/bin/env python3
"""
Dependency Operations - Helper tools for updating and rolling back dependencies
"""

import json
import re
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()


@tool
def apply_all_updates(
    current_content: str, outdated_packages: str, file_type: str
) -> str:
    """
    Apply all dependency updates (including major versions) to a dependency file.

    Args:
        current_content: Current file content
        outdated_packages: JSON string with list of outdated packages
        file_type: Type of file (package.json, requirements.txt, Cargo.toml, etc.)

    Returns:
        JSON with updated content and list of applied updates
    """
    try:
        updates = json.loads(outdated_packages)
        applied_updates = []

        # Normalize: accept both "latest" and "latest_version" keys
        for u in updates:
            if "latest" not in u and "latest_version" in u:
                u["latest"] = u["latest_version"]

        if file_type == "package.json":
            package_data = json.loads(current_content)

            # Update dependencies
            for section in ["dependencies", "devDependencies", "peerDependencies"]:
                if section in package_data:
                    for update in updates:
                        pkg_name = update["name"]
                        new_version = update.get(
                            "latest", update.get("latest_version", "")
                        )

                        if pkg_name in package_data[section]:
                            old_version = package_data[section][pkg_name]
                            # Preserve version prefix (^, ~, etc.)
                            prefix = ""
                            if old_version.startswith("^"):
                                prefix = "^"
                            elif old_version.startswith("~"):
                                prefix = "~"
                            elif old_version.startswith(">="):
                                prefix = ">="

                            package_data[section][pkg_name] = f"{prefix}{new_version}"
                            applied_updates.append(
                                {
                                    "name": pkg_name,
                                    "old": update.get("current", old_version),
                                    "new": new_version,
                                    "section": section,
                                }
                            )

            updated_content = json.dumps(package_data, indent=2)

        elif file_type == "requirements.txt":
            lines = current_content.split("\n")
            updated_lines = []
            updates_dict = {u["name"].lower(): u for u in updates}

            for line in lines:
                stripped = line.strip()

                # Keep comments and empty lines
                if not stripped or stripped.startswith("#"):
                    updated_lines.append(line)
                    continue

                # Parse package name
                pkg_name = None
                if "==" in stripped:
                    pkg_name = stripped.split("==")[0].strip()
                elif ">=" in stripped:
                    pkg_name = stripped.split(">=")[0].strip()
                elif "<=" in stripped:
                    pkg_name = stripped.split("<=")[0].strip()
                else:
                    pkg_name = stripped

                # Update if found
                if pkg_name and pkg_name.lower() in updates_dict:
                    update_info = updates_dict[pkg_name.lower()]
                    new_version = update_info.get(
                        "latest", update_info.get("latest_version", "")
                    )
                    updated_lines.append(f"{pkg_name}=={new_version}")
                    applied_updates.append(
                        {
                            "name": pkg_name,
                            "old": update_info.get("current", "unknown"),
                            "new": new_version,
                        }
                    )
                else:
                    updated_lines.append(line)

            updated_content = "\n".join(updated_lines)

        elif file_type == "Cargo.toml":
            lines = current_content.split("\n")
            updated_lines = []
            updates_dict = {u["name"].lower(): u for u in updates}
            in_dependencies = False

            for line in lines:
                # Track if we're in dependencies section
                if line.strip().startswith("["):
                    in_dependencies = "dependencies" in line.lower()

                # Try to update version
                if in_dependencies and "=" in line and not line.strip().startswith("#"):
                    match = re.match(
                        r'(\s*)([a-zA-Z0-9_-]+)\s*=\s*["\']([^"\']+)["\']', line
                    )
                    if match:
                        indent, pkg_name, current_version = match.groups()
                        if pkg_name.lower() in updates_dict:
                            update_info = updates_dict[pkg_name.lower()]
                            new_version = update_info.get(
                                "latest", update_info.get("latest_version", "")
                            )
                            updated_lines.append(
                                f'{indent}{pkg_name} = "{new_version}"'
                            )
                            applied_updates.append(
                                {
                                    "name": pkg_name,
                                    "old": current_version,
                                    "new": new_version,
                                }
                            )
                            continue

                updated_lines.append(line)

            updated_content = "\n".join(updated_lines)

        else:
            return json.dumps(
                {"status": "error", "message": f"Unsupported file type: {file_type}"}
            )

        return json.dumps(
            {
                "status": "success",
                "updated_content": updated_content,
                "applied_updates": applied_updates,
                "total_updates": len(applied_updates),
            }
        )

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error applying updates: {str(e)}"}
        )


@tool
def rollback_major_update(
    current_content: str, package_name: str, file_type: str, target_version: str
) -> str:
    """
    Rollback a specific package's major version update.

    Args:
        current_content: Current file content
        package_name: Name of the package to rollback
        file_type: Type of file (package.json, requirements.txt, etc.)
        target_version: Version to rollback to

    Returns:
        JSON with updated content after rollback
    """
    try:
        if file_type == "package.json":
            package_data = json.loads(current_content)

            # Find and rollback in all sections
            for section in ["dependencies", "devDependencies", "peerDependencies"]:
                if section in package_data and package_name in package_data[section]:
                    old_value = package_data[section][package_name]
                    prefix = ""
                    if old_value.startswith("^"):
                        prefix = "^"
                    elif old_value.startswith("~"):
                        prefix = "~"

                    package_data[section][package_name] = f"{prefix}{target_version}"

            updated_content = json.dumps(package_data, indent=2)

        elif file_type == "requirements.txt":
            lines = current_content.split("\n")
            updated_lines = []

            for line in lines:
                stripped = line.strip()

                if not stripped or stripped.startswith("#"):
                    updated_lines.append(line)
                    continue

                # Check if this is the package to rollback
                if "==" in stripped:
                    pkg_name = stripped.split("==")[0].strip()
                    if pkg_name.lower() == package_name.lower():
                        updated_lines.append(f"{pkg_name}=={target_version}")
                        continue

                updated_lines.append(line)

            updated_content = "\n".join(updated_lines)

        elif file_type == "Cargo.toml":
            lines = current_content.split("\n")
            updated_lines = []

            for line in lines:
                match = re.match(
                    r"(\s*)("
                    + re.escape(package_name)
                    + r')\s*=\s*["\']([^"\']+)["\']',
                    line,
                )
                if match:
                    indent, pkg_name, _ = match.groups()
                    updated_lines.append(f'{indent}{pkg_name} = "{target_version}"')
                else:
                    updated_lines.append(line)

            updated_content = "\n".join(updated_lines)

        else:
            return json.dumps(
                {"status": "error", "message": f"Unsupported file type: {file_type}"}
            )

        return json.dumps(
            {
                "status": "success",
                "updated_content": updated_content,
                "package": package_name,
                "rolled_back_to": target_version,
            }
        )

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error rolling back: {str(e)}"}
        )


@tool
def parse_error_for_dependency(error_output: str, updated_packages: str) -> str:
    """
    Analyze error output to identify which dependency likely caused the failure.
    Uses AI to intelligently parse error messages.

    Args:
        error_output: Error output from build/test command
        updated_packages: JSON string with list of packages that were updated

    Returns:
        JSON with identified problematic package and confidence level
    """
    try:
        packages = json.loads(updated_packages)
        package_names = [p["name"] for p in packages]
        error_lower = error_output.lower()

        # Heuristic 1: Direct package name match in error output (most common)
        matches = []
        for pkg in package_names:
            pkg_lower = pkg.lower()
            # Count occurrences — more mentions = more likely culprit
            count = error_lower.count(pkg_lower)
            if count > 0:
                matches.append((pkg, count))

        if matches:
            # Sort by frequency, pick the most mentioned package
            matches.sort(key=lambda x: x[1], reverse=True)
            suspected = matches[0][0]

            # Detect error type from common patterns
            error_type = "other"
            if re.search(r"(ImportError|ModuleNotFoundError|cannot find module)", error_output):
                error_type = "import_error"
            elif re.search(r"(TypeError|AttributeError|has no attribute|is not callable)", error_output):
                error_type = "api_change"
            elif re.search(r"(type error|type mismatch|incompatible types)", error_output, re.IGNORECASE):
                error_type = "type_error"

            confidence = "high" if matches[0][1] >= 3 else "medium"
            return json.dumps({
                "status": "success",
                "analysis": {
                    "suspected_package": suspected,
                    "confidence": confidence,
                    "reasoning": f"Package '{suspected}' appears {matches[0][1]} time(s) in error output",
                    "error_type": error_type,
                },
            })

        # Heuristic 2: Check for common import/require patterns mentioning packages
        import_pattern = re.search(
            r"(?:from|import|require\()\s*['\"]?([a-zA-Z0-9_@/.-]+)", error_output
        )
        if import_pattern:
            mentioned = import_pattern.group(1).split("/")[0].lstrip("@")
            for pkg in package_names:
                if mentioned.lower() in pkg.lower() or pkg.lower() in mentioned.lower():
                    return json.dumps({
                        "status": "success",
                        "analysis": {
                            "suspected_package": pkg,
                            "confidence": "medium",
                            "reasoning": f"Import/require of '{mentioned}' found in error, matches package '{pkg}'",
                            "error_type": "import_error",
                        },
                    })

        return json.dumps({
            "status": "success",
            "analysis": {
                "suspected_package": None,
                "confidence": "low",
                "reasoning": "Could not identify specific package from error output",
                "error_type": "unknown",
            },
        })

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error parsing error output: {str(e)}"}
        )


@tool
def categorize_updates(outdated_packages: str) -> str:
    """
    Categorize dependency updates into major, minor, and patch.

    Args:
        outdated_packages: JSON string with outdated packages

    Returns:
        JSON with categorized updates
    """
    try:
        parsed = json.loads(outdated_packages)

        # Handle wrapped formats: {"outdated_dependencies": [...]} or {"packages": [...]}
        if isinstance(parsed, dict):
            for key in ["outdated_dependencies", "outdated_packages", "packages"]:
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                # If it's a dict with no known list key, wrap in a list
                if "name" in parsed:
                    parsed = [parsed]
                else:
                    parsed = []

        packages = parsed

        major_updates = []
        minor_updates = []
        patch_updates = []

        for pkg in packages:
            name = pkg.get("name", "unknown")
            # Accept both "current"/"latest" and "current_version"/"latest_version"
            current = pkg.get("current", pkg.get("current_version", "0.0.0"))
            latest = pkg.get("latest", pkg.get("latest_version", "0.0.0"))
            current = current.lstrip("^~>=v")
            latest = latest.lstrip("^~>=v")

            try:
                curr_parts = current.split(".")
                latest_parts = latest.split(".")

                if len(curr_parts) >= 1 and len(latest_parts) >= 1:
                    if curr_parts[0] != latest_parts[0]:
                        major_updates.append(pkg)
                    elif (
                        len(curr_parts) >= 2
                        and len(latest_parts) >= 2
                        and curr_parts[1] != latest_parts[1]
                    ):
                        minor_updates.append(pkg)
                    else:
                        patch_updates.append(pkg)
                else:
                    minor_updates.append(pkg)
            except (ValueError, IndexError):
                minor_updates.append(pkg)

        return json.dumps(
            {
                "status": "success",
                "major": major_updates,
                "minor": minor_updates,
                "patch": patch_updates,
                "counts": {
                    "major": len(major_updates),
                    "minor": len(minor_updates),
                    "patch": len(patch_updates),
                },
            }
        )

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error categorizing updates: {str(e)}"}
        )


@tool
def get_latest_version_for_major(
    package_name: str, major_version: str, package_manager: str
) -> str:
    """
    Get the latest version within a specific major version.

    Args:
        package_name: Name of the package
        major_version: Major version to stay within (e.g., "17" for React 17.x)
        package_manager: Package manager (npm, pip, cargo)

    Returns:
        JSON with the latest version in that major version line
    """
    try:
        import subprocess

        if package_manager == "npm":
            result = subprocess.run(
                ["npm", "view", package_name, "versions", "--json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                versions = json.loads(result.stdout)
                if not isinstance(versions, list):
                    versions = [versions]

                # Filter for major version
                matching_versions = [
                    v for v in versions if v.split(".")[0] == major_version
                ]

                if matching_versions:
                    # Get the latest
                    latest = matching_versions[-1]
                    return json.dumps(
                        {
                            "status": "success",
                            "package": package_name,
                            "major_version": major_version,
                            "latest_in_major": latest,
                        }
                    )

        # Fallback or other package managers
        return json.dumps(
            {
                "status": "error",
                "message": f"Could not find latest version for {package_name} major {major_version}",
            }
        )

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error getting version info: {str(e)}"}
        )
