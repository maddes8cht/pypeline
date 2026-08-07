import subprocess
import sys
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
MODULE_PATH = SRC_DIR / "check-git.py"

spec = importlib.util.spec_from_file_location("check_git", str(MODULE_PATH))
mod = importlib.util.module_from_spec(spec)
sys.modules["check_git"] = mod
spec.loader.exec_module(mod)

run_git = mod.run_git
get_branch_status = mod.get_branch_status
main = mod.main

LOG_FORMAT = (
    "%C(cyan)%ad%Creset %an  %Cgreen<%ae>%Creset , %ar %C(magenta)%h%n%C(yellow)%s%Creset"
)


def _log_call(mock_run):
    """Extract the 'git log' invocation (a list) from a mocked run_git."""
    for call in mock_run.call_args_list:
        args = call.args[0]
        if isinstance(args, list) and args and args[0] == "log":
            return args
    return None


class TestRunGit:
    def test_returns_stripped_stdout_with_utf8(self):
        mock_result = MagicMock()
        mock_result.stdout = "  on branch main  \n"
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = run_git(["status", "-sb"])
        mock_run.assert_called_once_with(
            ["git", "status", "-sb"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert result == "on branch main"

    def test_decode_false_returns_raw_bytes(self):
        mock_result = MagicMock()
        mock_result.stdout = b"raw: \xc3\xa9 line\n"
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = run_git(["status"], decode=False)
        mock_run.assert_called_once_with(
            ["git", "status"],
            capture_output=True,
            text=False,
            encoding=None,
        )
        assert result == b"raw: \xc3\xa9 line\n"

    def test_empty_stdout_returns_empty_string(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            assert run_git(["status"]) == ""

    def test_subprocess_failure_propagates(self):
        error = subprocess.CalledProcessError(128, ["git", "status"])
        with patch("subprocess.run", side_effect=error):
            with pytest.raises(subprocess.CalledProcessError):
                run_git(["status"])


class TestGetBranchStatus:
    def _status(self, short, full):
        with patch("check_git.run_git", side_effect=[full, short]) as mock_run:
            ahead, behind, full_out = get_branch_status()
        mock_run.assert_any_call(["status"])
        mock_run.assert_any_call(["status", "-sb"])
        return ahead, behind, full_out

    def test_ahead_only(self):
        ahead, behind, full_out = self._status(
            "## main...origin/main [ahead 3]",
            "Your branch is ahead of 'origin/main' by 3 commits.",
        )
        assert ahead == 3
        assert behind == 0
        assert full_out == "Your branch is ahead of 'origin/main' by 3 commits."

    def test_behind_only(self):
        ahead, behind, _ = self._status(
            "## main...origin/main [behind 2]", "Your branch is behind by 2 commits."
        )
        assert ahead == 0
        assert behind == 2

    @pytest.mark.parametrize(
        "short,expected",
        [
            ("## main...origin/main [ahead 1, behind 2]", (1, 2)),
            ("## main...origin/main [ahead 7, behind 1]", (7, 1)),
        ],
    )
    def test_ahead_and_behind(self, short, expected):
        ahead, behind, _ = self._status(short, "")
        assert (ahead, behind) == expected

    def test_up_to_date_returns_zeros(self):
        ahead, behind, _ = self._status("## main...origin/main", "On branch main")
        assert (ahead, behind) == (0, 0)

    def test_untracked_files_still_zero_count(self):
        short = "## main...origin/main\n?? untracked.txt\n?? another.tmp"
        ahead, behind, _ = self._status(short, "On branch main")
        assert (ahead, behind) == (0, 0)

    def test_empty_short_status_returns_zeros(self):
        ahead, behind, full_out = self._status("", "On branch main")
        assert (ahead, behind) == (0, 0)
        assert full_out == "On branch main"

    def test_malformed_counts_return_zeros(self):
        ahead, behind, _ = self._status(
            "## main...origin/main [ahead dauntingly, behind secretly]", "x"
        )
        assert (ahead, behind) == (0, 0)

    def test_returns_full_status_verbatim(self):
        _, _, full_out = self._status("## main...", "line1\nline2")
        assert full_out == "line1\nline2"


class TestMain:
    def _run(
        self,
        ahead,
        behind,
        full_status="some status output",
        num=None,
        branch=None,
        stat=False,
        no_status=False,
    ):
        argv = ["check-git.py"]
        if branch is not None:
            argv.append(branch)
        if num is not None:
            argv += ["-n", str(num)]
        if stat:
            argv.append("--stat")
        if no_status:
            argv.append("--no-status")
        with (
            patch("sys.argv", argv),
            patch(
                "check_git.get_branch_status",
                return_value=(ahead, behind, full_status),
            ) as mock_branch,
            patch("check_git.run_git", return_value="LOG OUTPUT") as mock_run,
            patch("builtins.print") as mock_print,
        ):
            main()
        return mock_run, mock_print, mock_branch

    def test_fetch_is_first_git_command(self):
        mock_run, _, _ = self._run(0, 0)
        assert mock_run.call_args_list[0].args[0] == ["fetch"]

    def test_up_to_date_uses_default_count_of_five(self):
        mock_run, _, _ = self._run(0, 0)
        assert _log_call(mock_run) == [
            "log",
            "-n5",
            "--color=always",
            "--abbrev-commit",
            f"--pretty=format:{LOG_FORMAT}",
        ]

    @pytest.mark.parametrize(
        "ahead,behind,expected",
        [
            (3, 1, "-n4"),
            (1, 3, "-n4"),  # behind wins the max
            (4, 2, "-n5"),
        ],
    )
    def test_count_is_max_delta_plus_one(self, ahead, behind, expected):
        mock_run, _, _ = self._run(ahead, behind)
        assert expected in _log_call(mock_run)

    def test_multi_digit_ahead_counts(self):
        mock_run, _, _ = self._run(12, 0)
        assert "-n13" in _log_call(mock_run)

    def test_behind_inserts_upstream_selector(self):
        mock_run, _, _ = self._run(0, 2)
        log_args = _log_call(mock_run)
        assert log_args[1] == "HEAD..@{u}"
        assert "-n3" in log_args

    def test_num_override_wins_over_delta(self):
        mock_run, _, _ = self._run(7, 0, num=2)
        assert "-n2" in _log_call(mock_run)

    def test_num_zero_falls_back_to_delta(self):
        # args.num == 0 is falsy, so the delta path is used
        mock_run, _, _ = self._run(0, 0, num=0)
        assert "-n5" in _log_call(mock_run)

    def test_branch_positional_inserted(self):
        mock_run, _, _ = self._run(0, 0, branch="feature")
        assert _log_call(mock_run)[1] == "feature"

    def test_branch_takes_priority_over_upstream(self):
        mock_run, _, _ = self._run(1, 4, branch="feature")
        log_args = _log_call(mock_run)
        assert log_args[1] == "feature"
        assert "HEAD..@{u}" not in log_args

    def test_stat_flag_appended(self):
        mock_run, _, _ = self._run(0, 0, stat=True)
        assert _log_call(mock_run)[-1] == "--stat"

    def test_status_summary_printed_by_default(self):
        _, mock_print, _ = self._run(0, 0, full_status="BRANCH STATUS TEXT")
        printed = [c.args for c in mock_print.call_args_list]
        assert ("--- BRANCH STATUS ---",) in printed or any(
            "BRANCH STATUS TEXT" in str(c) for c in printed
        )
        assert any("--- GIT LOG ---" in str(c) for c in printed)

    def test_no_status_suppresses_summary(self):
        _, mock_print, _ = self._run(0, 0, full_status="HIDDEN", no_status=True)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "BRANCH STATUS" not in printed
        assert "HIDDEN" not in printed