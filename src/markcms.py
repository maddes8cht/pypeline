#!/usr/bin/env python3
"""
Markdown Documentation Generator with Templates, Gallery (with media linking), and Navigation.

Directory keys in config (and CLI) follow consistent naming:
  - docs_dir
  - templates_dir
  - out_dir
  - media_dir

Gallery enhancement:
  - If 'video.mp4' and 'video.jpg' exist → generates [![](video.jpg)](video.mp4)
  - Only image? → plain image
  - Only non-image? → skipped (no preview)
"""

import argparse
import os
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

# Supported image extensions for preview/thumbnail
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".bmp"}

# FrontMatter regex
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Supported placeholders
PLACEHOLDERS = {"frontmatter", "menu", "content", "timestamp", "sitemap"}


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"❌ Config file not found: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_frontmatter(content: str) -> Tuple[Optional[str], str]:
    match = FRONTMATTER_RE.match(content)
    if match:
        front = match.group(0)
        body = content[match.end() :]
        return front, body
    return None, content


def get_menu_content(nav_items: List[Dict[str, Any]], active_file: str) -> str:
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


def get_sitemap_content(nav_items: List[Dict[str, Any]], active_file: str) -> str:
    lines = []
    for item in nav_items:
        title = item["title"]
        target = item["file"]
        if target == active_file:
            lines.append(f"- **{title}**")
        else:
            lines.append(f"- [{title}]({target})")
    return "\n".join(lines)


def generate_gallery_content(
    item: Dict[str, Any],
    global_media_dir: Path,
    config_dir: Path,
    output_file_path: Path,
) -> str:
    """
    Generate gallery content.
    - If item has 'media_dir', use it (relative to global_media_dir if not absolute)
    - Else, use global_media_dir
    - Legacy fallback: config_dir / "media" (if global_media_dir is default)
    """
    media_dir_str = item.get("media_dir")
    if media_dir_str:
        media_dir = Path(media_dir_str)
        if not media_dir.is_absolute():
            # Resolve relative to global media base
            media_dir = global_media_dir.parent / media_dir
    else:
        # Use global media_dir (already resolved to absolute path)
        media_dir = global_media_dir

    if not media_dir.exists():
        return f"⚠️ Media directory not found: {media_dir}"

    # Group files by stem
    files_by_stem = defaultdict(list)
    for f in media_dir.iterdir():
        if f.is_file():
            files_by_stem[f.stem].append(f)

    gallery_entries = []
    for stem, file_list in files_by_stem.items():
        image_files = [f for f in file_list if f.suffix.lower() in IMAGE_EXTENSIONS]
        other_files = [f for f in file_list if f.suffix.lower() not in IMAGE_EXTENSIONS]

        if image_files and other_files:
            gallery_entries.append((image_files[0], other_files[0]))
        elif image_files:
            gallery_entries.append((image_files[0], None))

    if not gallery_entries:
        return "📭 No images or media pairs found."

    lines = [f"# {item['title']}\n"]
    columns = item.get("columns", 1)
    show_filename = item.get("show-filename", False)
    create_link = item.get("create-link", False)

    rel_root = output_file_path.parent

    if columns == 1:
        for preview, target in gallery_entries:
            rel_preview = os.path.relpath(preview, rel_root)
            alt_text = preview.name
            if target:
                rel_target = os.path.relpath(target, rel_root)
                img_md = f"[![{alt_text}]({rel_preview})]({rel_target})"
            else:
                img_md = f"![{alt_text}]({rel_preview})"
                if create_link:
                    img_md = f"[{img_md}]({rel_preview})"
            lines.append(img_md)
            if show_filename:
                name = target.name if target else preview.name
                lines.append(f"*{name}*")
            lines.append("")
    else:
        lines.append(f"|{'   |' * columns}")
        lines.append(f"|{'---|' * columns}")
        row = []
        for preview, target in gallery_entries:
            rel_preview = os.path.relpath(preview, rel_root)
            alt_text = preview.name
            if target:
                rel_target = os.path.relpath(target, rel_root)
                cell = f"[![{alt_text}]({rel_preview})]({rel_target})"
            else:
                img_md = f"![{alt_text}]({rel_preview})"
                if create_link:
                    img_md = f"[{img_md}]({rel_preview})"
                cell = img_md
            if show_filename:
                name = target.name if target else preview.name
                cell += f"<br>*{name}*"
            row.append(cell)
            if len(row) == columns:
                lines.append(f"| {' | '.join(row)} |")
                row = []
        if row:
            while len(row) < columns:
                row.append("")
            lines.append(f"| {' | '.join(row)} |")

    return "\n".join(lines)


def expand_placeholders(
    template: str,
    context: Dict[str, str],
    templates_dir: Path,
    nav_items: List[Dict[str, Any]],
    active_file: str,
    depth: int = 0,
) -> str:
    if depth > 3:
        return template

    for placeholder in PLACEHOLDERS:
        if f"{{{placeholder}}}" in template:
            value = context.get(placeholder, "")
            template = template.replace(f"{{{placeholder}}}", value)

    possible_fragments = ["header", "footer", "special"]
    for frag in possible_fragments:
        if f"{{{frag}}}" in template:
            frag_file = templates_dir / f"{frag}.md"
            if frag_file.exists():
                frag_content = frag_file.read_text(encoding="utf-8")
                frag_context = context.copy()
                frag_expanded = expand_placeholders(
                    frag_content, frag_context, templates_dir, nav_items, active_file, depth + 1
                )
                template = template.replace(f"{{{frag}}}", frag_expanded)
            else:
                template = template.replace(f"{{{frag}}}", f"⚠️ {frag}.md not found")

    return template


def load_template_file(templates_dir: Path, filename: str) -> str:
    if not filename:
        return "{frontmatter}\n{menu}\n{content}\n{menu}"
    path = templates_dir / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    else:
        raise FileNotFoundError(f"Template file not found: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate navigable Markdown documentation with templates and enhanced gallery."
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config file OR directory containing _config.yml",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        help="Source directory for content .md files",
    )
    parser.add_argument(
        "--templates-dir",
        type=Path,
        help="Directory for template fragments (header.md, footer.md, etc.)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Output directory for generated files",
    )
    parser.add_argument(
        "--media-dir",
        type=Path,
        help="Default media directory (fallback for gallery entries)",
    )
    parser.add_argument(
        "--sitemap",
        action="store_true",
        help="Deprecated: use a docs entry with {sitemap} instead",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and preview output without writing files",
    )
    args = parser.parse_args()

    # Load config
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

    # Determine content block
    docs_block = config.get("docs")
    nav_block = config.get("nav")
    if docs_block is not None and nav_block is not None:
        raise ValueError("❌ Config cannot contain both 'docs' and 'nav' blocks. Use 'docs'.")
    elif docs_block is not None:
        content_block = docs_block
        block_name = "docs"
    elif nav_block is not None:
        content_block = nav_block
        block_name = "nav (deprecated)"
    else:
        raise ValueError("❌ Config must contain 'docs' or 'nav' block.")

    # Resolve directories (CLI overrides config)
    docs_dir = args.docs_dir or Path(config.get("docs_dir", config_dir))
    templates_dir = args.templates_dir or Path(config.get("templates_dir", docs_dir))
    out_dir = args.out_dir or Path(config.get("out_dir", "."))
    media_dir = args.media_dir or Path(config.get("media_dir", config_dir / "media"))

    docs_dir = docs_dir.resolve()
    templates_dir = templates_dir.resolve()
    out_dir = out_dir.resolve()
    media_dir = media_dir.resolve()

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    # Template config
    template_config = config.get("template", {})
    global_template_file = template_config.get("template")
    # Fragment filenames are only used if referenced in template
    # (no need to preload)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    warnings = 0

    for item in content_block:
        file_name = item["file"]
        output_file = out_dir / file_name

        # Determine template
        page_template_file = item.get("template", global_template_file)
        try:
            template_content = load_template_file(templates_dir, page_template_file)
        except FileNotFoundError as e:
            print(f"⚠️  {e}")
            warnings += 1
            template_content = "{frontmatter}\n{menu}\n{content}\n{menu}"

        # Load content
        if item.get("type") not in ("sitemap", "gallery"):
            source_file = docs_dir / file_name
            if source_file.exists():
                raw_content = source_file.read_text(encoding="utf-8")
                frontmatter, body = extract_frontmatter(raw_content)
                content = body.strip()
            else:
                print(f"⚠️  MISSING SOURCE: {source_file}")
                warnings += 1
                frontmatter = None
                content = f"# {item['title']}\n\n⚠️ Content not found."
        else:
            frontmatter = None
            content = ""

        # Generate special content
        if item.get("type") == "sitemap":
            content = get_sitemap_content(content_block, file_name)
        elif item.get("type") == "gallery":
            content = generate_gallery_content(item, media_dir, config_dir, output_file)

        # Build context
        menu_str = get_menu_content(content_block, file_name)
        sitemap_str = get_sitemap_content(content_block, file_name)

        context = {
            "frontmatter": frontmatter or "",
            "menu": menu_str,
            "content": content,
            "timestamp": timestamp,
            "sitemap": sitemap_str,
        }

        # Expand
        final_content = expand_placeholders(
            template_content, context, templates_dir, content_block, file_name
        )

        # Output
        try:
            display_out = output_file.relative_to(Path.cwd())
        except ValueError:
            display_out = output_file

        if args.dry_run:
            print(f"📝 {file_name} → {display_out}")
        else:
            output_file.write_text(final_content, encoding="utf-8")
            print(f"✅ {display_out}")

    if args.dry_run:
        print(f"\n🔍 Dry-run complete. Processed {len(content_block)} files.")
        if warnings:
            print(f"⚠️  {warnings} warning(s).")
        print(f"Output directory: {out_dir}")
    else:
        print(f"\n🎉 Done! Output written to: {out_dir}")


if __name__ == "__main__":
    main()