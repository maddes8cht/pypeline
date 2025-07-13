# Pypeline

A compact set of Python CLI tools to keep my dev workflow flowing smoothly, built for automation and LLM collaboration.

Super easy and simple system to manage my python scripts scattered in different repositories and locations on my disks: Always have easy to update wrapper scripts in one location in my path that allow me to execute the script
* from their respective current location
* with the proper python interpreter of their conda environment
* automagically have an easy to use info system with all the help texts for all script files

## Tools

### `generate-cmd.py`

**Problem**: I have Python scripts scattered across different Conda environments and GitHub repos. Running them requires switching to the right directory and environment, which is tedious from various terminals or editors. Even with shebangs or PATH setups, finding the correct Conda environment is a hassle.

**Solution**: `generate-cmd.py` creates Windows `.cmd` wrappers for Python scripts, embedding their `--help` text as comments. These wrappers go into a central `C:\PAP\cmd` directory (in my `PATH`), so I can run scripts from anywhere. Paired with `cmdfzf.cmd`, which uses `fzf` to browse and preview help text, it’s a fast, organized system to find and execute scripts—even if I vaguely remember their names.

### `cmdfzf.cmd`

**Problem**: As my collection of `.cmd` wrappers grew, finding and running the right script became tricky. I needed quick access to their help text without calling each script.

**Solution**: `cmdfzf.cmd` is a Windows batch script that uses `fzf` to interactively list `.cmd` files in `C:\PAP\cmd`. It shows help text or script content in a preview window, making it faster to browse and run scripts than executing them directly. It’s like a supercharged help system powered by `fzf`’s fuzzy search.

### `generate-issue-md.py`

**Problem**: I manage projects with GitHub Issues, creating issue branches, solving them, and merging back. To keep LLMs updated on project status via RAG, I need a concise summary of issues.

**Solution**: `generate-issue-md.py` pulls GitHub issues and generates a single Markdown file with summaries and details. It’s customizable (filter by state, add emojis) and creates LLM-friendly reports, streamlining project tracking.

### `debug.py`

**Problem**: During development, I need debug output for troubleshooting, but Python’s `logging` module feels overkill for simple scripts. I also want optional verbose output for users without complex setup.

**Solution**: `debug.py` provides a lightweight `Debug` class with two instances: `debug` for development-only output (enabled manually in code) and `verbose` for user-controlled output (via `--verbose` flag). It’s simpler than `logging`, integrates easily with my scripts, and keeps my pypeline clean and focused.

## Setup

- **recent Python version**: For `generate-cmd.py` and `generate-issue-md.py`.  
Tested with python 3.12, 3.13. Should work with any current version greater as 3.9.
- **Windows**: For `.cmd` files and `cmdfzf.cmd`. The pypeline is windows-centric,  things may not work on other OSes.
- **Tools**: Install [GitHub CLI (`gh`)](https://cli.github.com/), [`fzf`](https://github.com/junegunn/fzf/releases), [`awk`](https://git-scm.com/downloads) (via Git Bash), and optionally [`bat`](https://github.com/sharkdp/bat/releases) for previews.
- **Custom**: `cmdlist` for `cmdfzf.cmd` previews (replace with your tool if needed).
- **Conda**: Optional for future `generate-cmd.py` support.

1. Clone: `git clone https://github.com/maddes8cht/pypeline.git`
2. Install deps: `pip install -r requirements.txt` (currently empty).
3. Set up `C:\PAP\cmd` and add to `PATH`.
4. Run `gh auth login` for GitHub CLI.
5. Place `cmdfzf.cmd` in `C:\PAP\cmd` or `PATH`.

## Requirements
The tools are meant to be lightweight and without much dependencys. From the python side, there are no requirements byond the standard libraries always included in python. Once this changes, there will be a `requuirements.txt` file.

## Usage

- **generate-cmd.py**: `python scripts/generate-cmd.py path/to/script.py C:\PAP\cmd`  
  Creates `C:\PAP\cmd\script.cmd`. Use `--update path/to/existing.cmd` to refresh.  
  Run: `script --help`

- **cmdfzf.cmd**: `cmdfzf.cmd [query]`  
  Browse `.cmd` files with `fzf`. Use `[ctrl]-b` for script preview, `[ctrl]-c` for help text.

- **generate-issue-md.py**: `python scripts/generate-issue-md.py --repo user/repo --filename issues.md`  
  Outputs Markdown with issue summaries. Use `--state all`, `--color`, or `--dry-run`.


- **debug.py**: Import `debug` and `verbose` instances:  
  ```python
  from scripts.debug import debug, verbose
  debug.enabled = True  # For dev-only output
  verbose.enabled = args.verbose  # For user-controlled output
  debug.print("Debugging info")
  verbose.print("Verbose output")
  ```

## Structure
```
pypeline/
├── scr/
│   ├── cmdfzf.cmd
│   ├── generate-cmd.py
│   ├── generate_issue_md.py
│   ├── debug.py
├── tests/
├── README.md
└── requirements.txt
```
