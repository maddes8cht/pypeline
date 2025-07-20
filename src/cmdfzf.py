import os
import subprocess
import sys
import argparse
from iterfzf import iterfzf

# Default directory containing .cmd files (script's directory)
CMDDIR = os.path.dirname(os.path.abspath(__file__))

def get_cmd_files(cmddir):
    """Return a list of .cmd files in cmddir without the .cmd extension."""
    if not os.path.exists(cmddir):
        print(f"Error: Directory {cmddir} does not exist!")
        return []
    return [os.path.splitext(f)[0] for f in os.listdir(cmddir) if f.endswith(".cmd")]

def run_fzf_with_preview(cmd_files, query="", preview_percent=60, keep=False):
    """Run FZF with preview and return the selected command."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Define the footer with keybindings and --keep status
    footer_lines = [
        "Ctrl+Q (quit)",
        "Enter (run command, add arguments)"
    ]
    footer = "|".join(footer_lines)  # Use | as a separator for multi-line header
    label = f"--keep: {'On' if keep else 'Off'}, --preview: {preview_percent}%, --cmddir: {CMDDIR}"
    preview_label = "Ctrl+B (bat), Ctrl+C (cmdlist.py), PgUp/PgDn (scroll)"
    try:
        selected = iterfzf(
            cmd_files,
            multi=False,
            query=query,
            preview=f"python {os.path.join(script_dir, 'cmdlist.py')} --cmdonly {{}}",
            bind={
                "ctrl-b": f"change-preview(bat --style=plain --color=always --line-range=:50 {{}}.cmd)",
                "ctrl-c": f"change-preview(python {os.path.join(script_dir, 'cmdlist.py')} --cmdonly {{}})",
                "pgup": "preview-up",  # Bind PgUp to scroll up in preview
                "pgdn": "preview-down"  # Bind PgDown to scroll down in preview
            },
            __extra__=[
                f"--border=bold",
                f"--border-label={label}",
                f"--border-label-pos=3",
                f"--preview-window=right:{preview_percent}%",
                f"--preview-border=bold",
                f"--preview-label={preview_label}",
                #f"--info=inline",
                # f"--header={footer}"
            ]
        )
        return selected
    except KeyboardInterrupt:
        # Handle [Esc] or other interruptions in FZF
        return None
    except Exception as e:
        print(f"Error running FZF: {e}")
        return None

def show_preview(selected_cmd):
    """Run cmdlist.py --cmdonly to show the preview of the selected command."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if selected_cmd:
        try:
            result = subprocess.run(
                f"python {os.path.join(script_dir, 'cmdlist.py')} --cmdonly {selected_cmd}",
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

def get_user_edited_command(selected_cmd, keep_preview=False, cmddir=CMDDIR):
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
    parser.add_argument(
        "--cmddir",
        default=CMDDIR,
        help=f"Directory containing .cmd files. Default is the script's directory: {CMDDIR}."
    )

    args = parser.parse_args()

    # Validate preview percentage
    if not 1 <= args.preview <= 100:
        print("Error: --preview must be between 1 and 100.")
        sys.exit(1)

    # Get list of .cmd files
    cmd_files = get_cmd_files(args.cmddir)
    if not cmd_files:
        print(f"No .cmd files found in {args.cmddir}!")
        sys.exit(1)

    # Run FZF to select a command
    selected = run_fzf_with_preview(cmd_files, query=args.query, preview_percent=args.preview, keep=args.keep)
    if not selected:
        print("Command selection cancelled.")
        sys.exit(1)

    # Prompt user to add arguments and confirm execution
    edited_cmd = get_user_edited_command(selected, keep_preview=args.keep, cmddir=args.cmddir)
    if edited_cmd:
        execute_command(edited_cmd)
    else:
        print("Command execution cancelled.")
        sys.exit(1)
if __name__ == "__main__":
    main()