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

## Usage

- **generate-cmd.py**: `python scripts/generate-cmd.py path/to/script.py C:\PAP\cmd`  
  Creates `C:\PAP\cmd\script.cmd`. Use `--update path/to/existing.cmd` to refresh.  
  Run: `script --help`

- **cmdfzf.cmd**: `cmdfzf.cmd [query]`  
  Browse `.cmd` files with `fzf`. Use `[ctrl]-b` for script preview, `[ctrl]-c` for help text.

- **generate-issue-md.py**: `python scripts/generate-issue-md.py --repo user/repo --filename issues.md`  
  Outputs Markdown with issue summaries. Use `--state all`, `--color`, or `--dry-run`.


### Installation
1. Clone the repo:
   ```bash
   git clone https://github.com/maddes8cht/pypeline.git
   cd pypeline
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   (Currently empty, but check `requirements.txt` for future updates.)
3. Set up the central `.cmd` directory:
   - Create a folder (e.g., `C:\PAP\cmd`).
   - Add it to your system `PATH` (search "Edit environment variables" in Windows).
4. Ensure `fzf`, `awk`, and `bat` (optional) are in your `PATH`.
5. Configure the GitHub CLI:
   ```bash
   gh auth login
   ```
6. Place `cmdfzf.cmd` in `C:\PAP\cmd` or another `PATH` location.

## Usage

### 1. `generate-cmd.py`
Wraps Python scripts into `.cmd` files with their `--help` output as comments, feeding into your system-wide script pipeline.

**Run it**:
```bash
python scripts/generate-cmd.py path/to/your_script.py path/to/output_dir
```
- Skip arguments to use file dialogs.
- Update an existing `.cmd`:
  ```bash
  python scripts/generate-cmd.py --update path/to/existing.cmd
  ```

**Example**:
```bash
python scripts/generate-cmd.py my_script.py C:\PAP\cmd
```
Creates `C:\PAP\cmd\my_script.cmd`, callable with:
```bash
my_script --help
```

**Note**: Conda environment support is coming to keep your script pipeline flowing smoothly.

### 2. `cmdfzf.cmd`
Browse and run `.cmd` files in your central directory (e.g., `C:\PAP\cmd`) with `fzf` for an interactive help system.

**Run it**:
```bash
cmdfzf.cmd [query]
```
- `[ctrl]-b`: Toggle between `bat` (script content) and `cmdlist` (help text) previews.
- `[ctrl]-c`: Switch back to `cmdlist`.

**Example**:
```bash
cmdfzf.cmd git
```
Searches for `.cmd` files with "git" in the name and runs the selected one.

**Note**: The `C:\PAP\cmd` directory is hardcoded for now—configurable version coming soon.

### 3. `generate-issue-md.py`
Pipes GitHub issues into Markdown files with summaries and details, perfect for LLM-friendly project updates.

**Run it**:
```bash
python scripts/generate-issue-md.py --repo user/repo --filename ISSUES.md --state open
```
- `--repo`: GitHub repo (e.g., `user/repo`). Defaults to current repo.
- `--filename`: Output file (default: `ISSUES.md`).
- `--state`: Issues to include (`open`, `closed`, `all`; default: `open`).
- `--color`: Add emoji icons.
- `--top-link-style`: Back-to-top links (`icon`, `text`, `both`, `none`; default: `both`).
- `--verbose`: Show detailed output.
- `--dry-run`: Preview without saving.

**Example**:
```bash
python scripts/generate-issue-md.py --repo octocat/hello-world --filename issues.md --state all --color
```
Creates `issues.md` with all issues from `octocat/hello-world`.

## Folder Structure
```
pypeline/
├── scripts/
│   ├── generate-cmd.py        # Generates .cmd wrappers
│   ├── generate-issue-md.py   # Generates GitHub issue Markdown
│   └── (future scripts)
├── tests/
│   ├── test_generate_cmd.py   # Tests for generate-cmd.py
│   ├── test_generate-issue-md.py # Tests for generate-issue-md.py
├── cmdfzf.cmd                 # Interactive .cmd runner (place in C:\PAP\cmd or PATH)
├── README.md                  # You're reading it!
└── requirements.txt           # Python dependencies (if any)
```

## Contributing
Got ideas to keep the pypeline flowing? Open an issue or submit a pull request! I’m especially interested in:
- Conda support for `generate-cmd.py`.
- Configurable directories in `cmdfzf.cmd`.
- New Python CLI tools to enhance the pipeline, especially for LLM workflows.

## License
MIT License. See the `LICENSE` file for details.