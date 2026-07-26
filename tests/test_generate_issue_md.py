import json
import sys
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


SRC_DIR = Path(__file__).resolve().parent.parent / "src"
MODULE_PATH = SRC_DIR / "generate-issue-md.py"

spec = importlib.util.spec_from_file_location("generate_issue_md", str(MODULE_PATH))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

github_anchor = mod.github_anchor
run_gh_command = mod.run_gh_command
get_issues = mod.get_issues
get_issue_details = mod.get_issue_details
build_markdown = mod.build_markdown


SAMPLE_ISSUES = [
    {"number": 1, "title": "Fix bug", "state": "open", "createdAt": "2024-01-01T00:00:00Z",
     "milestone": {"title": "v1.0"}, "assignees": [{"login": "alice"}]},
    {"number": 2, "title": "Add feature", "state": "closed", "createdAt": "2024-01-02T00:00:00Z",
     "milestone": None, "assignees": []},
]


SAMPLE_ISSUE_DETAIL = {
    "state": "open", "created_at": "2024-01-01T00:00:00Z",
    "user": {"login": "alice"}, "body": "Details here.",
    "milestone": {"title": "v1.0"}, "assignees": [{"login": "alice"}],
}

SAMPLE_COMMENTS = [
    {"user": {"login": "bob"}, "created_at": "2024-01-02T00:00:00Z", "body": "Fixed in PR #42"},
]


class TestGithubAnchor:
    def test_basic(self):
        assert github_anchor("Hello World") == "hello-world"

    def test_special_chars_removed(self):
        assert github_anchor("Hello, World! #1") == "hello-world-1"

    def test_unicode_normalized(self):
        assert github_anchor("Café") == "cafe"

    def test_emoji_stripped(self):
        result = github_anchor("Feature: 🚀 launch")
        assert "🚀" not in result
        assert "launch" in result

    def test_multiple_hyphens_collapsed(self):
        assert github_anchor("a---b") == "a-b"

    def test_leading_trailing_hyphens_stripped(self):
        assert github_anchor("--hello--") == "hello"

    def test_accented_chars(self):
        assert github_anchor("Déjà vu") == "deja-vu"


class TestRunGhCommand:
    def test_success_returns_stdout(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        with patch("subprocess.run", return_value=mock_result):
            assert run_gh_command(["issue", "list"]) == "output"

    def test_failure_returns_none(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"
        with patch("subprocess.run", return_value=mock_result):
            assert run_gh_command(["issue", "list"]) is None

    def test_failure_verbose_prints_stderr(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "auth required"
        with (
            patch("subprocess.run", return_value=mock_result),
            patch("builtins.print") as mock_print,
        ):
            result = run_gh_command(["issue", "list"], verbose=True)
            assert result is None
            mock_print.assert_any_call("auth required", file=sys.stderr)


class TestGetIssues:
    def test_returns_parsed_json(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(SAMPLE_ISSUES)
        with patch("subprocess.run", return_value=mock_result):
            issues = get_issues(repo="user/repo", state="open")
        assert len(issues) == 2
        assert issues[0]["number"] == 1

    def test_json_decode_failure_returns_empty(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not json"
        with patch("subprocess.run", return_value=mock_result):
            issues = get_issues(state="open")
        assert issues == []

    def test_gh_failure_returns_empty(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "gh not logged in"
        with patch("subprocess.run", return_value=mock_result):
            issues = get_issues(state="open")
        assert issues == []


class TestGetIssueDetails:
    def test_success(self):
        mock_issue = MagicMock(returncode=0, stdout=json.dumps(SAMPLE_ISSUE_DETAIL))
        mock_comments = MagicMock(returncode=0, stdout=json.dumps(SAMPLE_COMMENTS))
        with (
            patch("subprocess.run", side_effect=[
                MagicMock(returncode=0, stdout="user/repo\n"),
                mock_issue,
                mock_comments,
            ]),
        ):
            issue_data, comments = get_issue_details(1, verbose=False)
        assert issue_data["state"] == "open"
        assert len(comments) == 1

    def test_repo_view_failure(self):
        with patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="no repo")):
            issue_data, comments = get_issue_details(1, verbose=False)
        assert issue_data is None
        assert comments is None

    def test_issue_fetch_failure(self):
        with (
            patch("subprocess.run", side_effect=[
                MagicMock(returncode=0, stdout="user/repo\n"),
                MagicMock(returncode=1, stderr="not found"),
            ]),
        ):
            issue_data, comments = get_issue_details(1)
        assert issue_data is None
        assert comments is None


class TestBuildMarkdown:
    def test_basic_output(self):
        result = build_markdown(SAMPLE_ISSUES, repo="user/repo")
        assert "# GitHub Issues for user/repo" in result
        assert "# Issue #1: Fix bug" in result
        assert "## Overview" in result

    def test_with_color(self):
        result = build_markdown(SAMPLE_ISSUES, color=True)
        assert "🟢" in result or "🔴" in result

    def test_no_milestone(self):
        result = build_markdown(SAMPLE_ISSUES, include_milestone=False)
        assert "Milestone" not in result

    def test_include_assignee(self):
        result = build_markdown(SAMPLE_ISSUES, include_assignee=True)
        assert "Assignee(s)" in result

    def test_top_link_style_none(self):
        result = build_markdown(SAMPLE_ISSUES, top_link_style="none")
        assert "Back to top" not in result

    def test_top_link_style_icon(self):
        result = build_markdown(SAMPLE_ISSUES, top_link_style="icon")
        assert "⬆️" in result

    def test_top_link_style_text(self):
        result = build_markdown(SAMPLE_ISSUES, top_link_style="text")
        assert "Back to top" in result
