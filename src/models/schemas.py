"""
Structured Output Models

Pydantic models for type-safe, validated responses across the agent system.
Inspired by Anthropic SDK's structured_outputs pattern (messages.parse + Pydantic).

These models replace raw JSON string parsing with validated, typed objects.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ── Dependency Analysis Models ──────────────────────────────────


class OutdatedPackage(BaseModel):
    """A single outdated dependency."""

    name: str = Field(description="Package name")
    current: str = Field(description="Currently installed version")
    latest: str = Field(description="Latest available version")

    @property
    def current_clean(self) -> str:
        return self.current.lstrip("^~>=v")

    @property
    def latest_clean(self) -> str:
        return self.latest.lstrip("^~>=v")


class UpdateType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class CategorizedPackage(OutdatedPackage):
    """An outdated package with its update type categorized."""

    update_type: UpdateType = Field(description="Whether this is a major, minor, or patch update")


class AnalysisResult(BaseModel):
    """Result from the dependency analyzer agent."""

    status: Literal["success", "error"] = "success"
    repo_path: str = Field(description="Path to the cloned repository")
    package_manager: str = Field(description="Detected package manager (npm, pip, cargo, etc.)")
    language: Optional[str] = Field(default=None, description="Detected programming language")
    outdated_count: int = Field(default=0, description="Number of outdated packages")
    outdated_packages: List[OutdatedPackage] = Field(default_factory=list)
    from_cache: bool = Field(default=False, description="Whether results came from cache")
    error_message: Optional[str] = Field(default=None, description="Error message if status is error")


class DetectedCommands(BaseModel):
    """Build/test commands detected for a repository."""

    package_manager: Optional[str] = None
    install: Optional[str] = None
    build: Optional[str] = None
    test: Optional[str] = None
    lint: Optional[str] = None
    type_check: Optional[str] = None


# ── Update & Rollback Models ────────────────────────────────────


class AppliedUpdate(BaseModel):
    """A single dependency update that was applied."""

    name: str
    old: str = Field(description="Previous version")
    new: str = Field(description="New version")
    section: Optional[str] = Field(default=None, description="e.g., dependencies, devDependencies")


class UpdateResult(BaseModel):
    """Result from applying dependency updates."""

    status: Literal["success", "error"] = "success"
    updated_content: Optional[str] = Field(default=None, description="Updated file content")
    applied_updates: List[AppliedUpdate] = Field(default_factory=list)
    total_updates: int = 0
    error_message: Optional[str] = None


class CategorizedUpdates(BaseModel):
    """Dependency updates categorized by severity."""

    major: List[OutdatedPackage] = Field(default_factory=list)
    minor: List[OutdatedPackage] = Field(default_factory=list)
    patch: List[OutdatedPackage] = Field(default_factory=list)

    @property
    def counts(self) -> Dict[str, int]:
        return {
            "major": len(self.major),
            "minor": len(self.minor),
            "patch": len(self.patch),
        }


# ── Error Analysis Models ───────────────────────────────────────


class ErrorAnalysis(BaseModel):
    """AI-powered analysis of a build/test error."""

    suspected_package: Optional[str] = Field(
        default=None,
        description="Package name most likely responsible for the error",
    )
    confidence: Literal["high", "medium", "low"] = "low"
    reasoning: str = Field(description="Brief explanation of why this package is suspected")
    error_type: Literal["import_error", "api_change", "type_error", "version_conflict", "other"] = "other"


# ── Build & Test Models ─────────────────────────────────────────


class CommandResult(BaseModel):
    """Result from running a build/test command."""

    status: Literal["success", "error"] = "success"
    command: str
    exit_code: Optional[int] = None
    succeeded: bool = False
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    error_message: Optional[str] = None


# ── Git & GitHub Models ─────────────────────────────────────────


class GitOperationResult(BaseModel):
    """Result from a git operation."""

    status: Literal["success", "error", "no_changes"] = "success"
    operation: str
    branch_name: Optional[str] = None
    files_pushed: Optional[int] = None
    url: Optional[str] = None
    repo_name: Optional[str] = None
    message: Optional[str] = None


class PRResult(BaseModel):
    """Result from creating a GitHub Pull Request."""

    status: Literal["success", "error"] = "success"
    pr_url: Optional[str] = None
    message: Optional[str] = None


class IssueResult(BaseModel):
    """Result from creating a GitHub Issue."""

    status: Literal["success", "error"] = "success"
    issue_url: Optional[str] = None
    message: Optional[str] = None


# ── Final Orchestrator Result ───────────────────────────────────


class OrchestratorResult(BaseModel):
    """Final result from the orchestrator agent."""

    status: Literal["pr_created", "issue_created", "issue_failed", "up_to_date", "error"]
    url: Optional[str] = Field(default=None, description="PR or Issue URL")
    message: Optional[str] = Field(default=None, description="Status message")
    details: Optional[str] = Field(default=None, description="Additional details (e.g., issue body on failure)")


# ── Validation Helpers ──────────────────────────────────────────


class PrerequisiteCheck(BaseModel):
    """Result of prerequisite validation."""

    is_valid: bool
    message: str
    missing: List[str] = Field(default_factory=list, description="List of missing prerequisites")
