"""Tests for Pydantic structured output models."""

import json
import pytest
from src.models.schemas import (
    OutdatedPackage,
    CategorizedPackage,
    UpdateType,
    AnalysisResult,
    DetectedCommands,
    AppliedUpdate,
    UpdateResult,
    CategorizedUpdates,
    ErrorAnalysis,
    CommandResult,
    GitOperationResult,
    PRResult,
    IssueResult,
    OrchestratorResult,
    PrerequisiteCheck,
)


class TestOutdatedPackage:
    def test_basic_creation(self):
        pkg = OutdatedPackage(name="react", current="^17.0.2", latest="18.2.0")
        assert pkg.name == "react"
        assert pkg.current_clean == "17.0.2"
        assert pkg.latest_clean == "18.2.0"

    def test_version_prefix_stripping(self):
        pkg = OutdatedPackage(name="lodash", current="~4.17.0", latest=">=4.17.21")
        assert pkg.current_clean == "4.17.0"
        assert pkg.latest_clean == "4.17.21"

    def test_no_prefix(self):
        pkg = OutdatedPackage(name="flask", current="2.0.0", latest="3.0.0")
        assert pkg.current_clean == "2.0.0"
        assert pkg.latest_clean == "3.0.0"


class TestCategorizedPackage:
    def test_major_update(self):
        pkg = CategorizedPackage(
            name="react", current="17.0.2", latest="18.2.0", update_type=UpdateType.MAJOR
        )
        assert pkg.update_type == UpdateType.MAJOR

    def test_serialization(self):
        pkg = CategorizedPackage(
            name="lodash", current="4.17.0", latest="4.18.0", update_type=UpdateType.MINOR
        )
        data = pkg.model_dump()
        assert data["update_type"] == "minor"


class TestAnalysisResult:
    def test_success(self):
        result = AnalysisResult(
            repo_path="/tmp/repo",
            package_manager="npm",
            language="nodejs",
            outdated_count=2,
            outdated_packages=[
                OutdatedPackage(name="react", current="17.0.0", latest="18.0.0"),
                OutdatedPackage(name="lodash", current="4.17.0", latest="4.17.21"),
            ],
        )
        assert result.status == "success"
        assert result.outdated_count == 2
        assert len(result.outdated_packages) == 2

    def test_error(self):
        result = AnalysisResult(
            status="error",
            repo_path="",
            package_manager="",
            error_message="Failed to clone",
        )
        assert result.status == "error"

    def test_json_roundtrip(self):
        result = AnalysisResult(
            repo_path="/tmp/repo",
            package_manager="pip",
            outdated_count=0,
        )
        json_str = result.model_dump_json()
        restored = AnalysisResult.model_validate_json(json_str)
        assert restored.repo_path == "/tmp/repo"


class TestErrorAnalysis:
    def test_high_confidence(self):
        analysis = ErrorAnalysis(
            suspected_package="react",
            confidence="high",
            reasoning="Import error directly references react",
            error_type="import_error",
        )
        assert analysis.suspected_package == "react"
        assert analysis.confidence == "high"

    def test_no_suspect(self):
        analysis = ErrorAnalysis(
            suspected_package=None,
            confidence="low",
            reasoning="Could not determine",
            error_type="other",
        )
        assert analysis.suspected_package is None


class TestCategorizedUpdates:
    def test_counts(self):
        cu = CategorizedUpdates(
            major=[OutdatedPackage(name="a", current="1.0.0", latest="2.0.0")],
            minor=[
                OutdatedPackage(name="b", current="1.0.0", latest="1.1.0"),
                OutdatedPackage(name="c", current="1.0.0", latest="1.2.0"),
            ],
            patch=[],
        )
        assert cu.counts == {"major": 1, "minor": 2, "patch": 0}


class TestOrchestratorResult:
    def test_pr_created(self):
        result = OrchestratorResult(
            status="pr_created",
            url="https://github.com/owner/repo/pull/1",
        )
        assert result.status == "pr_created"
        assert "pull/1" in result.url

    def test_up_to_date(self):
        result = OrchestratorResult(
            status="up_to_date",
            message="All dependencies are up to date.",
        )
        assert result.url is None


class TestDetectedCommands:
    def test_defaults(self):
        cmds = DetectedCommands()
        assert cmds.build is None
        assert cmds.test is None

    def test_npm(self):
        cmds = DetectedCommands(
            package_manager="npm",
            install="npm install",
            build="npm run build",
            test="npm test",
        )
        assert cmds.package_manager == "npm"
