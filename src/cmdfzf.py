import os
import subprocess
import sys
import argparse
from iterfzf import iterfzf

# Directory containing .cmd files
CMDDIR = r"C:\PAP\cmd"

def get_cmd_files():
    """Return a list of .cmd files in CMDDIR without the .cmd extension."""
    if not os.path.exists(CMDDIR):
        print(f"Error: Directory {CMDDIR} does not exist!")
        return []
    return [os.path.splitext(f)[0] for f in os.listdir(CMDDIR) if f.endswith(".cmd")]

def run_fzf_with_preview(cmd_files, query="", preview_percent=60):
    """Run FZF with preview and return the selected command."""
    try:
        selected = iterfzf(
            cmd_files,
            multi=False,
            query=query,
            preview="cmdlist /c {}",
            bind={
                "ctrl-b": "change-preview(bat --style=plain --color=always --line-range=:50 {}.cmd)",
                "ctrl-c": "change-preview(cmdlist /c {})"
            },
            __extra__=[f"--preview-window=right:{preview_percent}%"]
        )
        return selected
    except KeyboardInterrupt:
        # Handle [Esc] or other interruptions in FZF
        return None
    except Exception as e:
        print(f"Error running FZF: {e}")
        return None

def show_preview(selected_cmd):
    """Run cmdlist /c to show the preview of the selected command."""
    if selected_cmd:
        try:
            result = subprocess.run(
                f"cmdlist /c {selected_cmd}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"Preview error: {result.stderr}", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Error running preview: {e}", file=sys.stderr)

def get_user_edited_command(selected_cmd, keep_preview=False):
    """Prompt the user to add arguments and confirm execution in the terminal."""
    if selected_cmd:
        try:
            # Show the selected command
            print(f"Selected command: {selected_cmd}")
            # Show the preview if --keep is specified
            if keep_preview:
                show_preview(selected_cmd)
                print("  -- Press [Enter] to continue or [Ctrl+C] to cancel --")
            print("Add optional arguments:")
            # Display the base command (non-editable) with a space for arguments
            arguments = input(f"{selected_cmd} ") or ""
            # Construct the full command: base command + .cmd + arguments
            full_cmd = f"{selected_cmd}.cmd {arguments}".strip()
            return full_cmd
        except KeyboardInterrupt:
            return None
    return None

def execute_command(cmd):
    """Execute the given command."""
    if cmd:
        try:
            print(f"Running {cmd}...")
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")

def main():
    # Argument parser
    parser = argparse.ArgumentParser(
        description="FZF-based wrapper for selecting and running .cmd scripts with optional arguments."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="",
        help="Initial query to filter the command list in FZF."
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=60,
        help="Set the preview window size as a percentage (1-100). Default is 60."
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Show the cmdlist preview of the selected command before the argument prompt."
    )

    args = parser.parse_args()

    # Validate preview percentage
    if not 1 <= args.preview <= 100:
        print("Error: --preview must be between 1 and 100.")
        sys.exit(1)

    # Get list of .cmd files
    cmd_files = get_cmd_files()
    if not cmd_files:
        print("No .cmd files found!")
        sys.exit(1)

    # Run FZF to select a command
    selected = run_fzf_with_preview(cmd_files, query=args.query, preview_percent=args.preview)
    if not selected:
        print("Command selection cancelled.")
        sys.exit(1)

    # Prompt user to add arguments and confirm execution
    edited_cmd = get_user_edited_command(selected, keep_preview=args.keep)
    if edited_cmd:
        execute_command(edited_cmd)
    else:
        print("Command execution cancelled.")
        sys.exit(1)

if __name__ == "__main__":
    main()