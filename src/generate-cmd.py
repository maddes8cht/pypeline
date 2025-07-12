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
    file_path = filedialog.askopenfilename(
        title="Select .cmd File to Update",
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


def extract_python_script_path(cmd_file_path):
    """Extract the Python script path from the last line of the .cmd file."""
    try:
        with open(cmd_file_path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        if not lines:
            print("Error: .cmd file is empty.")
            sys.exit(1)
        
        # Get first and last two lines for error reporting
        first_lines = lines[:2] if len(lines) >= 2 else lines
        last_lines = lines[-2:] if len(lines) >= 2 else lines
        last_line = lines[-1].strip()
        
        # ebug: Show the exact input line
        print(f"Attempting to extract path from last line: '{last_line}'")
        
        # Check if the line matches the expected format: python "<path>" %*
        if not last_line.lower().startswith('python ') or not last_line.endswith(' %*'):
            print(f"Error: Last line does not match expected format in .cmd file: {cmd_file_path}")
            print("First two lines of the .cmd file:")
            for i, line in enumerate(first_lines, 1):
                print(f"Line {i}: {line.rstrip()}")
            print("Last two lines of the .cmd file:")
            for i, line in enumerate(last_lines, 1):
                print(f"Line {len(lines)-len(last_lines)+i}: {line.rstrip()}")
            print(f"Raw last line (hex): {last_line.encode('utf-8').hex()}")
            sys.exit(1)
        
        # Extract the path by removing 'python ' (7 chars) and ' %*' (3 chars)
        path_with_quotes = last_line[7:-3]
        # print(f"Extracted path with quotes: '{path_with_quotes}'")
        
        # Remove quotes if present
        if path_with_quotes.startswith('"') and path_with_quotes.endswith('"'):
            script_path = path_with_quotes[1:-1]
        else:
            script_path = path_with_quotes
        
        print(f"Extracted path: '{script_path}'")
        return script_path
    except IOError as e:
        print(f"Error reading .cmd file {cmd_file_path}: {e}")
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
        # If cmd_file is provided via --update, use it; otherwise, open a dialog
        cmd_file = args.update if isinstance(args.update, str) else select_cmd_file()
        if not cmd_file or not os.path.isfile(cmd_file) or not cmd_file.lower().endswith('.cmd'):
            print("Error: No valid .cmd file selected.")
            sys.exit(1)
        
        # Extract the Python script path from the .cmd file
        script_path = extract_python_script_path(cmd_file)
        if not script_path or not os.path.isfile(script_path):
            print(f"Error: Invalid or missing Python script referenced in .cmd file: {script_path}")
            sys.exit(1)
        
        # Output directory is the same as the .cmd file's directory
        output_dir = os.path.dirname(cmd_file)
        output_path = cmd_file  # Overwrite the existing .cmd file
    else:
        # Original mode: request missing paths through dialogs
        script_path = args.script_path if args.script_path else select_python_script()
        output_dir = args.output_dir if args.output_dir else select_output_directory()

        # Validate paths
        if not script_path or not os.path.isfile(script_path):
            print("Error: No valid Python script selected.")
            sys.exit(1)
        if not output_dir or not os.path.isdir(output_dir):
            print("Error: No valid output directory selected.")
            sys.exit(1)

        # Generate output filename
        base_name = os.path.splitext(os.path.basename(script_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.cmd")

    # Capture help text
    try:
        result = subprocess.run(
            [sys.executable, script_path, "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        help_output = result.stdout
    except Exception as e:
        print(f"Error capturing help text for {script_path}: {e}")
        sys.exit(1)

    # Process help text into batch comments
    help_lines = help_output.splitlines()  # Entfernt alle Zeilenenden
    processed_help = [":: " + line if line.strip() else "::" for line in help_lines]

    # Create batch file content
    content = [
        f":: wrapper for {os.path.basename(script_path)}",
        *processed_help,
        "@echo off",
        f'python "{os.path.abspath(script_path)}" %*'
    ]

    # Write to file with Windows line endings
    try:
        with open(output_path, "w", newline="\r\n") as f:
            f.write("\n".join(content)) # Use \n to join lines, will be converted to \r\n on write
        print(f"Successfully created/updated: {output_path}")
    except IOError as e:
        print(f"Error writing file {output_path}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()