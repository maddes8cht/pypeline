import subprocess
import json
import argparse
import unicodedata
import re
from datetime import datetime, timezone

icon_map = {"open": "🟢", "closed": "🔴"}

def github_anchor(heading: str) -> str:
    """
    Convert a string to a GitHub-style anchor link.
    This function normalizes the string, removes combining characters,
    converts it to lowercase, and replaces spaces and special characters with hyphens.
    """
    heading = unicodedata.normalize('NFKD', heading)
    heading = ''.join(c for c in heading if not unicodedata.combining(c))
    heading = heading.lower()
    heading = re.sub(r'[^\w\s-]', '', heading)
    heading = re.sub(r'\s+', '-', heading)
    heading = re.sub(r'-+', '-', heading)
    return heading.strip('-')

def run_gh_command(args, verbose=False):
    result = subprocess.run(["gh"] + args, capture_output=True, encoding="utf-8")
    if result.returncode != 0:
        if verbose:
            print(f"Error running gh command: {' '.join(args)}")
            print(result.stderr.strip())
        return None
    return result.stdout

def get_issues(repo=None, state="open", verbose=False):
    cmd = [
        "issue", "list", "--state", state,
        "--json", "number,title,state,createdAt,milestone,assignees",
        "--limit", "100"
    ]
    if repo:
        cmd += ["--repo", repo]
    if verbose:
        print(f"Fetching issues (state={state}) from {repo or 'current repo'}...")
    output = run_gh_command(cmd, verbose)
    if output is None:
        return []
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        if verbose:
            print("Failed to parse issues JSON.")
        return []

def get_issue_details(number, repo=None, verbose=False):
    if repo:
        owner_repo = repo
    else:
        owner_repo = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
            capture_output=True, encoding="utf-8"
        ).stdout.strip()
    
    # Main issue data
    issue_cmd = ["api", f"/repos/{owner_repo}/issues/{number}"]
    if verbose:
        print(f"Fetching main data for issue #{number}...")
    issue_data_raw = run_gh_command(issue_cmd, verbose)
    if issue_data_raw is None:
        return None, None
    issue_data = json.loads(issue_data_raw)
    
    # Comments
    comments_cmd = ["api", f"/repos/{owner_repo}/issues/{number}/comments"]
    if verbose:
        print(f"Fetching comments for issue #{number}...")
    comments_data_raw = run_gh_command(comments_cmd, verbose)
    comments_data = json.loads(comments_data_raw) if comments_data_raw else []
    
    return issue_data, comments_data

def build_markdown(
    issues, repo=None, top_link_style="both", color=False,
    include_milestone=True, include_assignee=False, verbose=False
):
    output = []
    
    # Header
    title = f"GitHub Issues for {repo or 'current repository'} ({len(issues)} total)"
    output.append(f"# {title}\n")
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    output.append(f"_Generated: {ts}_\n")
    
    # Overview Table
    output.append("## Overview\n")
    headers = ["Issue", "Title", "State", "Created"]
    if include_milestone:
        headers.append("Milestone")
    if include_assignee:
        headers.append("Assignee(s)")
    output.append("| " + " | ".join(headers) + " |")
    output.append("|-" + "-|" * len(headers))
    
    for issue in issues:
        anchor = github_anchor(f"Issue #{issue['number']}: {issue['title']}")
        state_val = issue['state'].lower()
        state_display = f"{icon_map.get(state_val, '')} {issue['state']}" if color else issue['state']
        
        row = [
            f"[#{issue['number']}](#{anchor})",
            issue['title'],
            state_display,
            issue['createdAt']
        ]
        
        if include_milestone:
            ms = issue.get("milestone", {})
            milestone_title = ms.get("title", "None") if ms else "None"
            row.append(milestone_title)
        
        if include_assignee:
            assignees = issue.get("assignees", [])
            assignee_logins = ", ".join(a["login"] for a in assignees) if assignees else "-"
            row.append(assignee_logins)
        
        output.append("| " + " | ".join(row) + " |")
    
    output.append("\n---\n")
    output.append("## Details\n")
    
    for issue in issues:
        anchor = github_anchor(f"Issue #{issue['number']}: {issue['title']}")
        output.append(f"# Issue #{issue['number']}: {issue['title']}\n")
        
        issue_data, comments_data = get_issue_details(issue["number"], repo=repo, verbose=verbose)
        if issue_data is None:
            output.append("_Failed to fetch issue details._\n")
            continue
        
        state_val = issue_data["state"].lower()
        state_icon = icon_map.get(state_val, "") if color else ""
        output.append(f"**State:** {state_icon} {issue_data['state']}\n")
        output.append(f"**Created at:** {issue_data['created_at']}\n")
        output.append(f"**Author:** {issue_data['user']['login']}\n")
        
        if include_milestone:
            ms = issue_data.get("milestone")
            ms_title = ms["title"] if ms else "None"
            output.append(f"**Milestone:** {ms_title}\n")
        
        if include_assignee:
            assignees = issue_data.get("assignees", [])
            assignee_logins = ", ".join(a["login"] for a in assignees) if assignees else "None"
            output.append(f"**Assignee(s):** {assignee_logins}\n")
        
        output.append("\n**Body:**\n")
        output.append(issue_data.get("body", "_No description provided._") + "\n")
        
        if comments_data:
            output.append("\n**Comments:**\n")
            for comment in comments_data:
                output.append(f"- *{comment['user']['login']}* at {comment['created_at']}:\n")
                output.append(f"  > {comment['body'].replace(chr(10), chr(10)+'  > ')}\n")
        
        if top_link_style != "none":
            parts = []
            if top_link_style in ("icon", "both"):
                parts.append("⬆️")
            if top_link_style in ("text", "both"):
                parts.append("Back to top")
            if parts:
                output.append(f"\n[{' '.join(parts)}](#overview)\n")
        
        output.append("\n---\n")
    
    return "\n".join(output)

def write_markdown(
    issues, filename, repo=None, top_link_style="both", color=False,
    include_milestone=True, include_assignee=False, verbose=False
):
    md = build_markdown(
        issues, repo, top_link_style, color,
        include_milestone, include_assignee, verbose
    )
    with open(filename, "w", encoding="utf-8") as f:
        f.write(md)
    if verbose:
        print(f"Markdown written to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate GitHub Issues as Markdown")
    parser.add_argument("--repo", type=str, help="user/repo (optional)")
    parser.add_argument("--filename", type=str, default="ISSUES.md")
    parser.add_argument("--state", choices=["open","closed","all"], default="open")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--top-link-style", choices=["icon","text","both","none"], default="both")
    parser.add_argument("--color", action="store_true")
    parser.add_argument("--include-milestone", action="store_true", default=True,
                        help="Include milestone in output (default: True)")
    parser.add_argument("--no-milestone", dest="include_milestone", action="store_false",
                        help="Exclude milestone from output")
    parser.add_argument("--include-assignee", action="store_true", default=False,
                        help="Include assignee(s) in output")

    args = parser.parse_args()
    
    issues = get_issues(repo=args.repo, state=args.state, verbose=args.verbose)
    
    if args.dry_run:
        if args.verbose:
            print(build_markdown(
                issues, repo=args.repo, top_link_style=args.top_link_style, color=args.color,
                include_milestone=args.include_milestone, include_assignee=args.include_assignee,
                verbose=args.verbose
            ))
        else:
            for issue in issues:
                parts = [f"#{issue['number']}: {issue['title']} ({issue['state']}, {issue['createdAt']})"]
                if args.include_milestone:
                    ms = issue.get("milestone", {})
                    parts.append(f"Milestone: {ms.get('title', 'None') if ms else 'None'}")
                if args.include_assignee:
                    ass = ", ".join(a["login"] for a in issue.get("assignees", [])) or "-"
                    parts.append(f"Assignee: {ass}")
                print(" | ".join(parts))
    else:
        write_markdown(
            issues, args.filename, repo=args.repo, top_link_style=args.top_link_style, color=args.color,
            include_milestone=args.include_milestone, include_assignee=args.include_assignee,
            verbose=args.verbose
        )