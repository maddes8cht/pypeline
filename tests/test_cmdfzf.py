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
