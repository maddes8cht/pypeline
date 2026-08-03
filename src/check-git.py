import subprocess
import sys
import argparse
import re

def run_git(args: list[str], decode: bool = True):
    """Executes a git command. If decode is True, returns stripped string."""
    # Use shell=False for better argument handling on Windows
    result = subprocess.run(
        ["git"] + args, 
        capture_output=True, 
        text=decode, 
        encoding="utf-8" if decode else None
    )
    return result.stdout.strip() if decode else result.stdout

def get_branch_status() -> tuple[int, int, str]:
    """
    Parses git status to find how many commits we are ahead/behind.
    Returns (ahead_count, behind_count, full_status_output).
    """
    full_status = run_git(["status"])
    short_status = run_git(["status", "-sb"])
    
    ahead = 0
    behind = 0
    
    ahead_match = re.search(r"ahead (\d+)", short_status)
    behind_match = re.search(r"behind (\d+)", short_status)
    
    if ahead_match:
        ahead = int(ahead_match.group(1))
    if behind_match:
        behind = int(behind_match.group(1))
        
    return ahead, behind, full_status

def main():
    # Use RawTextHelpFormatter to keep the custom layout of the description
    parser = argparse.ArgumentParser(
        description=(
            "Advanced Git Log & Status Checker\n\n"
            "Default behavior (no options):\n"
            "  Shows all commits you are ahead or behind your remote.\n"
            "  Always includes +1 commit to show the common ancestor (overlap)."
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("branch", nargs="?", help="Target branch name (default: current)")
    parser.add_argument("-n", "--num", type=int, help="Override number of commits to show")
    parser.add_argument("-s", "--stat", action="store_true", help="Show diffstat for each commit")
    parser.add_argument("--no-status", action="store_true", help="Hide the git status summary at the end")
    args = parser.parse_args()

    # Step 1: Fetch latest info from remote
    run_git(["fetch"])

    # Step 2: Determine status and commit count
    ahead, behind, full_status = get_branch_status()
    
    if args.num:
        count = args.num
    else:
        delta = max(ahead, behind)
        count = delta + 1 if delta > 0 else 5

    # Step 3: Prepare Log Command
    # Removed double %% and added --color=always to ensure colors work through pipe
    log_format = "%C(cyan)%ad%Creset %an  %Cgreen<%ae>%Creset , %ar %C(magenta)%h%n%C(yellow)%s%Creset"
    
    log_args = [
        "log", 
        f"-n{count}", 
        "--color=always",
        "--abbrev-commit", 
        f"--pretty=format:{log_format}"
    ]
    
    if args.stat:
        log_args.append("--stat")
        
    if args.branch:
        log_args.insert(1, args.branch)
    elif not args.num and behind > 0:
        log_args.insert(1, "HEAD..@{u}")

    # Step 4: Output Log
    print("\n--- GIT LOG ---")
    # Using sys.stdout.buffer.write for colored output to handle raw ANSI bytes if needed,
    # but standard print usually works if --color=always is set.
    print(run_git(log_args))

    # Step 5: Output Status Summary
    if not args.no_status:
        print("\n--- BRANCH STATUS ---")
        print(full_status)

if __name__ == "__main__":
    main()
