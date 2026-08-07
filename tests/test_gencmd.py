import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest

from gencmd import (
    select_python_script,
    select_cmd_file,
    select_output_directory,
)


class TestExtractPythonAndScriptPathsAndEnv:
    def test_valid_cmd_file(self, sample_cmd_file):
        from gencmd import extract_python_and_script_paths_and_env
        interp, script, env = extract_python_and_script_paths_and_env(str(sample_cmd_file))
        assert interp == "python"
        assert script == "C:\\scripts\\test_script.py"
        assert env is None

    def test_with_env_name(self, sample_cmd_file_with_env):
        from gencmd import extract_python_and_script_paths_and_env
        interp, script, env = extract_python_and_script_paths_and_env(str(sample_cmd_file_with_env))
        assert interp == "C:\\conda\\envs\\myenv\\python.exe"
        assert env == "myenv"

    def test_empty_file_exits(self, tmp_path):
        from gencmd import extract_python_and_script_paths_and_env
        f = tmp_path / "empty.cmd"
        f.write_text("", encoding="utf-8")
        with pytest.raises(SystemExit):
            extract_python_and_script_paths_and_env(str(f))

    def test_missing_trailing_percent_star_exits(self, tmp_path):
        from gencmd import extract_python_and_script_paths_and_env
        f = tmp_path / "bad.cmd"
        f.write_text('"python" "script.py"\n', encoding="utf-8")
        with pytest.raises(SystemExit):
            extract_python_and_script_paths_and_env(str(f))

    def test_malformed_quotes_exits(self, tmp_path):
        from gencmd import extract_python_and_script_paths_and_env
        f = tmp_path / "bad.cmd"
        f.write_text('"python" "extra" "arg" %*\n', encoding="utf-8")
        with pytest.raises(SystemExit):
            extract_python_and_script_paths_and_env(str(f))

    def test_too_many_parts_exits(self, tmp_path):
        from gencmd import extract_python_and_script_paths_and_env
        f = tmp_path / "bad2.cmd"
        f.write_text('python script.py extra %*\n', encoding="utf-8")
        with pytest.raises(SystemExit):
            extract_python_and_script_paths_and_env(str(f))

    def test_io_error_exits(self, tmp_path):
        from gencmd import extract_python_and_script_paths_and_env
        f = tmp_path / "locked.cmd"
        with (
            patch("builtins.open", side_effect=IOError("permission denied")),
            pytest.raises(SystemExit),
        ):
            extract_python_and_script_paths_and_env(str(f))

    def test_non_quoted_format(self, tmp_path):
        from gencmd import extract_python_and_script_paths_and_env
        f = tmp_path / "nonquoted.cmd"
        f.write_text(
            ':: cmd  : test.py\n'
            ':: env  : default\n'
            '@echo off\n'
            'python C:\\scripts\\test.py %*\n',
            encoding="utf-8"
        )
        interp, script, env = extract_python_and_script_paths_and_env(str(f))
        assert interp == "python"
        assert script == "C:\\scripts\\test.py"
        assert env is None


class TestGetPythonInterpreterForCondaEnv:
    def test_valid_conda_env(self):
        from gencmd import get_python_interpreter_for_conda_env
        mock_result = MagicMock()
        mock_result.stdout = "C:\\conda\\envs\\myenv\\python.exe\n"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            with patch("os.path.isfile", return_value=True):
                result = get_python_interpreter_for_conda_env("myenv")
        assert result == "C:\\conda\\envs\\myenv\\python.exe"

    def test_empty_output_exits(self):
        from gencmd import get_python_interpreter_for_conda_env
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(SystemExit):
                get_python_interpreter_for_conda_env("myenv")

    def test_non_existent_path_exits(self):
        from gencmd import get_python_interpreter_for_conda_env
        mock_result = MagicMock()
        mock_result.stdout = "C:\\fake\\python.exe\n"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            with patch("os.path.isfile", return_value=False):
                with pytest.raises(SystemExit):
                    get_python_interpreter_for_conda_env("myenv")

    def test_called_process_error_exits(self):
        from gencmd import get_python_interpreter_for_conda_env
        error = __import__("subprocess").CalledProcessError(1, "conda")
        error.stderr = "conda not found"
        with patch("subprocess.run", side_effect=error):
            with pytest.raises(SystemExit):
                get_python_interpreter_for_conda_env("myenv")


class TestMain:
    def test_create_mode_ask_with_directory_arg_opens_dialog(self, tmp_path):
        from gencmd import main
        script_dir = tmp_path / "scripts"
        script_dir.mkdir()
        sample_script = script_dir / "myscript.py"
        sample_script.write_text('print("hello")', encoding="utf-8")
        with (
            patch("sys.argv", ["gencmd.py", str(tmp_path), "--ask"]),
            patch("gencmd.select_python_script", return_value=str(sample_script)),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="usage: script [--help]\n", returncode=0)
            main()
        expected_cmd = tmp_path / "myscript.cmd"
        assert expected_cmd.exists()
        content = expected_cmd.read_text(encoding="utf-8")
        assert "myscript" in content

    def test_create_mode_default(self, tmp_path, sample_script_file):
        from gencmd import main
        with (
            patch("sys.argv", ["gencmd.py", str(sample_script_file), str(tmp_path)]),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="usage: script [--help]\n", returncode=0)
            main()
        expected_cmd = tmp_path / "myscript.cmd"
        assert expected_cmd.exists()
        content = expected_cmd.read_text(encoding="utf-8")
        assert "myscript" in content
        assert "@echo off" in content

    def test_create_mode_with_env_name(self, tmp_path, sample_script_file):
        from gencmd import main
        mock_conda_result = MagicMock()
        mock_conda_result.stdout = "C:\\conda\\envs\\myenv\\python.exe\n"
        mock_conda_result.stderr = ""
        with (
            patch("sys.argv", ["gencmd.py", str(sample_script_file), str(tmp_path), "-n", "myenv"]),
            patch("subprocess.run", return_value=mock_conda_result) as mock_run,
            patch("os.path.isfile", return_value=True),
        ):
            main()
        expected_cmd = tmp_path / "myscript.cmd"
        content = expected_cmd.read_text(encoding="utf-8")
        assert "C:\\conda\\envs\\myenv\\python.exe" in content

    def test_update_mode(self, sample_cmd_file, sample_script_file):
        from gencmd import main
        with (
            patch("sys.argv", ["gencmd.py", "--update", str(sample_cmd_file), "-n", "myenv"]),
            patch("subprocess.run") as mock_run,
            patch("os.path.isfile", return_value=True),
        ):
            mock_run.return_value = MagicMock(stdout="usage: script\n", returncode=0)
            main()
        content = sample_cmd_file.read_text(encoding="utf-8")
        assert "@echo off" in content

    def test_update_invalid_file_exits(self, tmp_path):
        from gencmd import main
        f = tmp_path / "notacmd.txt"
        f.write_text("x", encoding="utf-8")
        with (
            patch("sys.argv", ["gencmd.py", "--update", str(f)]),
            pytest.raises(SystemExit),
        ):
            main()

    def test_no_script_selected_exits(self):
        from gencmd import main
        with (
            patch("sys.argv", ["gencmd.py"]),
            patch("gencmd.select_python_script", return_value=None),
            pytest.raises(SystemExit),
        ):
            main()

    def test_help_capture_failure_exits(self, tmp_path, sample_script_file):
        from gencmd import main
        with (
            patch("sys.argv", ["gencmd.py", str(sample_script_file), str(tmp_path)]),
            patch("subprocess.run", side_effect=Exception("python not found")),
            pytest.raises(SystemExit),
        ):
            main()

    def test_write_error_exits(self, tmp_path, sample_script_file):
        from gencmd import main
        with (
            patch("sys.argv", ["gencmd.py", str(sample_script_file), str(tmp_path)]),
            patch("subprocess.run") as mock_run,
            patch("builtins.open", side_effect=IOError("disk full")),
            pytest.raises(SystemExit),
        ):
            mock_run.return_value = MagicMock(stdout="help text\n", returncode=0)
            main()

    def test_update_mode_missing_script_exits(self, tmp_path):
        from gencmd import main
        cmd_file = tmp_path / "bad_ref.cmd"
        cmd_file.write_text(
            ':: cmd  : missing_script.py\n'
            ':: env  : default\n'
            '@echo off\n'
            '"python" "C:\\nonexistent\\script.py" %*\n',
            encoding="utf-8"
        )
        with (
            patch("sys.argv", ["gencmd.py", "--update", str(cmd_file)]),
            pytest.raises(SystemExit),
        ):
            main()


class TestSelectFunctions:
    def test_select_python_script_returns_path(self):
        with (
            patch("tkinter.Tk") as mock_tk,
            patch("gencmd.filedialog.askopenfilename", return_value="C:\\scripts\\my.py"),
        ):
            result = select_python_script()
        assert result == "C:\\scripts\\my.py"
        mock_tk.return_value.withdraw.assert_called_once()
        mock_tk.return_value.destroy.assert_called_once()

    def test_select_cmd_file_passes_expected_options(self):
        with (
            patch("tkinter.Tk"),
            patch("gencmd.filedialog.askopenfilename", return_value="C:\\scripts\\x.cmd") as mock_dlg,
        ):
            result = select_cmd_file()
        assert result == "C:\\scripts\\x.cmd"
        assert mock_dlg.call_args.kwargs["title"] == "Select .cmd File to Update"
        assert mock_dlg.call_args.kwargs["filetypes"][0] == ("Command Files", "*.cmd")
        assert mock_dlg.call_args.kwargs["initialdir"]

    def test_select_output_directory_returns_dir(self):
        with (
            patch("tkinter.Tk"),
            patch("gencmd.filedialog.askdirectory", return_value="C:\\out") as mock_dlg,
        ):
            result = select_output_directory()
        assert result == "C:\\out"
        assert mock_dlg.call_args.kwargs["title"] == "Select Output Directory"
        assert mock_dlg.call_args.kwargs["mustexist"] is True

    @pytest.mark.parametrize(
        "func,attr",
        [
            (select_python_script, "askopenfilename"),
            (select_cmd_file, "askopenfilename"),
            (select_output_directory, "askdirectory"),
        ],
    )
    def test_cancel_returns_none(self, func, attr):
        with (
            patch("tkinter.Tk"),
            patch(f"gencmd.filedialog.{attr}", return_value=""),
        ):
            assert func() is None

    def test_select_python_script_raises_on_dialog_failure(self):
        with (
            patch("tkinter.Tk"),
            patch("gencmd.filedialog.askopenfilename", side_effect=Exception("no display")),
            pytest.raises(Exception),
        ):
            select_python_script()


class TestMainDialogsAndEnv:
    def test_create_mode_ask_uses_directory_dialog(self, tmp_path, sample_script_file):
        from gencmd import main
        out_dir = tmp_path / "chosen"
        out_dir.mkdir()
        with (
            patch("sys.argv", ["gencmd.py", str(sample_script_file), "--ask"]),
            patch("gencmd.select_output_directory", return_value=str(out_dir)),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="usage: script\n", returncode=0)
            main()
        assert (out_dir / "myscript.cmd").exists()

    def test_create_mode_ask_with_empty_dialog_exits(self, tmp_path, sample_script_file):
        from gencmd import main
        with (
            patch("sys.argv", ["gencmd.py", str(sample_script_file), "--ask"]),
            patch("gencmd.select_output_directory", return_value=None),
            pytest.raises(SystemExit),
        ):
            main()

    def test_create_mode_directory_argument_uses_script_dialog(self, tmp_path):
        from gencmd import main
        out_dir = tmp_path / "outdir"
        out_dir.mkdir()
        sample_script = tmp_path / "dialog_script.py"
        sample_script.write_text('print("hi")', encoding="utf-8")
        with (
            patch("sys.argv", ["gencmd.py", str(out_dir)]),
            patch("gencmd.select_python_script", return_value=str(sample_script)),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="usage: script\n", returncode=0)
            main()
        assert (out_dir / "dialog_script.cmd").exists()

    def test_update_mode_keeps_old_env_name(self, sample_cmd_file_with_env):
        from gencmd import main
        with (
            patch("sys.argv", ["gencmd.py", "--update", str(sample_cmd_file_with_env)]),
            patch("subprocess.run") as mock_run,
            patch("os.path.isfile", return_value=True),
        ):
            mock_run.return_value = MagicMock(stdout="usage: script\n", returncode=0)
            main()
        content = sample_cmd_file_with_env.read_text(encoding="utf-8")
        assert ":: env  : myenv" in content

    def test_update_mode_with_explicit_env_overrides_old_env_name(self, sample_cmd_file_with_env):
        from gencmd import main
        mock_conda_result = MagicMock()
        mock_conda_result.stdout = "C:\\conda\\envs\\other\\python.exe\n"
        mock_conda_result.stderr = ""
        with (
            patch("sys.argv", ["gencmd.py", "--update", str(sample_cmd_file_with_env), "-n", "other"]),
            patch("subprocess.run", return_value=mock_conda_result) as mock_run,
            patch("os.path.isfile", return_value=True),
        ):
            main()
        content = sample_cmd_file_with_env.read_text(encoding="utf-8")
        assert ":: env  : other" in content

    def test_create_mode_env_comment_defaults_to_default(self, tmp_path, sample_script_file):
        from gencmd import main
        with (
            patch("sys.argv", ["gencmd.py", str(sample_script_file), str(tmp_path)]),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="usage: script\n", returncode=0)
            main()
        content = (tmp_path / "myscript.cmd").read_text(encoding="utf-8")
        assert ":: env  : default" in content
