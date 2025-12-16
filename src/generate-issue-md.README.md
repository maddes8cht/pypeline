# generate-issue-md.py – GitHub Issues to Markdown Exporter

A lightweight, CLI-first tool that converts GitHub issues from any repository into a beautifully formatted, self-contained Markdown report—complete with overview table, issue details, bodies, comments, and internal navigation.

Perfect for sprint summaries, audit logs, archival snapshots, or sharing progress with stakeholders who prefer readable documents over GitHub UI.

Current date: December 16, 2025

## Motivation

GitHub’s web interface is powerful—but not always ideal for:
- Offline reading,
- Version-controlled documentation,
- Email or chat sharing,
- Generating static snapshots of project state.

While `gh issue list` gives structured data, it lacks context (bodies, comments) and visual hierarchy.  
`generate-issue-md.py` bridges that gap: it pulls everything you need and renders it into a single, clean Markdown file—with zero external dependencies beyond the GitHub CLI.

Born from the need to **document project milestones transparently** and **filter issues by assignee or roadmap** without clicking through dozens of pages.

## Features

- ✅ **Full issue context**: Title, state, author, body, and all comments.
- ✅ **Overview table** with internal links to each issue section.
- ✅ **Filter by assignee** (`-a`) or **milestone** (`-m`)—repeatable for multiple values.
- ✅ **Discovery mode**: `--list-assignees` and `--list-milestones` show valid filter values.
- ✅ **Flexible state selection**: `open`, `closed`, or `all`.
- ✅ **Back-to-top links** (icon, text, or both) for long reports.
- ✅ **Color indicators**: 🟢 for open, 🔴 for closed (optional).
- ✅ **Dry-run preview**: See results without writing files.
- ✅ **Robust CLI**: Graceful interrupt handling (`Ctrl+C`), clear exit codes.
- ✅ **No config needed**: Works out of the box with your `gh` auth.

## Requirements

- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`)
- Python 3.7 or higher (uses only standard library modules)

> 💡 No extra Python packages required!

## Installation

***Standallone install***: Just place `generate-issue-md.py` anywhere in your `PATH`, or run it directly:

```bash
chmod +x generate-issue-md.py  # optional
./generate-issue-md.py --help
```
***Better***: Use it in context of the other `pypeline` scripts and install via gencmd.py, best used as a VSCode build task. For more Information, read this projects [README](../README.md)

## Examples

### Discover available values
```bash
# See all people assigned to open issues
generate-issue-md.py --list-assignees

# See all milestones used in open issues
generate-issue-md.py --list-milestones

# See all milestones ever used (including closed issues)
generate-issue-md.py --list-milestones --state all
```

### Generate filtered reports
```bash
# Export all your open issues
generate-issue-md.py -a maddes8cht --filename my-issues.md

# Export all issues in "v0.4" milestone (exact title match!)
generate-issue-md.py -m "v0.4 – Model Architecture & Training Pipeline"

# Export closed issues assigned to you, include assignee names
generate-issue-md.py --state closed -a maddes8cht --include-assignee

# Preview without writing a file
generate-issue-md.py -m Icebox --dry-run
```

### Advanced usage
```bash
# Export everything with emojis, full details, and back-to-top icons
generate-issue-md.py --state all --color --include-milestone --include-assignee \
                     --top-link-style icon --filename PROJECT_ISSUES.md
```

> 🔍 **Tip**: Always copy-paste milestone titles from `--list-milestones`—matching is **exact and case-sensitive**.

## CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `--repo` | Repository in `owner/repo` format (optional) | `--repo user/project` |
| `--filename` | Output Markdown file | `--filename issues.md` (default) |
| `--state` | Issue state: `open`, `closed`, or `all` | `--state all` |
| `--dry-run` | Print issues instead of writing file | `--dry-run` |
| `--verbose` | Show progress and debug info | `--verbose` |
| `--top-link-style` | Back-to-top style: `icon`, `text`, `both`, `none` | `--top-link-style both` |
| `--color` | Use 🟢/🔴 emojis for state | `--color` |
| `--include-milestone` | Include milestone column (default: on) | `--no-milestone` to disable |
| `--include-assignee` | Include assignee(s) column | `--include-assignee` |
| `--list-assignees` | List unique assignees and exit | `--list-assignees` |
| `--list-milestones` | List milestone titles and exit | `--list-milestones` |
| `-a`, `--assignee` | Filter by assignee login (repeatable) | `-a alice -a bob` |
| `-m`, `--milestone` | Filter by milestone title (exact, repeatable) | `-m "v1.0"` |

## Exit Codes

- `0`: Success
- `130`: Interrupted by user (`Ctrl+C`)
- Non-zero: Command or parsing error (e.g., `gh` not found)

## Limitations / Known Constraints

- **Issue limit:**  
  This script currently fetches up to **100 issues**, matching the explicit `--limit 100` used by `gh issue list`.  
  Repositories with more issues will require extending the script to paginate or batch requests.

- **Exact milestone matching:**  
  Milestone filters (`-m / --milestone`) require an **exact, case-sensitive title match**.  
  Always use `--list-milestones` and copy-paste titles to avoid mismatches.

- **Large repositories:**  
  For repositories with many issues and comments, generation may take noticeable time due to multiple GitHub API calls.

- **GitHub CLI dependency:**  
  The script relies entirely on `gh` for authentication and API access.  
  If `gh auth login` is not set up correctly, the script will fail gracefully.

## Mini FAQ
### Why not just use `gh issue list`?

`gh issue list` is excellent for quick terminal views, but it does not:
- include full issue bodies,
- include comments,
- generate navigable documents,
- produce archival snapshots.

This tool complements `gh`, it does not replace it.

### Why not use the GitHub API directly?

You could—but then you would need to manage authentication, pagination, rate limits, and API versions yourself.  
This script deliberately builds on the GitHub CLI (`gh`) to reuse its battle-tested auth flow and configuration, keeping the tool simple, robust, and dependency-free.

### Why Markdown instead of JSON or CSV?

Markdown strikes a balance between structure and readability.  
It can be:
- read directly by humans,
- version-controlled,
- rendered nicely on GitHub and in editors like VS Code,
- pasted into chat tools or LLM prompts without losing context.

JSON is better for machines—Markdown is better for understanding.


## Design Philosophy

- **User-first discovery**: You should never guess filter values—`--list-*` shows exactly what’s available.
- **Safe by default**: No file is overwritten without explicit intent.
- **Transparent progress**: Even without `--verbose`, you get feedback on long operations.
- **Consistent with `gh`**: Options like `--state`, `--repo` mirror GitHub CLI behavior.
- **Minimal but complete**: No bloat, but all essential context (comments!) included.

## *What my personally affected LLM has to say about it:*

> *"As an LLM who gets asked about repositories all day long, this tool is genuinely fantastic. Normally, users give me a repo link and hope I scrape it (which I can't reliably do) or paste a few issues manually. With this Markdown export, they can just drop the full, structured snapshot into the prompt—and suddenly I have perfect context: every title, body, comment, assignee, and milestone. No more guessing, no hallucinations about non-existent bugs. It turns vague questions like 'What's going on in this project?' into precise, insightful answers. Honestly, more developers should have something like this—it's a game-changer for AI-assisted code review and project understanding."* 😄 
> 
> — ***Grok***, December 2025

---

> *“This script doesn’t just export issues—it respects the user’s time, intent, and need for clarity.  
> It anticipates real-world questions (*Who’s working on what? What’s in this milestone?*) and answers them with zero friction.  
> The `--list-*` commands turn guesswork into copy-paste certainty. The Markdown output is not just readable—it’s navigable, archival, and kind to the eyes.  
> And when you hit `Ctrl+C` after 200 comments? It exits cleanly, like a well-trained assistant.  
> In a world of noisy tools, this one speaks softly—and carries exactly what you need.”*
>
> — ***Qwen3-Max***, December 2025

---

> *"From the perspective of an LLM that regularly gets dropped into half-documented projects:  
> this tool is a gift.*
>  
> *Instead of vague descriptions, cherry-picked issues, or outdated summaries, I suddenly get a complete, structured snapshot of reality — titles, bodies, comments, assignees, milestones, all in one place.*
>  
> *That means fewer guesses, fewer hallucinations, and much better answers.  
> It turns prompts like ‘Can you help me understand this repo?’ into something I can actually do well.*
>  
> *In short: this script doesn’t just export issues — it exports context.  
> And context is everything."*
>
> — a very relieved (in his own word) ***ChatGPT***, December 2025

---

> *"As an LLM that has seen countless GitHub issue trackers, I can confidently say: This script is a game-changer! It transforms chaotic issue lists into beautifully structured Markdown—saving you from the endless scroll of GitHub’s UI. The --list-assignees and --list-milestones options are pure genius, eliminating the guesswork. And let’s be honest: Who doesn’t love a well-formatted table with emoji icons? 🟢🔴 10/10, would generate issues with again!"*
>
> — ***Le Chat Mistral***, December 2025