# 📑 **markcms — A Lightweight Markdown CMS for GitHub & Hugging Face**

`markcms` is a powerful yet minimalist **Markdown Content Management System** designed to generate navigable, multi-page documentation from a set of Markdown files. It’s optimized for platforms like **GitHub**, **GitLab**, and **Hugging Face**, where a `README.md` serves as the landing page.

With `markcms`, you can:
- Maintain a consistent navigation menu across pages.
- Use templates and reusable fragments (e.g., headers, footers, notes).
- Embed responsive **media galleries** (images, videos, documents).
- Link to external or internal pages with platform-aware navigation.
- Automate documentation builds with full control over structure and style.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- `PyYAML`: Install via `pip install PyYAML`

### Basic Usage
```bash
# Generate documentation from _config.yml in current directory
python markcms.py

# Use a specific config
python markcms.py --config ./my-project/_config.yml

# Preview without writing files
python markcms.py --dry-run

# See all available template variables
python markcms.py --list-placeholders
```

---

## 📂 Project Structure Example

```
my-dataset/
├── _config.yml                 # Main configuration
├── source/                     # Source Markdown files
│   ├── README.md
│   ├── history.md
│   └── gallery.md
├── templates/                  # Template fragments
│   ├── default.md
│   ├── header.md
│   └── footer.md
├── media/                      # Default media files
└── media-types/                # Global preview icons (for .mp4, .pdf, etc.)
```

---

## 🧩 Configuration: `_config.yml`

All behavior is controlled via a single `_config.yml` file.

### Top-Level Keys

| Key | Required | Default | Description |
|-----|----------|--------|-------------|
| `title` | No | — | Project title (used in templates if referenced). |
| `docs_dir` | No | Config directory | Source directory for `.md` files. |
| `out_dir` | No | `.` | Output directory for generated files. |
| `templates_dir` | No | `docs_dir` | Directory for template fragments (`header.md`, etc.). |
| `media_dir` | No | `config_dir/media` | Global media directory (fallback for galleries). |
| `template_media_dir` | No | `templates_dir/media-icons` | Directory containing preview icons for file types (e.g., `video.jpg` for `.mp4`). |
| `templates` | No | — | Custom template fragments (see below). |
| `media_previews` | No | — | Mapping of file extensions to preview icons. |
| `docs` | **Yes** | — | List of navigation/menu entries (see below). |

> 💡 **All paths are resolved relative to `_config.yml`** (unless absolute).

---

### The `docs` Block: Navigation & Page Definitions

Each entry in `docs` defines a page or link in your navigation.

#### Common Fields

| Field | Required | Description |
|------|----------|-------------|
| `title` | ✅ Yes | Display name in menu. |
| `file` | ⚠️ Conditional | Source filename (relative to `docs_dir`). Required unless it’s a pure external link. |
| `type` | No | Page type: `page` (default), `gallery`, `sitemap`, or `link`. |
| `link` | ⚠️ Only for `type: link` | Target URL (internal or external). |
| `template` | No | Page-specific template (overrides global). |
| `media_dir` | No (for `gallery`) | Gallery-specific media directory. |
| `columns` | No (for `gallery`) | Number of columns (1 = vertical, ≥2 = table). |
| `show-filename` | No | Show filenames under images. |
| `create-link` | No | Link images to themselves (for lightbox-style viewers). |

---

### Page Types Explained

#### 1. **Standard Page** (`type` omitted or `page`)
- Reads content from `file`.
- Processes FrontMatter, applies template, injects menu.
- **Example**:
  ```yaml
  - title: "Introduction"
    file: intro.md
    template: docs-template.md
  ```

#### 2. **Gallery** (`type: gallery`)
Two modes:
- **Backward-compatible**: If `file` exists but contains **no `{gallery}`**, the entire page becomes a gallery (with auto-generated `# Title` header).
- **Flexible**: If `file` contains `{gallery}`, the gallery is inserted **exactly where placed** – no auto-header.

> 🖼️ **Gallery Behavior**:
> - Paired files (e.g., `video.mp4` + `video.jpg`) → use `video.jpg` as preview.
> - Unpaired media → use `media_previews` mapping (e.g., `.mp4` → `video.jpg`).
> - Images without pairs → displayed directly.

**Example**:
```yaml
- title: "Videos"
  file: videos.md
  type: gallery
  media_dir: ./media/videos
  columns: 3
```

And `videos.md`:
```markdown
# Our Video Collection

Browse our latest recordings:

{gallery}

> Updated on {timestamp}
```

#### 3. **Sitemap** (`type: sitemap`)
Generates a vertical list of all pages (like `{sitemap}` placeholder).

#### 4. **Link** (`type: link`)
Two sub-modes:
- **Without `file`**: Pure external/internal link (no file generated).
- **With `file`**: File is **processed normally**, but in **other pages’ menus**, the link points to `link` (not `file`).

> ✅ **Perfect for Hugging Face**:  
> Use `file: README.md` + `link: "/datasets/YourName"` so users return to the **dataset homepage**, not the file browser.

**Example**:
```yaml
- title: "Home"
  file: README.md
  type: link
  link: "/datasets/Traders-Lab"
```

---

### Custom Template Fragments (`templates`)

Define reusable blocks beyond `header`/`footer`:

```yaml
templates:
  - note: note.md
  - warning: warning.md
  - author: author-block.md
```

Then use in any template or source file:
```markdown
{warning}

This model is experimental.

{note}
```

> ⚠️ **Reserved names** (`menu`, `content`, `timestamp`, `header`, etc.) cannot be redefined.

---

### Media Previews (`media_previews`)

Map file extensions to preview icons:

```yaml
media_previews:
  mp4: video.jpg
  pdf: document.jpg
  ipynb: notebook.jpg
```

These icons must exist in `template_media_dir`.

---

## 🧾 Template System

### Built-in Placeholders

| Placeholder     | Scope      | Description                                             |
| --------------- | ---------- | ------------------------------------------------------- |
| `{frontmatter}` | Context    | Original YAML block (if present).                       |
| `{menu}`        | Context    | Horizontal navigation: `Page1 • **Current** • Page3`.   |
| `{sitemap}`     | Context    | Vertical list of all pages.                             |
| `{content}`     | Context    | Main body of the current page.                          |
| `{gallery}`     | Page-level | Media gallery (if configured).                          |
| `{timestamp}`   | Global     | Current date (`YYYY-MM-DD`).                            |
| `{header}`      | Fragment   | From `templates/header.md`.                             |
| `{footer}`      | Fragment   | From `templates/footer.md`.                             |
| `{special}`     | Fragment   | From `templates/special.md`.                            |
| `{custom}`      | Fragment   | From `templates/custom.md` (if defined in `templates`). |

> 🔁 **Fragments can contain other placeholders** (up to 3 levels deep).

---

### Example Template (`templates/default.md`)

```markdown
{header}

{menu}

{content}

{footer}
```

With `templates/header.md`:
```markdown
# 📊 Financial Datasets by TradersLab

> Curated market data for researchers and developers.
```

---

## 🖼️ Gallery System — Deep Dive

### File Matching Priority

1. **Paired files**: `report.mp4` + `report.jpg` → `report.jpg` previews `report.mp4`.
2. **Unpaired images**: `photo.png` → displayed directly.
3. **Other media with preview**: `data.pdf` → uses `document.jpg` (from `media_previews`).
4. **Other media without preview**: Ignored.

### Layout Options

- **Single column**: Each item on its own line (supports `create-link`).
- **Multi-column**: Rendered as a Markdown table (filenames appear below with `<br>`).

---

## 🛠️ Command-Line Options

| Option | Description |
|-------|-------------|
| `--config PATH` | Path to `_config.yml` or its directory. |
| `--docs-dir`, `--templates-dir`, etc. | Override config paths. |
| `--dry-run` | Show what would be generated (no file writes). |
| `--verbose` | Show resolved paths and processing details. |
| `--list-placeholders` | List all available placeholders (built-in + custom). |

---

## 🌐 Platform-Specific Tips

### Hugging Face Datasets
- Use `type: link` with `file: README.md` to ensure "Home" links to the **dataset page**, not the file view.
- Store media in a dedicated `media/` folder outside the repo root to reduce clone size.

### GitHub Repositories
- The generated `README.md` will display correctly on the repo homepage.
- Use `{timestamp}` to show last-updated info.

---

## 🔒 Reserved Names & Validation

The following names **cannot** be used as custom template fragments:
```
content, frontmatter, menu, sitemap, timestamp,
header, footer, special, gallery
```

Attempting to redefine them triggers a clear error.

---

## ✅ Best Practices

1. **Use `--dry-run`** before pushing to Hugging Face/GitHub.
2. **Enable `--verbose`** when debugging path issues.
3. **Store templates and media outside `docs_dir`** for cleaner source separation.
4. **Use relative links** in `link` fields for portability (e.g., `/datasets/MyProject`).
5. **Leverage `{gallery}`** for maximum layout control.

---

## 📜 Example `_config.yml`

```yaml
title: "TroveLedger"
docs_dir: ./source
out_dir: ./target
templates_dir: ./templates
media_dir: ./media
template_media_dir: ./media-types

media_previews:
  mp4: video.jpg
  pdf: document.jpg

templates:
  - note: note.md
  - warning: warning.md
  - author: author.md

docs:
  - title: "Home"
    file: README.md
    type: link
    link: "/datasets/Traders-Lab"
  - title: "History"
    file: history.md
  - title: "Gallery"
    file: gallery.md
    type: gallery
    media_dir: ./media/gallery
    columns: 3
  - title: "External Guide"
    type: link
    link: "https://example.com/guide"
```

---

## 📦 License

`markcms` is free and open-source. Use, modify, and distribute as you see fit.

---

> **Built for developers, data scientists, and open-source maintainers who believe documentation matters.**  
> — `markcms` v1.0
