import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog
import argparse

def select_python_script():
    """Open a file dialog to select a Python script."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Python Script",
        filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path if file_path else None

def select_cmd_file():
    """Open a file dialog to select a .cmd file."""
    root = tk.Tk()
    root.withdraw()
    # Start in script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = filedialog.askopenfilename(
        title="Select .cmd File to Update",
        initialdir=script_dir,
        filetypes=[("Command Files", "*.cmd"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path if file_path else None

def select_output_directory():
    """Open a directory dialog to select an output location."""
    root = tk.Tk()
    root.withdraw()
    # Determine the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dir_path = filedialog.askdirectory(
        title="Select Output Directory",
        # Open the dialog in the script directory
        initialdir=script_dir,
        mustexist=True
    )
    root.destroy()
    return dir_path if dir_path else None

def extract_python_and_script_paths_and_env(cmd_file_path):
    """Extract the Python interpreter path, script path and env name from the .cmd file."""
    try:
        with open(cmd_file_path, "r", encoding="utf-8-sig") as f:
            lines = [line.rstrip('\r\n') for line in f]

        if not lines:
            print("Error: .cmd file is empty.")
            sys.exit(1)

        # Find last line (the actual call line)
        last_line = lines[-1].strip()

        print(f"Attempting to extract python call from last line: '{last_line}'")

        # Find line starting with :: env-name:
        old_env_name = None
        for line in lines:
            if line.lower().startswith(':: env-name:'):
                old_env_name = line[len(':: env-name:'):].strip()
                break

        # Expected format: "<interpreter>" "<script>" %*
        if not last_line.lower().endswith(' %*'):
            print(f"Error: Last line does not match expected format: {last_line}")
            sys.exit(1)

        call_part = last_line[:-3].strip()  # remove ' %*'
        if call_part.startswith('"') and call_part.endswith('"'):
            call_parts = call_part[1:-1].split('" "')
        else:
            call_parts = call_part.split(' ')

        if len(call_parts) != 2:
            print(f"Error: Could not split last line into interpreter and script: {call_parts}")
            sys.exit(1)

        python_interpreter = call_parts[0]
        script_path = call_parts[1]

        print(f"Extracted interpreter: '{python_interpreter}'")
        print(f"Extracted script path: '{script_path}'")
        if old_env_name:
            print(f"Extracted old env name: '{old_env_name}'")
        return python_interpreter, script_path, old_env_name

    except IOError as e:
        print(f"Error reading .cmd file {cmd_file_path}: {e}")
        sys.exit(1)

def get_python_interpreter_for_conda_env(env_name):
    """Return the full path to the Python interpreter inside the given conda environment."""
    try:
        result = subprocess.run(
            f'conda run -n "{env_name}" python -c "import sys; print(sys.executable)"',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            check=True
        )
        python_path = result.stdout.strip()
        if not python_path or not os.path.isfile(python_path):
            print(f"Error: Could not find python in conda environment '{env_name}'. Output: {python_path}")
            sys.exit(1)
        return python_path
    except subprocess.CalledProcessError as e:
        print(f"Error running conda to get python path: {e.stderr.strip()}")
        sys.exit(1)

def main():
    # Argument parser
    parser = argparse.ArgumentParser(
        description="Generate or update a Windows .cmd wrapper for a Python script, including its help text as comments."
    )
    parser.add_argument(
        "--update",
        nargs="?",
        default=False,
        metavar="CMD_FILE",
        help="Path to an existing .cmd file to update. If not provided, a file dialog will open."
    )
    parser.add_argument(
        "-n", "--env-name",
        help="Conda environment name to use (overrides existing interpreter)."
    )
    parser.add_argument(
        "--ask",
        action="store_true",
        help="Prompt for output directory if not specified. If not set, use script directory silently."
    )
    parser.add_argument(
        "script_path",
        nargs="?",
        help="Path to the Python script to wrap. Only used if --update is not specified. If not provided, a file dialog will open."
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        help="Directory where the .cmd file will be saved. Only used if --update is not specified. If not provided and --ask is set, a directory dialog will open; otherwise, the script directory is used."
    )

    args = parser.parse_args()
    old_env_name = None

    if args.update is not False:
        # UPDATE MODE
        cmd_file = args.update if isinstance(args.update, str) else select_cmd_file()
        if not cmd_file or not os.path.isfile(cmd_file) or not cmd_file.lower().endswith('.cmd'):
            print("Error: No valid .cmd file selected.")
            sys.exit(1)

        # Extract interpreter, script path, and old env name
        python_interpreter, script_path, old_env_name = extract_python_and_script_paths_and_env(cmd_file)

        # If user provided new env name, replace interpreter
        if args.env_name:
            python_interpreter = get_python_interpreter_for_conda_env(args.env_name)

        # Validate script path
        if not script_path or not os.path.isfile(script_path):
            print(f"Error: Invalid or missing Python script referenced: {script_path}")
            sys.exit(1)

        output_dir = os.path.dirname(cmd_file)
        output_path = cmd_file  # overwrite existing file

    else:
        # CREATE MODE
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Try to detect which positional arg is script vs output dir
        if args.script_path and os.path.isdir(args.script_path) and not args.output_dir:
            # User gave only a dir → open file dialog to select script
            script_path = select_python_script()
            output_dir = args.script_path
        else:
            script_path = args.script_path if args.script_path and os.path.isfile(args.script_path) else select_python_script()
            if args.output_dir and os.path.isdir(args.output_dir):
                output_dir = args.output_dir
            elif args.ask:
                output_dir = select_output_directory()
            else:
                output_dir = script_dir  # Use script directory silently

        if not script_path or not os.path.isfile(script_path):
            print("Error: No valid Python script selected.")
            sys.exit(1)
        if not output_dir or not os.path.isdir(output_dir):
            print("Error: No valid output directory selected.")
            sys.exit(1)

        output_path = os.path.join(
            output_dir,
            f"{os.path.splitext(os.path.basename(script_path))[0]}.cmd"
        )

        if args.env_name:
            python_interpreter = get_python_interpreter_for_conda_env(args.env_name)
        else:
            python_interpreter = "python"

    # Capture help text
    try:
        result = subprocess.run(
            [python_interpreter, script_path, "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        help_output = result.stdout
    except Exception as e:
        print(f"Error capturing help text for {script_path}: {e}")
        sys.exit(1)

    help_lines = help_output.splitlines()
    processed_help = [":: " + line if line.strip() else "::" for line in help_lines]

    # Decide env-name for comment
    if args.env_name:
        env_name_for_comment = args.env_name
    elif old_env_name:
        env_name_for_comment = old_env_name
    else:
        env_name_for_comment = "default"

    # Build content
    content = [
        f":: wrapper for {os.path.basename(script_path)}",
        f":: env-name: {env_name_for_comment}",
        *processed_help,
        "@echo off",
        f'"{python_interpreter}" "{os.path.abspath(script_path)}" %*'
    ]

    # Write file
    try:
        with open(output_path, "w", newline="\r\n") as f:
            f.write("\n".join(content))
        print(f"Successfully created/updated: {os.path.normpath(output_path)}")
    except IOError as e:
        print(f"Error writing file {os.path.normpath(output_path)}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()