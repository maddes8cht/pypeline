import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestListCmdFiles:
    def test_missing_directory_exits(self, tmp_path):
        from cmdlist import list_cmd_files
        missing = tmp_path / "nonexistent"
        with pytest.raises(SystemExit) as exc:
            list_cmd_files(str(missing))
        assert exc.value.code == 1

    def test_list_cmd_files_basic(self, tmp_path):
        from cmdlist import list_cmd_files
        (tmp_path / "foo.cmd").write_text(":: hello\n@echo off\n", encoding="utf-8")
        (tmp_path / "bar.cmd").write_text(":: world\n@echo off\n", encoding="utf-8")
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_cmd_files(str(tmp_path))
        output = "\n".join(buf)
        assert "foo" in output
        assert "bar" in output

    def test_bare_hides_comments(self, tmp_path):
        from cmdlist import list_cmd_files
        (tmp_path / "foo.cmd").write_text(":: hidden\n@echo off\n", encoding="utf-8")
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_cmd_files(str(tmp_path), show_comments=False)
        output = "\n".join(buf)
        assert "foo" in output
        assert "hidden" not in output

    def test_exeonly_shows_only_exe(self, tmp_path):
        from cmdlist import list_cmd_files
        (tmp_path / "foo.cmd").write_text("@echo off\n", encoding="utf-8")
        (tmp_path / "bar.exe").write_text("MZ", encoding="utf-8")
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_cmd_files(str(tmp_path), show_cmd=False, show_exe=True)
        output = "\n".join(buf)
        assert "bar" in output
        assert "foo" not in output

    def test_cmdonly_shows_only_cmd(self, tmp_path):
        from cmdlist import list_cmd_files
        (tmp_path / "foo.cmd").write_text("@echo off\n", encoding="utf-8")
        (tmp_path / "bar.exe").write_text("MZ", encoding="utf-8")
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_cmd_files(str(tmp_path), show_cmd=True, show_exe=False)
        output = "\n".join(buf)
        assert "foo" in output
        assert "bar" not in output

    def test_bat_file_not_found_exits(self, tmp_path):
        from cmdlist import list_cmd_files
        with pytest.raises(SystemExit):
            list_cmd_files(str(tmp_path), bat_file="nonexistent")

    def test_bat_command_not_found_exits(self, tmp_path):
        from cmdlist import list_cmd_files
        (tmp_path / "foo.cmd").write_text("@echo off\n", encoding="utf-8")
        with patch("subprocess.run", side_effect=FileNotFoundError("bat not found")):
            with pytest.raises(SystemExit):
                list_cmd_files(str(tmp_path), bat_file="foo")

    def test_bat_subprocess_error_exits(self, tmp_path):
        from cmdlist import list_cmd_files
        (tmp_path / "foo.cmd").write_text("@echo off\n", encoding="utf-8")
        with patch("subprocess.run", side_effect=__import__("subprocess").CalledProcessError(1, "bat")):
            with pytest.raises(SystemExit):
                list_cmd_files(str(tmp_path), bat_file="foo")

    def test_comment_extraction_stops_at_non_comment(self, tmp_path):
        from cmdlist import list_cmd_files
        content = ":: visible\nnoncomment\n:: hidden\n"
        (tmp_path / "test.cmd").write_text(content, encoding="utf-8")
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_cmd_files(str(tmp_path))
        output = "\n".join(buf)
        assert "visible" in output
        assert "hidden" not in output

    def test_no_cmd_files(self, tmp_path):
        from cmdlist import list_cmd_files
        (tmp_path / "data.txt").write_text("hello", encoding="utf-8")
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_cmd_files(str(tmp_path))
        output = "\n".join(buf)
        assert output.strip() == ""

    def test_empty_comment_line_prints_blank(self, tmp_path):
        from cmdlist import list_cmd_files
        content = ":: cmd  : foo\n::\n:: help text\n@echo off\n"
        (tmp_path / "foo.cmd").write_text(content, encoding="utf-8")
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_cmd_files(str(tmp_path))
        assert buf[0] == "foo"
        assert any("cmd  : foo" in b for b in buf)
        assert "" in buf               # empty comment line -> print()
        assert any("help text" in b for b in buf)

    def test_blank_line_comment_in_middle(self, tmp_path):
        from cmdlist import list_cmd_files
        content = ":: first\n::\n::second without space\n@echo off\n"
        (tmp_path / "a.cmd").write_text(content, encoding="utf-8")
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_cmd_files(str(tmp_path))
        assert "" in buf
        assert any("second without space" in b for b in buf)

    def test_file_read_error_prints_message(self, tmp_path):
        from cmdlist import list_cmd_files
        import builtins
        bad_path = tmp_path / "bad.cmd"
        bad_path.write_text(":: ok\n@echo off\n", encoding="utf-8")
        real_open = builtins.open

        def selective_open(*args, **kwargs):
            if args and str(args[0]) == str(bad_path):
                raise PermissionError("denied")
            return real_open(*args, **kwargs)

        with (
            patch("builtins.open", side_effect=selective_open),
            patch("builtins.print") as mock_print,
        ):
            list_cmd_files(str(tmp_path))
        calls = [c for c in mock_print.call_args_list if "Error reading" in str(c) and "bad.cmd" in str(c)]
        assert len(calls) > 0, f"Expected error call not found in {mock_print.call_args_list}"


class TestMain:
    def test_default(self, tmp_path):
        (tmp_path / "foo.cmd").write_text("@echo off\n", encoding="utf-8")
        (tmp_path / "bar.cmd").write_text("@echo off\n", encoding="utf-8")
        with (
            patch("sys.argv", ["cmdlist.py", "--cmddir", str(tmp_path)]),
        ):
            from cmdlist import main
            buf = []
            with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
                main()
        output = "\n".join(buf)
        assert "foo" in output
        assert "bar" in output

    def test_bare_hides_comments(self, tmp_path):
        (tmp_path / "test.cmd").write_text(":: comment\n@echo off\n", encoding="utf-8")
        with (
            patch("sys.argv", ["cmdlist.py", "--bare", "--cmddir", str(tmp_path)]),
        ):
            from cmdlist import main
            buf = []
            with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
                main()
        output = "\n".join(buf)
        assert "test" in output
        assert "comment" not in output

    def test_cmdonly_shows_only_cmd(self, tmp_path):
        (tmp_path / "foo.cmd").write_text("@echo off\n", encoding="utf-8")
        (tmp_path / "bar.exe").write_text("MZ", encoding="utf-8")
        with (
            patch("sys.argv", ["cmdlist.py", "--cmdonly", "--cmddir", str(tmp_path)]),
        ):
            from cmdlist import main
            buf = []
            with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
                main()
        output = "\n".join(buf)
        assert "foo" in output
        assert "bar" not in output

    def test_exeonly_shows_only_exe(self, tmp_path):
        (tmp_path / "foo.cmd").write_text("@echo off\n", encoding="utf-8")
        (tmp_path / "bar.exe").write_text("MZ", encoding="utf-8")
        with (
            patch("sys.argv", ["cmdlist.py", "--exeonly", "--cmddir", str(tmp_path)]),
        ):
            from cmdlist import main
            buf = []
            with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
                main()
        output = "\n".join(buf)
        assert "bar" in output
        assert "foo" not in output

    def test_bat_flag_uses_bat(self, tmp_path):
        (tmp_path / "foo.cmd").write_text("@echo off\n", encoding="utf-8")
        with (
            patch("sys.argv", ["cmdlist.py", "--bat", "foo", "--cmddir", str(tmp_path)]),
        ):
            from cmdlist import main
            with patch("subprocess.run") as mock_run:
                main()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0][0] == "bat"

    def test_pattern_filters_output(self, tmp_path):
        (tmp_path / "foo.cmd").write_text("@echo off\n", encoding="utf-8")
        (tmp_path / "foobar.cmd").write_text("@echo off\n", encoding="utf-8")
        (tmp_path / "other.cmd").write_text("@echo off\n", encoding="utf-8")
        with (
            patch("sys.argv", ["cmdlist.py", "foo", "--cmddir", str(tmp_path)]),
        ):
            from cmdlist import main
            buf = []
            with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
                main()
        output = "\n".join(buf)
        assert "foo" in output
        assert "foobar" in output
        assert "other" not in output
