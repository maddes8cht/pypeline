import os
import glob
import argparse
import sys

def list_cmd_files(cmddir, pattern="*", show_cmd=True, show_exe=True, show_comments=True):
    """List .cmd and/or .exe files in cmddir matching pattern, with optional comments."""
    if not os.path.exists(cmddir):
        print(f"Error: Directory {cmddir} does not exist!")
        sys.exit(1)

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
        description="List CMD and/or EXE files in a directory and display comments at the beginning of each CMD file."
    )
    parser.add_argument(
        "pattern",
        nargs="?",
        default="*",
        help="Pattern to match files (applies to both .cmd and .exe)."
    )
    parser.add_argument(
        "--nobare",
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
        "--cmddir",
        default=r"C:\PAP\cmd",
        help="Directory containing .cmd and .exe files. Default: C:\\PAP\\cmd."
    )

    args = parser.parse_args()

    # Determine file types to show
    show_cmd = not args.exeonly or args.cmdonly
    show_exe = not args.cmdonly or args.exeonly
    show_comments = not args.nobare

    list_cmd_files(args.cmddir, args.pattern, show_cmd, show_exe, show_comments)

if __name__ == "__main__":
    main()