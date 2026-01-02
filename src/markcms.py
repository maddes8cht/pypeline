#!/usr/bin/env python3
"""
Markdown Documentation Generator with Navigation, Sitemap, and Gallery Support.

The --config option specifies either:
  - A directory → script looks for _config.yml inside it
  - A full path to a YAML config file (any name)

Other path resolution logic (CLI arguments override config):
- --docs   : Source directory for content .md files
- --out    : Output directory for generated .md files
- --media  : Default media directory (fallback for gallery entries)

The config file may optionally contain:
  out: ...
  docs: ...
  media: ...

Each entry in the 'nav' list is processed:
- Regular .md files are read from the docs directory and wrapped with navigation.
- Entries with type: sitemap generate an auto-built table of contents.
- Entries with type: gallery generate a Markdown image gallery from a media folder.

All generated files include consistent top/bottom navigation bars.
"""

import argparse
import os
import yaml
from pathlib import Path
from typing import List, Dict, Any

# Supported image extensions for gallery generation
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".bmp"}


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load and parse YAML config file."""
    if not config_path.exists():
        raise FileNotFoundError(f"❌ Config file not found: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


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
    item: Dict[str, Any], media_base_dir: Path, output_file_path: Path
) -> str:
    """Generate a Markdown image gallery from a media directory."""
    media_dir_str = item.get("media")
    if media_dir_str:
        media_dir = Path(media_dir_str)
        if not media_dir.is_absolute():
            media_dir = media_base_dir / media_dir
    else:
        media_dir = media_base_dir

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
    link_target = item.get("link-target", "image")  # 'image' or 'blank' (HTML only)

    # Compute relative path from output file to image
    rel_root = output_file_path.parent

    if columns == 1:
        for img in image_files:
            rel_img_path = os.path.relpath(img, rel_root)
            alt_text = img.name
            img_md = f"![{alt_text}]({rel_img_path})"
            if create_link:
                # Wrap image in a link to itself
                img_md = f"[{img_md}]({rel_img_path})"
            lines.append(img_md)
            if show_filename:
                lines.append(f"*{img.name}*")
            lines.append("")
    else:
        # Use empty headers: |   |   |   |
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
    args = parser.parse_args()

    # 1. Determine config file path
    if args.config:
        config_input = args.config
        if config_input.is_dir():
            config_path = config_input / "_config.yml"
        else:
            config_path = config_input
    else:
        # Default: _config.yml in current working directory
        config_path = Path.cwd() / "_config.yml"

    config = load_config(config_path)

    # 2. Resolve directories: CLI args override config
    config_dir = config_path.parent  # used as base for relative paths in config

    docs_dir = args.docs or Path(config.get("docs", config_dir))
    out_dir = args.out or Path(config.get("out", "."))
    media_dir = args.media or Path(config.get("media", config_dir / "media"))

    # Normalize to absolute paths
    docs_dir = docs_dir.resolve()
    out_dir = out_dir.resolve()
    media_dir = media_dir.resolve()

    out_dir.mkdir(parents=True, exist_ok=True)

    # 3. Load navigation structure
    nav_items = config.get("nav", [])
    if not nav_items:
        raise ValueError("❌ No 'nav' entries found in config file.")

    base_title = config.get("title", "Documentation")

    # Optionally inject forced sitemap
    if args.sitemap:
        sitemap_item = {"title": "Sitemap", "file": "sitemap.md", "type": "sitemap"}
        if not any(item.get("type") == "sitemap" for item in nav_items):
            nav_items.append(sitemap_item)

    # 4. Process every nav item
    for item in nav_items:
        file_name = item["file"]
        output_file = out_dir / file_name

        if item.get("type") == "sitemap":
            content = generate_sitemap_content(nav_items)
        elif item.get("type") == "gallery":
            content = generate_gallery_content(item, media_dir, output_file)
        else:
            # Regular content file: read from docs_dir
            source_file = docs_dir / file_name
            if source_file.exists():
                content = source_file.read_text(encoding="utf-8").strip()
            else:
                print(f"⚠️ Source file missing: {source_file} → creating placeholder.")
                content = f"# {item['title']}\n\n⚠️ Content not found."

        # Wrap with navigation
        nav_bar = get_nav_links(nav_items, file_name)
        header = f"# {base_title}\n\n{nav_bar}\n\n---\n\n"
        final_content = header + content + f"\n\n---\n\n{nav_bar}"

        output_file.write_text(final_content, encoding="utf-8")

        # Safely display output path (relative if possible, else absolute)
        try:
            display_path = output_file.relative_to(Path.cwd())
        except ValueError:
            display_path = output_file
        print(f"✅ {display_path}")

    print(f"\n🎉 Done! Output written to: {out_dir}")


if __name__ == "__main__":
    main()