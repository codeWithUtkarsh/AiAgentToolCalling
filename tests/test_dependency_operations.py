#!/usr/bin/env python3
"""
Tests for the dependency_operations module.

Tests dependency update application, rollback functionality,
error parsing, and version categorization.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.tools.dependency_ops import (
    apply_all_updates,
    categorize_updates,
    get_latest_version_for_major,
    rollback_major_update,
)


class TestApplyAllUpdates:
    """Test cases for apply_all_updates function."""

    def test_update_package_json_dependencies(self):
        """Test updating dependencies in package.json."""
        current_content = json.dumps(
            {
                "name": "test-project",
                "dependencies": {"lodash": "^4.17.0", "react": "~17.0.0"},
            },
            indent=2,
        )

        outdated_packages = json.dumps(
            [
                {"name": "lodash", "current": "4.17.0", "latest": "4.17.21"},
                {"name": "react", "current": "17.0.0", "latest": "18.2.0"},
            ]
        )

        result = json.loads(
            apply_all_updates.invoke(
                {
                    "current_content": current_content,
                    "outdated_packages": outdated_packages,
                    "file_type": "package.json",
                }
            )
        )

        assert result["status"] == "success"
        assert result["total_updates"] == 2

        updated = json.loads(result["updated_content"])
        assert updated["dependencies"]["lodash"] == "^4.17.21"
        assert updated["dependencies"]["react"] == "~18.2.0"

    def test_update_package_json_dev_dependencies(self):
        """Test updating devDependencies in package.json."""
        current_content = json.dumps(
            {"name": "test-project", "devDependencies": {"jest": "^28.0.0"}}, indent=2
        )

        outdated_packages = json.dumps(
            [{"name": "jest", "current": "28.0.0", "latest": "29.5.0"}]
        )

        result = json.loads(
            apply_all_updates.invoke(
                {
                    "current_content": current_content,
                    "outdated_packages": outdated_packages,
                    "file_type": "package.json",
                }
            )
        )

        assert result["status"] == "success"
        updated = json.loads(result["updated_content"])
        assert updated["devDependencies"]["jest"] == "^29.5.0"

    def test_update_package_json_preserves_prefix(self):
        """Test that version prefixes are preserved."""
        current_content = json.dumps(
            {
                "name": "test",
                "dependencies": {
                    "exact": "1.0.0",
                    "caret": "^1.0.0",
                    "tilde": "~1.0.0",
                    "gte": ">=1.0.0",
                },
            },
            indent=2,
        )

        outdated_packages = json.dumps(
            [
                {"name": "exact", "current": "1.0.0", "latest": "2.0.0"},
                {"name": "caret", "current": "1.0.0", "latest": "2.0.0"},
                {"name": "tilde", "current": "1.0.0", "latest": "2.0.0"},
                {"name": "gte", "current": "1.0.0", "latest": "2.0.0"},
            ]
        )

        result = json.loads(
            apply_all_updates.invoke(
                {
                    "current_content": current_content,
                    "outdated_packages": outdated_packages,
                    "file_type": "package.json",
                }
            )
        )

        assert result["status"] == "success"
        updated = json.loads(result["updated_content"])
        assert updated["dependencies"]["exact"] == "2.0.0"  # No prefix
        assert updated["dependencies"]["caret"] == "^2.0.0"
        assert updated["dependencies"]["tilde"] == "~2.0.0"
        assert updated["dependencies"]["gte"] == ">=2.0.0"

    def test_update_requirements_txt(self):
        """Test updating requirements.txt file."""
        current_content = """# Python dependencies
requests==2.25.0
flask==2.0.0
# End of file
"""

        outdated_packages = json.dumps(
            [
                {"name": "requests", "current": "2.25.0", "latest": "2.31.0"},
                {"name": "flask", "current": "2.0.0", "latest": "3.0.0"},
            ]
        )

        result = json.loads(
            apply_all_updates.invoke(
                {
                    "current_content": current_content,
                    "outdated_packages": outdated_packages,
                    "file_type": "requirements.txt",
                }
            )
        )

        assert result["status"] == "success"
        assert result["total_updates"] == 2
        assert "requests==2.31.0" in result["updated_content"]
        assert "flask==3.0.0" in result["updated_content"]
        # Comments should be preserved
        assert "# Python dependencies" in result["updated_content"]

    def test_update_requirements_txt_case_insensitive(self):
        """Test that package name matching is case-insensitive."""
        current_content = "Flask==2.0.0\n"

        outdated_packages = json.dumps(
            [{"name": "flask", "current": "2.0.0", "latest": "3.0.0"}]
        )

        result = json.loads(
            apply_all_updates.invoke(
                {
                    "current_content": current_content,
                    "outdated_packages": outdated_packages,
                    "file_type": "requirements.txt",
                }
            )
        )

        assert result["status"] == "success"
        assert "Flask==3.0.0" in result["updated_content"]

    def test_update_cargo_toml(self):
        """Test updating Cargo.toml file."""
        current_content = """[package]
name = "test"
version = "0.1.0"

[dependencies]
serde = "1.0.0"
tokio = "1.20.0"
"""

        outdated_packages = json.dumps(
            [
                {"name": "serde", "current": "1.0.0", "latest": "1.0.193"},
                {"name": "tokio", "current": "1.20.0", "latest": "1.35.0"},
            ]
        )

        result = json.loads(
            apply_all_updates.invoke(
                {
                    "current_content": current_content,
                    "outdated_packages": outdated_packages,
                    "file_type": "Cargo.toml",
                }
            )
        )

        assert result["status"] == "success"
        assert 'serde = "1.0.193"' in result["updated_content"]
        assert 'tokio = "1.35.0"' in result["updated_content"]

    def test_unsupported_file_type(self):
        """Test handling of unsupported file types."""
        result = json.loads(
            apply_all_updates.invoke(
                {
                    "current_content": "content",
                    "outdated_packages": "[]",
                    "file_type": "unsupported.xyz",
                }
            )
        )

        assert result["status"] == "error"
        assert "Unsupported file type" in result["message"]

    def test_no_updates_needed(self):
        """Test when no packages match for update."""
        current_content = json.dumps(
            {"name": "test", "dependencies": {"lodash": "^4.17.0"}}, indent=2
        )

        outdated_packages = json.dumps(
            [{"name": "nonexistent", "current": "1.0.0", "latest": "2.0.0"}]
        )

        result = json.loads(
            apply_all_updates.invoke(
                {
                    "current_content": current_content,
                    "outdated_packages": outdated_packages,
                    "file_type": "package.json",
                }
            )
        )

        assert result["status"] == "success"
        assert result["total_updates"] == 0


class TestRollbackMajorUpdate:
    """Test cases for rollback_major_update function."""

    def test_rollback_package_json(self):
        """Test rolling back a package in package.json."""
        current_content = json.dumps(
            {
                "name": "test",
                "dependencies": {"react": "^18.2.0", "lodash": "^4.17.21"},
            },
            indent=2,
        )

        result = json.loads(
            rollback_major_update.invoke(
                {
                    "current_content": current_content,
                    "package_name": "react",
                    "file_type": "package.json",
                    "target_version": "17.0.2",
                }
            )
        )

        assert result["status"] == "success"
        updated = json.loads(result["updated_content"])
        assert updated["dependencies"]["react"] == "^17.0.2"
        assert updated["dependencies"]["lodash"] == "^4.17.21"  # Unchanged

    def test_rollback_requirements_txt(self):
        """Test rolling back a package in requirements.txt."""
        current_content = "requests==2.31.0\nflask==3.0.0\n"

        result = json.loads(
            rollback_major_update.invoke(
                {
                    "current_content": current_content,
                    "package_name": "flask",
                    "file_type": "requirements.txt",
                    "target_version": "2.3.0",
                }
            )
        )

        assert result["status"] == "success"
        assert "flask==2.3.0" in result["updated_content"]
        assert "requests==2.31.0" in result["updated_content"]

    def test_rollback_cargo_toml(self):
        """Test rolling back a package in Cargo.toml."""
        current_content = """[dependencies]
serde = "2.0.0"
tokio = "1.35.0"
"""

        result = json.loads(
            rollback_major_update.invoke(
                {
                    "current_content": current_content,
                    "package_name": "serde",
                    "file_type": "Cargo.toml",
                    "target_version": "1.0.193",
                }
            )
        )

        assert result["status"] == "success"
        assert 'serde = "1.0.193"' in result["updated_content"]

    def test_rollback_preserves_prefix(self):
        """Test that version prefix is preserved during rollback."""
        current_content = json.dumps({"dependencies": {"react": "~18.2.0"}}, indent=2)

        result = json.loads(
            rollback_major_update.invoke(
                {
                    "current_content": current_content,
                    "package_name": "react",
                    "file_type": "package.json",
                    "target_version": "17.0.2",
                }
            )
        )

        assert result["status"] == "success"
        updated = json.loads(result["updated_content"])
        assert updated["dependencies"]["react"] == "~17.0.2"


class TestCategorizeUpdates:
    """Test cases for categorize_updates function."""

    def test_categorize_major_updates(self):
        """Test categorization of major version updates."""
        outdated_packages = json.dumps(
            [
                {"name": "react", "current": "17.0.0", "latest": "18.2.0"},
                {"name": "lodash", "current": "3.0.0", "latest": "4.17.21"},
            ]
        )

        result = json.loads(categorize_updates.invoke(outdated_packages))

        assert result["status"] == "success"
        assert result["counts"]["major"] == 2
        assert result["counts"]["minor"] == 0
        assert result["counts"]["patch"] == 0

    def test_categorize_minor_updates(self):
        """Test categorization of minor version updates."""
        outdated_packages = json.dumps(
            [
                {"name": "react", "current": "18.0.0", "latest": "18.2.0"},
                {"name": "lodash", "current": "4.15.0", "latest": "4.17.21"},
            ]
        )

        result = json.loads(categorize_updates.invoke(outdated_packages))

        assert result["status"] == "success"
        assert result["counts"]["major"] == 0
        assert result["counts"]["minor"] == 2
        assert result["counts"]["patch"] == 0

    def test_categorize_patch_updates(self):
        """Test categorization of patch version updates."""
        outdated_packages = json.dumps(
            [
                {"name": "react", "current": "18.2.0", "latest": "18.2.1"},
                {"name": "lodash", "current": "4.17.20", "latest": "4.17.21"},
            ]
        )

        result = json.loads(categorize_updates.invoke(outdated_packages))

        assert result["status"] == "success"
        assert result["counts"]["major"] == 0
        assert result["counts"]["minor"] == 0
        assert result["counts"]["patch"] == 2

    def test_categorize_mixed_updates(self):
        """Test categorization of mixed update types."""
        outdated_packages = json.dumps(
            [
                {"name": "major", "current": "1.0.0", "latest": "2.0.0"},
                {"name": "minor", "current": "1.0.0", "latest": "1.1.0"},
                {"name": "patch", "current": "1.0.0", "latest": "1.0.1"},
            ]
        )

        result = json.loads(categorize_updates.invoke(outdated_packages))

        assert result["status"] == "success"
        assert result["counts"]["major"] == 1
        assert result["counts"]["minor"] == 1
        assert result["counts"]["patch"] == 1

    def test_categorize_with_version_prefixes(self):
        """Test categorization handles version prefixes."""
        outdated_packages = json.dumps(
            [
                {"name": "react", "current": "^17.0.0", "latest": "18.2.0"},
                {"name": "lodash", "current": "~4.15.0", "latest": "4.17.21"},
            ]
        )

        result = json.loads(categorize_updates.invoke(outdated_packages))

        assert result["status"] == "success"
        assert result["counts"]["major"] == 1  # react 17 -> 18
        assert result["counts"]["minor"] == 1  # lodash 4.15 -> 4.17

    def test_categorize_empty_list(self):
        """Test categorization with empty package list."""
        result = json.loads(categorize_updates.invoke("[]"))

        assert result["status"] == "success"
        assert result["counts"]["major"] == 0
        assert result["counts"]["minor"] == 0
        assert result["counts"]["patch"] == 0


class TestGetLatestVersionForMajor:
    """Test cases for get_latest_version_for_major function."""

    def test_get_latest_npm_version(self):
        """Test getting latest version for npm package."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(["17.0.0", "17.0.1", "17.0.2", "18.0.0", "18.2.0"]),
            )

            result = json.loads(
                get_latest_version_for_major.invoke(
                    {
                        "package_name": "react",
                        "major_version": "17",
                        "package_manager": "npm",
                    }
                )
            )

            assert result["status"] == "success"
            assert result["package"] == "react"
            assert result["major_version"] == "17"
            assert result["latest_in_major"] == "17.0.2"

    def test_get_latest_version_no_matching(self):
        """Test when no versions match the major version."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(["18.0.0", "18.2.0"])
            )

            result = json.loads(
                get_latest_version_for_major.invoke(
                    {
                        "package_name": "react",
                        "major_version": "17",
                        "package_manager": "npm",
                    }
                )
            )

            assert result["status"] == "error"

    def test_get_latest_version_npm_failure(self):
        """Test handling npm command failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="npm ERR! 404"
            )

            result = json.loads(
                get_latest_version_for_major.invoke(
                    {
                        "package_name": "nonexistent-package",
                        "major_version": "1",
                        "package_manager": "npm",
                    }
                )
            )

            assert result["status"] == "error"


class TestParseErrorForDependency:
    """Test cases for parse_error_for_dependency function."""

    def test_parse_error_identifies_package(self):
        """Test that error parsing identifies problematic package via heuristics."""
        from src.tools.dependency_ops import parse_error_for_dependency

        error_output = "Error: Cannot find module 'react'\nImportError: react is not installed"
        updated_packages = json.dumps(
            [
                {"name": "react", "old": "17.0.0", "new": "18.0.0"},
                {"name": "lodash", "old": "4.17.0", "new": "4.17.21"},
            ]
        )

        result = json.loads(
            parse_error_for_dependency.invoke(
                {"error_output": error_output, "updated_packages": updated_packages}
            )
        )

        assert result["status"] == "success"
        assert result["analysis"]["suspected_package"] == "react"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
