#!/usr/bin/env python3
"""
GitHub Issues to Markdown Exporter

This script fetches GitHub issues (open, closed, or all) via the GitHub CLI (`gh`)
and generates a well-formatted Markdown document containing an overview table and
detailed sections for each issue, including bodies and comments.

It supports filtering by repository, state, assignee(s), and milestone(s).
Optional listing modes (`--list-assignees`, `--list-milestones`) help users
discover valid filter values before exporting.

Output can be written to a file or previewed via --dry-run.
"""

import sys
import subprocess
import json
import argparse
import unicodedata
import re
from datetime import datetime, timezone


icon_map = {"open": "🟢", "closed": "🔴"}


def github_anchor(heading: str) -> str:
    """Convert a heading string into a GitHub-compatible anchor slug.

    GitHub automatically generates anchor IDs for headings by:
    - Normalizing Unicode characters (NFKD),
    - Removing diacritics/combining marks,
    - Converting to lowercase,
    - Replacing whitespace and special characters with hyphens,
    - Collapsing multiple hyphens and trimming leading/trailing ones.

    This function replicates that behavior to ensure stable internal links.

    Args:
        heading: The heading text to convert.

    Returns:
        A normalized, hyphen-separated slug suitable for use in a URL fragment.
    """
    heading = unicodedata.normalize('NFKD', heading)
    heading = ''.join(c for c in heading if not unicodedata.combining(c))
    heading = heading.lower()
    heading = re.sub(r'[^\w\s-]', '', heading)
    heading = re.sub(r'\s+', '-', heading)
    heading = re.sub(r'-+', '-', heading)
    return heading.strip('-')


def run_gh_command(args, verbose=False):
    """Execute a GitHub CLI (`gh`) command and return its stdout.

    Args:
        args: List of arguments to pass to `gh` (e.g., ["issue", "list", ...]).
        verbose: If True, print error messages to stderr on failure.

    Returns:
        The stdout output as a string if the command succeeds; None otherwise.
    """
    result = subprocess.run(["gh"] + args, capture_output=True, encoding="utf-8")
    if result.returncode != 0:
        if verbose:
            print(f"Error running gh command: {' '.join(args)}", file=sys.stderr)
            print(result.stderr.strip(), file=sys.stderr)
        return None
    return result.stdout


def get_issues(repo=None, state="open", verbose=False):
    """Fetch a list of GitHub issues using the `gh issue list` command.

    Retrieves up to 100 issues in JSON format, including number, title, state,
    creation time, milestone, and assignees.

    Args:
        repo: Optional "owner/repo" string. If omitted, uses the current repo.
        state: Issue state filter: "open", "closed", or "all".
        verbose: If True, print progress messages to stderr.

    Returns:
        A list of issue dictionaries, or an empty list on failure.
    """
    cmd = [
        "issue", "list", "--state", state,
        "--json", "number,title,state,createdAt,milestone,assignees",
        "--limit", "100"
    ]
    if repo:
        cmd += ["--repo", repo]
    if verbose:
        target = repo or "current repository"
        print(f"Fetching {state} issues from {target}...", file=sys.stderr)
    output = run_gh_command(cmd, verbose)
    if output is None:
        return []
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        if verbose:
            print("Failed to parse issues JSON.", file=sys.stderr)
        return []


def get_issue_details(number, repo=None, verbose=False):
    """Fetch full issue data and its comments from GitHub.

    Uses the GitHub REST API via `gh api` to retrieve the issue body and all comments.

    Args:
        number: The issue number (e.g., 42).
        repo: Optional "owner/repo". If omitted, infers from current context.
        verbose: If True, print progress messages to stderr.

    Returns:
        A tuple (issue_data, comments_data), where each is a dict/list parsed from JSON.
        Returns (None, None) if fetching the main issue fails.
    """
    if repo:
        owner_repo = repo
    else:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
            capture_output=True, encoding="utf-8"
        )
        if result.returncode != 0:
            if verbose:
                print("Failed to determine current repository.", file=sys.stderr)
            return None, None
        owner_repo = result.stdout.strip()

    # Fetch main issue
    issue_cmd = ["api", f"/repos/{owner_repo}/issues/{number}"]
    if verbose:
        print(f"Fetching details for issue #{number}...", file=sys.stderr)
    issue_raw = run_gh_command(issue_cmd, verbose)
    if issue_raw is None:
        return None, None
    issue_data = json.loads(issue_raw)

    # Fetch comments
    comments_cmd = ["api", f"/repos/{owner_repo}/issues/{number}/comments"]
    if verbose:
        print(f"Fetching comments for issue #{number}...", file=sys.stderr)
    comments_raw = run_gh_command(comments_cmd, verbose)
    comments_data = json.loads(comments_raw) if comments_raw else []

    return issue_data, comments_data


def list_assignees(issues, verbose=False):
    """Print all unique assignees (login and optional name) from a list of issues.

    Args:
        issues: List of issue dictionaries (as returned by get_issues).
        verbose: Currently unused; kept for API consistency.
    """
    assignee_set = set()
    for issue in issues:
        for a in issue.get("assignees", []):
            login = a.get("login")
            name = a.get("name") or ""
            if login:
                assignee_set.add((login, name))
    # Sort by login for stability
    for login, name in sorted(assignee_set):
        if name:
            print(f"{login} ({name})")
        else:
            print(login)
    sys.exit(0)


def list_milestones(issues, verbose=False):
    """Print all unique milestone titles from a list of issues.

    Includes both open and closed milestones, as long as they have a title.
    This ensures users can see all valid names for filtering.

    Args:
        issues: List of issue dictionaries.
        verbose: Currently unused; kept for API consistency.
    """
    milestone_titles = set()
    for issue in issues:
        ms = issue.get("milestone")
        if ms and ms.get("title"):
            milestone_titles.add(ms["title"])
    for title in sorted(milestone_titles):
        print(title)
    sys.exit(0)


def build_markdown(
    issues,
    repo=None,
    top_link_style="both",
    color=False,
    include_milestone=True,
    include_assignee=False,
    verbose=False
):
    """Generate a complete Markdown document from a list of GitHub issues.

    The output includes:
    - A title and timestamp,
    - An overview table with links to each issue section,
    - A detailed section per issue (body, metadata, comments),
    - Optional back-to-top links.

    Args:
        issues: List of issue dicts (as returned by get_issues).
        repo: Repository name for display purposes.
        top_link_style: "icon", "text", "both", or "none".
        color: Whether to prefix state with emojis (🟢/🔴).
        include_milestone: Include milestone column and detail.
        include_assignee: Include assignee(s) column and detail.
        verbose: Passed to helper functions for diagnostics.

    Returns:
        A single string containing the full Markdown content.
    """
    output = []

    # Header
    display_repo = repo or "current repository"
    title = f"GitHub Issues for {display_repo} ({len(issues)} total)"
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
            ms = issue.get("milestone") or {}
            milestone_title = ms.get("title", "None")
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
        body = issue_data.get("body") or "_No description provided._"
        output.append(body + "\n")

        if comments_data:
            output.append("\n**Comments:**\n")
            for comment in comments_data:
                user = comment['user']['login']
                created = comment['created_at']
                output.append(f"- *{user}* at {created}:\n")
                indented = "\n".join(f"  > {line}" for line in comment['body'].splitlines())
                output.append(indented + "\n")

        # Back-to-top link
        if top_link_style != "none":
            parts = []
            if top_link_style in ("icon", "both"):
                parts.append("⬆️")
            if top_link_style in ("text", "both"):
                parts.append("Back to top")
            link_text = " ".join(parts)
            output.append(f"\n[{link_text}](#overview)\n")

        output.append("\n---\n")

    return "\n".join(output)


def write_markdown(
    issues,
    filename,
    repo=None,
    top_link_style="both",
    color=False,
    include_milestone=True,
    include_assignee=False,
    verbose=False
):
    """Write the generated Markdown to a file.

    Args:
        issues: List of issue dictionaries.
        filename: Output file path.
        repo: Repository name for display.
        top_link_style: Style of the back-to-top link.
        color: Whether to use state emojis.
        include_milestone: Include milestone info.
        include_assignee: Include assignee info.
        verbose: Print file write confirmation to stderr.
    """
    md = build_markdown(
        issues, repo, top_link_style, color,
        include_milestone, include_assignee, verbose
    )
    with open(filename, "w", encoding="utf-8") as f:
        f.write(md)
    if verbose:
        print(f"Markdown written to {filename}", file=sys.stderr)


def main():
    """Main entry point for the script.

    Parses command-line arguments, fetches issues, and either:
    - lists assignees/milestones and exits, or
    - filters issues, then prints a preview or writes a Markdown report.
    """
    parser = argparse.ArgumentParser(description="Generate GitHub Issues as Markdown")
    parser.add_argument("--repo", type=str, help="Repository in 'owner/repo' format (optional)")
    parser.add_argument("--filename", type=str, default="ISSUES.md", help="Output Markdown filename")
    parser.add_argument("--state", choices=["open", "closed", "all"], default="open",
                        help="Filter issues by state (default: open)")
    parser.add_argument("--dry-run", action="store_true", help="Print issues instead of writing file")
    parser.add_argument("--verbose", action="store_true", help="Enable diagnostic output")
    parser.add_argument("--top-link-style", choices=["icon", "text", "both", "none"], default="both",
                        help="Style of the 'back to top' link in issue details")
    parser.add_argument("--color", action="store_true", help="Use emojis to indicate issue state")
    parser.add_argument("--include-milestone", action="store_true", default=True,
                        help="Include milestone column and metadata (default: enabled)")
    parser.add_argument("--no-milestone", dest="include_milestone", action="store_false",
                        help="Exclude milestone information")
    parser.add_argument("--include-assignee", action="store_true", default=False,
                        help="Include assignee(s) in output")

    # New listing and filtering options
    parser.add_argument("--list-assignees", action="store_true",
                        help="List all unique assignees (login, optional name) and exit")
    parser.add_argument("--list-milestones", action="store_true",
                        help="List all open milestone titles and exit")
    parser.add_argument("-a", "--assignee", action="append",
                        help="Filter by assignee login (can be used multiple times)")
    parser.add_argument("-m", "--milestone", action="append",
                        help="Filter by milestone title (exact, case-sensitive; can be used multiple times)")

    args = parser.parse_args()

    # Fetch all issues first
    issues = get_issues(repo=args.repo, state=args.state, verbose=args.verbose)

    # Handle listing modes first (exit immediately)
    if args.list_assignees:
        list_assignees(issues, verbose=args.verbose)
    if args.list_milestones:
        list_milestones(issues, verbose=args.verbose)

    # Apply filtering by assignee (match on login)
    filtered_issues = issues
    if args.assignee:
        assignee_set = set(args.assignee)
        filtered_issues = [
            issue for issue in filtered_issues
            if any(a.get("login") in assignee_set for a in issue.get("assignees", []))
        ]

    # Apply filtering by milestone (exact title match, case-sensitive)
    if args.milestone:
        milestone_set = set(args.milestone)
        filtered_issues = [
            issue for issue in filtered_issues
            if issue.get("milestone") and issue["milestone"].get("title") in milestone_set
        ]

    # Proceed to output
    if args.dry_run:
        if args.verbose:
            md = build_markdown(
                filtered_issues, repo=args.repo, top_link_style=args.top_link_style, color=args.color,
                include_milestone=args.include_milestone, include_assignee=args.include_assignee,
                verbose=args.verbose
            )
            print(md)
        else:
            for issue in filtered_issues:
                parts = [f"#{issue['number']}: {issue['title']} ({issue['state']}, {issue['createdAt']})"]
                if args.include_milestone:
                    ms = issue.get("milestone") or {}
                    milestone = ms.get("title", "None")
                    parts.append(f"Milestone: {milestone}")
                if args.include_assignee:
                    assignees = ", ".join(a["login"] for a in issue.get("assignees", [])) or "-"
                    parts.append(f"Assignee: {assignees}")
                print(" | ".join(parts))
    else:
        # Minimal feedback for long-running writes
        if not args.verbose and len(filtered_issues) > 5:
            print(
                f"Writing {len(filtered_issues)} issues to {args.filename}... "
                "(use --verbose to see progress)",
                file=sys.stderr
            )
        write_markdown(
            filtered_issues, args.filename, repo=args.repo, top_link_style=args.top_link_style, color=args.color,
            include_milestone=args.include_milestone, include_assignee=args.include_assignee,
            verbose=args.verbose
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)