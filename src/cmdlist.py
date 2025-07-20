import os
import glob
import argparse
import sys
import subprocess

def list_cmd_files(cmddir, pattern="*", show_cmd=True, show_exe=True, show_comments=True, bat_file=None):
    """List .cmd and/or .exe files in cmddir matching pattern, with optional comments, or display a single file with bat."""
    if not os.path.exists(cmddir):
        print(f"Error: Directory {cmddir} does not exist!", file=sys.stderr)
        sys.exit(1)

    if bat_file:
        # Display a single .cmd file using bat
        cmd_path = os.path.join(cmddir, f"{bat_file}.cmd")
        if not os.path.isfile(cmd_path):
            print(f"Error: File {cmd_path} does not exist!", file=sys.stderr)
            sys.exit(1)
        try:
            subprocess.run(["bat", "--style=plain", "--color=always", cmd_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running bat for {cmd_path}: {e}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print("Error: 'bat' command not found. Please ensure bat is installed and in your PATH.", file=sys.stderr)
            sys.exit(1)
        return

    # Normalize pattern for glob
    pattern = f"*{pattern}*" if pattern else "*"

    # List .cmd files
    if show_cmd:
        for cmd_file in glob.glob(os.path.join(cmddir, f"{pattern}.cmd")):
            cmd_name = os.path.splitext(os.path.basename(cmd_file))[0]
            print(cmd_name)
            if show_comments:
                try:
                    with open(cmd_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('::'):
                                comment = line[2:].strip()
                                if comment:  # Skip empty comments
                                    print(f"    {comment}")
                                else:
                                    print()  # Print empty line for empty comment
                            else:
                                break  # Stop at first non-comment line
                except Exception as e:
                    print(f"Error reading {cmd_file}: {e}", file=sys.stderr)

        print()  # Empty line after .cmd files

    # List .exe files
    if show_exe:
        for exe_file in glob.glob(os.path.join(cmddir, f"{pattern}.exe")):
            print(os.path.splitext(os.path.basename(exe_file))[0])

def main():
    parser = argparse.ArgumentParser(
        description="List CMD and/or EXE files in a directory, display comments, or show a single CMD file with bat."
    )
    parser.add_argument(
        "pattern",
        nargs="?",
        default="*",
        help="Pattern to match files (applies to both .cmd and .exe)."
    )
    parser.add_argument(
        "-b",
        "--bare",
        action="store_true",
        help="Hide comments at the beginning of each CMD file (equivalent to /B)."
    )
    parser.add_argument(
        "--cmdonly",
        action="store_true",
        help="List only CMD files (equivalent to /c)."
    )
    parser.add_argument(
        "--exeonly",
        action="store_true",
        help="List only EXE files (equivalent to /e)."
    )
    parser.add_argument(
        "--bat",
        help="Display the specified CMD file using bat."
    )
    parser.add_argument(
        "--cmddir",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Directory containing .cmd and .exe files. Default: the script's directory."
    )

    args = parser.parse_args()

    # Determine file types to show
    show_cmd = not args.exeonly or args.cmdonly
    show_exe = not args.cmdonly or args.exeonly
    show_comments = not args.bare

    list_cmd_files(
        args.cmddir,
        args.pattern,
        show_cmd,
        show_exe,
        show_comments,
        bat_file=args.bat
    )

if __name__ == "__main__":
    main()