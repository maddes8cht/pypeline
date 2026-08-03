import sys
from unittest.mock import patch, MagicMock, PropertyMock
import pytest


sys.modules["iterfzf"] = MagicMock()

import cmdfzf


class TestGetCmdFiles:
    def test_missing_dir_returns_empty(self, tmp_path):
        result = cmdfzf.get_cmd_files(str(tmp_path / "nonexistent"))
        assert result == []

    def test_no_cmd_files_returns_empty(self, tmp_path):
        (tmp_path / "foo.txt").write_text("x", encoding="utf-8")
        result = cmdfzf.get_cmd_files(str(tmp_path))
        assert result == []

    def test_finds_cmd_files(self, tmp_path):
        (tmp_path / "foo.cmd").write_text("@echo off\n", encoding="utf-8")
        (tmp_path / "bar.cmd").write_text("@echo off\n", encoding="utf-8")
        (tmp_path / "baz.txt").write_text("x", encoding="utf-8")
        result = cmdfzf.get_cmd_files(str(tmp_path))
        assert sorted(result) == ["bar", "foo"]


class TestRunFzfWithPreview:
    def test_keyboard_interrupt_returns_none(self):
        with patch.object(cmdfzf, "iterfzf", side_effect=KeyboardInterrupt):
            result = cmdfzf.run_fzf_with_preview(["a", "b"])
        assert result is None

    def test_exception_returns_none(self):
        with patch.object(cmdfzf, "iterfzf", side_effect=Exception("fzf crash")):
            result = cmdfzf.run_fzf_with_preview(["a", "b"])
        assert result is None

    def test_selection_returned(self):
        with patch.object(cmdfzf, "iterfzf", return_value="foo"):
            result = cmdfzf.run_fzf_with_preview(["foo", "bar"])
        assert result == "foo"


class TestGetUserEditedCommand:
    def test_none_selected_returns_none(self):
        result = cmdfzf.get_user_edited_command(None)
        assert result is None

    def test_empty_arguments(self):
        with patch("builtins.input", return_value=""):
            result = cmdfzf.get_user_edited_command("myscript")
        assert result == "myscript.cmd"

    def test_with_arguments(self):
        with patch("builtins.input", return_value="--help"):
            result = cmdfzf.get_user_edited_command("myscript")
        assert result == "myscript.cmd --help"

    def test_keyboard_interrupt_returns_none(self):
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = cmdfzf.get_user_edited_command("myscript")
        assert result is None


class TestShowPreview:
    def test_none_selected_does_nothing(self):
        with patch("builtins.print") as mock_print:
            cmdfzf.show_preview(None)
        mock_print.assert_not_called()

    def test_success_prints_stdout(self):
        mock_result = MagicMock()
        mock_result.stdout = "preview content"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.print") as mock_print:
                cmdfzf.show_preview("myscript")
        mock_print.assert_any_call("preview content")

    def test_stderr_printed_as_error(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "something went wrong"
        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.print") as mock_print:
                cmdfzf.show_preview("myscript")
        mock_print.assert_any_call("Preview error: something went wrong", file=sys.stderr)


class TestGetUserEditedCommand:
    def test_with_keep_preview_shows_preview_and_prompt(self):
        with (
            patch("builtins.input", return_value=""),
            patch("builtins.print") as mock_print,
        ):
            with patch.object(cmdfzf, "show_preview") as mock_show:
                result = cmdfzf.get_user_edited_command("myscript", keep_preview=True)
        assert result == "myscript.cmd"
        mock_show.assert_called_once_with("myscript", cmdfzf.CMDDIR)
        mock_print.assert_any_call("  -- Press [Enter] to continue or [Ctrl+C] to cancel --")


class TestExecuteCommand:
    def test_empty_cmd_does_nothing(self):
        with patch("builtins.print") as mock_print:
            cmdfzf.execute_command("")
        mock_print.assert_not_called()

    def test_none_cmd_does_nothing(self):
        with patch("builtins.print") as mock_print:
            cmdfzf.execute_command(None)
        mock_print.assert_not_called()

    def test_success_runs_command(self):
        with patch("subprocess.run") as mock_run:
            cmdfzf.execute_command("myscript.cmd --help")
        mock_run.assert_called_once_with("myscript.cmd --help", shell=True, check=True)

    def test_called_process_error(self):
        with patch("subprocess.run", side_effect=__import__("subprocess").CalledProcessError(1, "cmd")):
            with patch("builtins.print") as mock_print:
                cmdfzf.execute_command("bad.cmd")
        assert any("Error executing command" in str(c) for c in mock_print.call_args_list)


class TestMain:
    def test_default_flow(self):
        with (
            patch("sys.argv", ["cmdfzf.py"]),
            patch.object(cmdfzf, "get_cmd_files", return_value=["foo", "bar"]),
            patch.object(cmdfzf, "run_fzf_with_preview", return_value="foo"),
            patch.object(cmdfzf, "get_user_edited_command", return_value="foo.cmd"),
            patch.object(cmdfzf, "execute_command") as mock_exec,
        ):
            cmdfzf.main()
        mock_exec.assert_called_once_with("foo.cmd")

    def test_no_cmd_files_exits(self):
        with (
            patch("sys.argv", ["cmdfzf.py"]),
            patch.object(cmdfzf, "get_cmd_files", return_value=[]),
            pytest.raises(SystemExit),
        ):
            cmdfzf.main()

    def test_selection_cancelled_exits(self):
        with (
            patch("sys.argv", ["cmdfzf.py"]),
            patch.object(cmdfzf, "get_cmd_files", return_value=["foo"]),
            patch.object(cmdfzf, "run_fzf_with_preview", return_value=None),
            pytest.raises(SystemExit),
        ):
            cmdfzf.main()

    def test_preview_boundary_values_valid(self):
        for val in ["1", "50", "100"]:
            with (
                patch("sys.argv", ["cmdfzf.py", "--preview", val]),
                patch.object(cmdfzf, "get_cmd_files", return_value=["foo"]),
                patch.object(cmdfzf, "run_fzf_with_preview", return_value="foo"),
                patch.object(cmdfzf, "get_user_edited_command", return_value="foo.cmd"),
                patch.object(cmdfzf, "execute_command"),
            ):
                cmdfzf.main()

    def test_preview_out_of_range_exits(self):
        for val in ["0", "101", "150"]:
            with (
                patch("sys.argv", ["cmdfzf.py", "--preview", val]),
                pytest.raises(SystemExit),
            ):
                cmdfzf.main()

    def test_keep_flag_passed_through(self):
        with (
            patch("sys.argv", ["cmdfzf.py", "--keep"]),
            patch.object(cmdfzf, "get_cmd_files", return_value=["foo"]),
            patch.object(cmdfzf, "run_fzf_with_preview",
                         return_value="foo") as mock_fzf,
            patch.object(cmdfzf, "get_user_edited_command", return_value="foo.cmd"),
            patch.object(cmdfzf, "execute_command"),
        ):
            cmdfzf.main()
        mock_fzf.assert_called_once()
        assert mock_fzf.call_args.kwargs["keep"] is True

    def test_cmddir_passed_through(self):
        custom_dir = "C:\\custom\\dir"
        with (
            patch("sys.argv", ["cmdfzf.py", "--cmddir", custom_dir]),
            patch.object(cmdfzf, "get_cmd_files",
                         return_value=["foo"]) as mock_get,
            patch.object(cmdfzf, "run_fzf_with_preview", return_value="foo"),
            patch.object(cmdfzf, "get_user_edited_command", return_value="foo.cmd"),
            patch.object(cmdfzf, "execute_command"),
        ):
            cmdfzf.main()
        mock_get.assert_called_once_with(custom_dir)
