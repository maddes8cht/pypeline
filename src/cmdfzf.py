import os
import subprocess
import sys
from iterfzf import iterfzf

# Directory containing .cmd files
CMDDIR = r"C:\PAP\cmd"

def get_cmd_files():
    """Return a list of .cmd files in CMDDIR without the .cmd extension."""
    if not os.path.exists(CMDDIR):
        print(f"Error: Directory {CMDDIR} does not exist!")
        return []
    return [os.path.splitext(f)[0] for f in os.listdir(CMDDIR) if f.endswith(".cmd")]

def run_fzf_with_preview(cmd_files, query=""):
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
            __extra__=["--preview-window=right:60%"]
        )
        return selected
    except Exception as e:
        print(f"Error running FZF: {e}")
        return None

def get_user_edited_command(selected_cmd):
    """Prompt the user to edit the selected command in the terminal."""
    if selected_cmd:
        try:
            # Use input() to allow editing in the terminal
            edited_cmd = input(f"Edit command to run [{selected_cmd}.cmd]: ") or f"{selected_cmd}.cmd"
            return edited_cmd
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
    # Get query from command-line arguments (if provided)
    query = sys.argv[1] if len(sys.argv) > 1 else ""

    # Get list of .cmd files
    cmd_files = get_cmd_files()
    if not cmd_files:
        print("No .cmd files found!")
        return

    # Run FZF to select a command
    selected = run_fzf_with_preview(cmd_files, query)
    if not selected:
        print("No command selected.")
        return

    # Debug: Print the selected command
    print(f"Selected command: {selected}")

    # No need to handle --expect=enter since we removed it
    selected_cmd = selected

    # Prompt user to edit the command in the terminal
    edited_cmd = get_user_edited_command(selected_cmd)
    if edited_cmd:
        execute_command(edited_cmd)
    else:
        print("Command execution cancelled.")

if __name__ == "__main__":
    main()