#!/usr/bin/env python3
"""
Markdown Documentation Generator with Navigation, Sitemap, and Gallery Support.

Features:
- Preserves YAML front matter from source .md files
- Auto-infers gallery media path relative to config file if not specified
- Supports --dry-run for validation without writing files
- Full CLI control over config, docs, out, media paths

The --config option specifies either:
  - A directory → script uses _config.yml inside it
  - A full path to a YAML config file (any name)
"""

import argparse
import os
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Supported image extensions for gallery generation
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".bmp"}

# FrontMatter detection (must be at very top of file)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load and parse YAML config file."""
    if not config_path.exists():
        raise FileNotFoundError(f"❌ Config file not found: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_frontmatter(content: str) -> Tuple[Optional[str], str]:
    """
    Extract YAML front matter from Markdown content.
    Returns (frontmatter_str, body_content).
    If no front matter, returns (None, original_content).
    """
    match = FRONTMATTER_RE.match(content)
    if match:
        front = match.group(0)
        body = content[match.end() :]
        return front, body
    return None, content


def get_nav_links(nav_items: List[Dict[str, Any]], active_file: str) -> str:
    """Generate a horizontal navigation bar with links to all nav items."""
    links = []
    for item in nav_items:
        title = item["title"]
        target = item["file"]
        if target == active_file:
            link = f"**{title}**"
        else:
            link = f"[{title}]({target})"
        links.append(link)
    return " • ".join(links)


def generate_sitemap_content(nav_items: List[Dict[str, Any]]) -> str:
    """Generate a markdown sitemap listing all non-sitemap nav items."""
    lines = ["# Table of Contents\n"]
    for item in nav_items:
        if item.get("type") == "sitemap":
            continue
        lines.append(f"- [{item['title']}]({item['file']})")
    return "\n".join(lines)


def generate_gallery_content(
    item: Dict[str, Any],
    config_dir: Path,
    media_base_dir: Path,
    output_file_path: Path,
) -> str:
    """
    Generate a Markdown image gallery.
    If 'media' is not specified in the item, infer as config_dir / 'media'.
    """
    media_dir_str = item.get("media")
    if media_dir_str:
        media_dir = Path(media_dir_str)
        if not media_dir.is_absolute():
            media_dir = media_base_dir / media_dir
    else:
        # Auto-infer: use 'media' subdirectory next to config file
        media_dir = config_dir / "media"

    if not media_dir.exists():
        return f"⚠️ Media directory not found: {media_dir}"

    image_files = sorted(
        [f for f in media_dir.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS]
    )

    if not image_files:
        return "📭 No images found."

    lines = [f"# {item['title']}\n"]
    columns = item.get("columns", 1)
    show_filename = item.get("show-filename", False)
    create_link = item.get("create-link", False)

    rel_root = output_file_path.parent

    if columns == 1:
        for img in image_files:
            rel_img_path = os.path.relpath(img, rel_root)
            alt_text = img.name
            img_md = f"![{alt_text}]({rel_img_path})"
            if create_link:
                img_md = f"[{img_md}]({rel_img_path})"
            lines.append(img_md)
            if show_filename:
                lines.append(f"*{img.name}*")
            lines.append("")
    else:
        # Use empty headers to avoid "Image" labels
        lines.append(f"|{'   |' * columns}")
        lines.append(f"|{'---|' * columns}")
        row = []
        for img in image_files:
            rel_img_path = os.path.relpath(img, rel_root)
            alt_text = img.name
            img_md = f"![{alt_text}]({rel_img_path})"
            if create_link:
                img_md = f"[{img_md}]({rel_img_path})"
            if show_filename:
                img_md += f"<br>*{img.name}*"
            row.append(img_md)
            if len(row) == columns:
                lines.append(f"| {' | '.join(row)} |")
                row = []
        if row:
            while len(row) < columns:
                row.append("")
            lines.append(f"| {' | '.join(row)} |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate navigable Markdown documentation with sitemap and gallery support."
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config file OR directory containing _config.yml (default: ./_config.yml)",
    )
    parser.add_argument(
        "--docs",
        type=Path,
        help="Source directory for content .md files",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Output directory for generated files",
    )
    parser.add_argument(
        "--media",
        type=Path,
        help="Default media directory (fallback for gallery entries)",
    )
    parser.add_argument(
        "--sitemap",
        action="store_true",
        help="Force generation of sitemap.md even if not declared in config",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and show what would be generated (no files written)",
    )
    args = parser.parse_args()

    # 1. Determine config file path
    if args.config:
        config_input = args.config
        if config_input.is_dir():
            config_path = config_input / "_config.yml"
        else:
            config_path = config_input
    else:
        config_path = Path.cwd() / "_config.yml"

    config = load_config(config_path)
    config_dir = config_path.parent

    # 2. Resolve directories: CLI args override config
    docs_dir = args.docs or Path(config.get("docs", config_dir))
    out_dir = args.out or Path(config.get("out", "."))
    media_dir = args.media or Path(config.get("media", config_dir / "media"))

    docs_dir = docs_dir.resolve()
    out_dir = out_dir.resolve()
    media_dir = media_dir.resolve()

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    # 3. Load navigation
    nav_items = config.get("nav", [])
    if not nav_items:
        raise ValueError("❌ No 'nav' entries found in config file.")

    base_title = config.get("title", "Documentation")

    if args.sitemap:
        sitemap_item = {"title": "Sitemap", "file": "sitemap.md", "type": "sitemap"}
        if not any(item.get("type") == "sitemap" for item in nav_items):
            nav_items.append(sitemap_item)

    errors = 0
    warnings = 0

    # 4. Validate and process
    for item in nav_items:
        file_name = item["file"]
        output_file = out_dir / file_name

        # Validate source file for regular content
        if item.get("type") not in ("sitemap", "gallery"):
            source_file = docs_dir / file_name
            if not source_file.exists():
                print(f"⚠️  MISSING SOURCE: {source_file}")
                warnings += 1
                content = f"# {item['title']}\n\n⚠️ Content not found."
                frontmatter = None
            else:
                raw_content = source_file.read_text(encoding="utf-8")
                frontmatter, body = extract_frontmatter(raw_content)
                content = body.strip()
        else:
            frontmatter = None
            content = ""

        # Special content generation
        if item.get("type") == "sitemap":
            content = generate_sitemap_content(nav_items)
        elif item.get("type") == "gallery":
            content = generate_gallery_content(item, config_dir, media_dir, output_file)

        # Final output assembly
        nav_bar = get_nav_links(nav_items, file_name)
        header = f"# {base_title}\n\n{nav_bar}\n\n---\n\n"
        final_content = header + content + f"\n\n---\n\n{nav_bar}"

        # Re-insert front matter if present
        if frontmatter:
            final_content = frontmatter + final_content

        # Safe display path
        try:
            display_out = output_file.relative_to(Path.cwd())
        except ValueError:
            display_out = output_file

        if args.dry_run:
            print(f"📝 {file_name} → {display_out}")
            if frontmatter:
                print("   (FrontMatter preserved)")
        else:
            output_file.write_text(final_content, encoding="utf-8")
            print(f"✅ {display_out}")

    # Summary
    if args.dry_run:
        print(f"\n🔍 Dry-run complete. Checked {len(nav_items)} files.")
        if warnings:
            print(f"⚠️  {warnings} warning(s) (missing sources).")
        print(f"Output directory: {out_dir}")
    else:
        print(f"\n🎉 Done! Output written to: {out_dir}")


if __name__ == "__main__":
    main()