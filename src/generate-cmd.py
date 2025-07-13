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


def extract_python_and_script_paths(cmd_file_path):
    """
    Extract the Python interpreter and script path from the last line of the .cmd file.
    """
    try:
        with open(cmd_file_path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        if not lines:
            print("Error: .cmd file is empty.")
            sys.exit(1)
        last_line = lines[-1].strip()
        print(f"Parsing last line: '{last_line}'")
        # Expected format: "<python>" "<script>" %*
        if not last_line.endswith(' %*'):
            print("Error: Last line does not end with ' %*'.")
            sys.exit(1)
        parts = last_line[:-3].strip().split('" "')
        if len(parts) != 2:
            print("Error: Could not parse last line into two quoted paths.")
            sys.exit(1)
        python_path = parts[0].strip('"')
        script_path = parts[1].strip('"')
        print(f"Found python interpreter: {python_path}")
        print(f"Found script path: {script_path}")
        return python_path, script_path
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
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Generate or update a Windows .cmd wrapper for a Python script, including its help text as comments."
    )
    parser.add_argument(
        "--update",
        nargs="?",
        default=False,
        metavar="CMD_FILE",
        help="Path to an existing .cmd file to update with new help text. If not provided, a file dialog will open."
    )
    parser.add_argument(
        "-n", "--env-name",
        metavar="ENV_NAME",
        help="Name of the Conda environment whose Python interpreter should be used."
    )
    parser.add_argument(
        "script_path",
        nargs="?",
        help="Path to the Python script to wrap. Only used if --update is not specified. If not provided, a file dialog will open."
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        help="Directory where the .cmd file will be saved. Only used if --update is not specified. If not provided, a directory dialog will open."
    )

    # Parse arguments
    args = parser.parse_args()

    # Handle update mode
    if args.update is not False:
        cmd_file = args.update if isinstance(args.update, str) else select_cmd_file()
        if not cmd_file or not os.path.isfile(cmd_file) or not cmd_file.lower().endswith('.cmd'):
            print("Error: No valid .cmd file selected.")
            sys.exit(1)

        # Extract the Python interpreter and the script from the existing .cmd file
        old_python_interpreter, script_path = extract_python_and_script_paths(cmd_file)
        if not script_path or not os.path.isfile(script_path):
            print(f"Error: Invalid or missing Python script referenced in .cmd file: {script_path}")
            sys.exit(1)

        # If new Env specified, get new interpreter
        if args.env_name:
            python_interpreter = get_python_interpreter_for_conda_env(args.env_name)
        else:
            python_interpreter = old_python_interpreter

        output_path = cmd_file  # overwrites existing file
    else:
        #  generate-new mode
        # If only a positional argument is specified, check whether file or directory
        if args.script_path and not args.output_dir:
            if os.path.isdir(args.script_path):
                output_dir = args.script_path
                script_path = select_python_script()
            elif os.path.isfile(args.script_path):
                script_path = args.script_path
                output_dir = select_output_directory()
            else:
                print(f"Error: Provided argument '{args.script_path}' is neither a valid file nor a directory.")
                sys.exit(1)
        else:
            script_path = args.script_path if args.script_path else select_python_script()
            output_dir = args.output_dir if args.output_dir else select_output_directory()

        # Validation
        if not script_path or not os.path.isfile(script_path):
            print("Error: No valid Python script selected.")
            sys.exit(1)
        if not output_dir or not os.path.isdir(output_dir):
            print("Error: No valid output directory selected.")
            sys.exit(1)

        # If -n is specified → get the interpreter, otherwise simply "python"
        if args.env_name:
            python_interpreter = get_python_interpreter_for_conda_env(args.env_name)
        else:
            python_interpreter = "python"

        # Target path for the .cmd file
        base_name = os.path.splitext(os.path.basename(script_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.cmd")

    # --help text extract with the selected interpreter
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

    # Convert help text to batch comments
    help_lines = help_output.splitlines()
    processed_help = [":: " + line if line.strip() else "::" for line in help_lines]

    # Contents of the .cmd file
    content = [
        f":: wrapper for {os.path.basename(script_path)}",
        *processed_help,
        "@echo off",
        f'"{python_interpreter}" "{os.path.abspath(script_path)}" %*'
    ]

    # Write with explicit Windows line endings
    try:
        with open(output_path, "w", newline="\r\n") as f:
            f.write("\n".join(content))
        print(f"Successfully created/updated: {output_path}")
    except IOError as e:
        print(f"Error writing file {output_path}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
