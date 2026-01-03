#!/usr/bin/env python3
"""
Markdown Documentation Generator with Templates, Enhanced Gallery, and Media Previews.

Features:
- Backward compatible: works with old configs (no template, no media_previews)
- Global media_previews with per-gallery media_dir support
- Paired previews (video.mp4 + video.jpg) take precedence
- Preview templates stored in template_media_dir (default: templates_dir/media-icons)
- Full FrontMatter preservation
- Dry-run mode for validation
- Supports 'type: link' entries (with or without 'file') for GitHub/HF UX
- All paths in config resolved relative to _config.yml (unless absolute)
- Verbose mode for debugging

Directory config keys (consistent):
  - docs_dir
  - templates_dir
  - out_dir
  - media_dir
  - template_media_dir

Content block: use 'docs' (preferred); 'nav' is deprecated.
"""

import argparse
import os
import re
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

# Optional debug/verbose support
try:
    from debug import debug, verbose
except ImportError:
    class DummyDebug:
        def print(self, *args, **kwargs): pass
        def on(self): pass
        def off(self): pass
    debug = DummyDebug()
    verbose = DummyDebug()

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".bmp"}

# FrontMatter regex
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Supported placeholders
PLACEHOLDERS = {"frontmatter", "menu", "content", "timestamp", "sitemap"}


def resolve_path(path_str: str, base_dir: Path) -> Path:
    """Resolve a path string: absolute as-is, relative to base_dir."""
    p = Path(path_str)
    return p if p.is_absolute() else (base_dir / p).resolve()


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"❌ Config file not found: {config_path}")
    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        error_msg = str(e)
        if "found character '\\t' that cannot start any token" in error_msg:
            line_info = ""
            if hasattr(e, 'problem_mark') and e.problem_mark:
                line_info = f" near line {e.problem_mark.line + 1}"
            detailed_msg = (
                f"❌ Invalid YAML in config file: {config_path}{line_info}\n"
                f"   → YAML does not allow TAB characters for indentation.\n"
                f"   → Please replace all TABs with spaces (e.g., 2 or 4 per level).\n"
                f"   → Tip: Enable 'Render Whitespace' in your editor to see TABs."
            )
        else:
            detailed_msg = (
                f"❌ Invalid YAML syntax in config file: {config_path}\n"
                f"   → {error_msg}"
            )
        raise ValueError(detailed_msg) from e


def extract_frontmatter(content: str) -> Tuple[Optional[str], str]:
    match = FRONTMATTER_RE.match(content)
    if match:
        front = match.group(0)
        body = content[match.end() :]
        return front, body
    return None, content


def get_menu_key(item: Dict[str, Any]) -> str:
    """Return a stable, unique key for menu/sitemap identification."""
    if "file" in item:
        return item["file"]
    elif item.get("type") == "link":
        title = item["title"]
        safe_title = re.sub(r"[^\w\-_.]", "_", title)
        return f"__link__{safe_title}__"
    else:
        return item["title"]


def get_menu_content(nav_items: List[Dict[str, Any]], active_key: str) -> str:
    links = []
    for item in nav_items:
        title = item["title"]
        key = get_menu_key(item)
        if key == active_key:
            link = f"**{title}**"
        else:
            if item.get("type") == "link" and "link" in item:
                target = item["link"]
            else:
                target = item["file"]
            link = f"[{title}]({target})"
        links.append(link)
    return " • ".join(links)


def get_sitemap_content(nav_items: List[Dict[str, Any]], active_key: str) -> str:
    lines = []
    for item in nav_items:
        title = item["title"]
        key = get_menu_key(item)
        if key == active_key:
            lines.append(f"- **{title}**")
        else:
            if item.get("type") == "link" and "link" in item:
                target = item["link"]
            else:
                target = item["file"]
            lines.append(f"- [{title}]({target})")
    return "\n".join(lines)


def _is_subpath(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def make_relative_path(path: Path, start: Path) -> Path:
    """Safely compute relative path, falling back to os.path.relpath if needed."""
    if path.is_absolute() and _is_subpath(path, start):
        return path.relative_to(start)
    else:
        return Path(os.path.relpath(path, start))


def generate_gallery_content(
    item: Dict[str, Any],
    global_media_dir: Path,
    template_media_dir: Path,
    media_previews: Dict[str, str],
    config_dir: Path,
    output_file_path: Path,
) -> str:
    media_dir_str = item.get("media_dir")
    if media_dir_str:
        media_dir = resolve_path(media_dir_str, config_dir)
    else:
        media_dir = global_media_dir

    if not media_dir.exists():
        return f"⚠️ Media directory not found: {media_dir}"

    preview_map = {k.lower(): v for k, v in media_previews.items()}
    files_by_stem = defaultdict(list)
    for f in media_dir.iterdir():
        if f.is_file():
            files_by_stem[f.stem].append(f)

    gallery_entries = []
    handled_stems = set()

    for stem, file_list in files_by_stem.items():
        image_files = [f for f in file_list if f.suffix.lower() in IMAGE_EXTENSIONS]
        other_files = [f for f in file_list if f.suffix.lower() not in IMAGE_EXTENSIONS]
        if image_files and other_files:
            gallery_entries.append((image_files[0], other_files[0]))
            handled_stems.add(stem)

    for stem, file_list in files_by_stem.items():
        if stem in handled_stems:
            continue
        for f in file_list:
            if f.suffix.lower() in IMAGE_EXTENSIONS:
                gallery_entries.append((f, None))
            else:
                ext = f.suffix.lower()[1:]
                if ext in preview_map:
                    preview_name = preview_map[ext]
                    preview_path = template_media_dir / preview_name
                    if preview_path.exists():
                        gallery_entries.append((preview_path, f))

    if not gallery_entries:
        return "📭 No images or supported media files found."

    lines = [f"# {item['title']}\n"]
    columns = item.get("columns", 1)
    show_filename = item.get("show-filename", False)
    create_link = item.get("create-link", False)
    rel_root = output_file_path.parent

    if columns == 1:
        for preview, target in gallery_entries:
            rel_preview = make_relative_path(preview, rel_root)
            alt_text = preview.name
            if target:
                rel_target = make_relative_path(target, rel_root)
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
            rel_preview = make_relative_path(preview, rel_root)
            alt_text = preview.name
            if target:
                rel_target = make_relative_path(target, rel_root)
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
        description="Generate navigable Markdown documentation with templates and media previews."
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
        "--template-media-dir",
        type=Path,
        help="Directory for media preview templates (e.g., video.jpg for .mp4 files)",
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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (shows resolved paths and processing details)",
    )
    args = parser.parse_args()

    if args.verbose:
        verbose.on()

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
        print("⚠️  'nav' block is deprecated. Use 'docs' instead.")
        content_block = nav_block
        block_name = "nav (deprecated)"
    else:
        raise ValueError("❌ Config must contain 'docs' or 'nav' block.")

    # Resolve directories relative to config_dir
    docs_dir = resolve_path(
        str(args.docs_dir or config.get("docs_dir", config_dir)), config_dir
    )
    templates_dir = resolve_path(
        str(args.templates_dir or config.get("templates_dir", docs_dir)), config_dir
    )
    out_dir = resolve_path(
        str(args.out_dir or config.get("out_dir", ".")), config_dir
    )
    media_dir = resolve_path(
        str(args.media_dir or config.get("media_dir", config_dir / "media")), config_dir
    )
    template_media_dir = resolve_path(
        str(args.template_media_dir or config.get("template_media_dir", templates_dir / "media-icons")),
        config_dir
    )

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    # Template & media config
    template_config = config.get("template", {})
    global_template_file = template_config.get("template")
    media_previews = config.get("media_previews", {})

    if media_previews and not args.dry_run:
        if not template_media_dir.exists():
            print(f"⚠️  template_media_dir not found (required for media_previews): {template_media_dir}")

    # Verbose output
    verbose.print("📍 Resolved paths:")
    verbose.print(f"   config_path        : {config_path}")
    verbose.print(f"   config_dir         : {config_dir}")
    verbose.print(f"   docs_dir           : {docs_dir}")
    verbose.print(f"   templates_dir      : {templates_dir}")
    verbose.print(f"   out_dir            : {out_dir}")
    verbose.print(f"   media_dir          : {media_dir}")
    verbose.print(f"   template_media_dir : {template_media_dir}")

    if media_previews:
        verbose.print("\n🖼️  Media preview mappings:")
        for ext, preview in media_previews.items():
            verbose.print(f"   .{ext} → {preview}")

    verbose.print(f"\n📄 Processing {len(content_block)} docs entries:")
    for i, item in enumerate(content_block, 1):
        title = item.get('title', 'unnamed')
        file_ = item.get('file', '–')
        type_ = item.get('type', 'page')
        if type_ == 'link' and 'file' not in item:
            action = "skip (external link)"
        else:
            action = "generate"
        target = item.get('link') if type_ == 'link' and 'link' in item else file_
        verbose.print(f"   {i}. {title!r} → {target} [{type_}] → {action}")

    timestamp = datetime.now().strftime("%Y-%m-%d")
    warnings = 0

    for item in content_block:
        # Skip pure external links (no file to generate)
        if item.get("type") == "link" and "file" not in item:
            continue

        # For all other items (including 'type: link' WITH 'file'), 'file' is required
        if "file" not in item:
            print(f"⚠️  Missing 'file' in item: {item.get('title', 'unnamed')}")
            warnings += 1
            continue

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
        item_type = item.get("type")
        if item_type not in ("sitemap", "gallery"):
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
        if item_type == "sitemap":
            content = get_sitemap_content(content_block, get_menu_key(item))
        elif item_type == "gallery":
            content = generate_gallery_content(
                item,
                media_dir,
                template_media_dir,
                media_previews,
                config_dir,
                output_file,
            )

        # Build context
        menu_str = get_menu_content(content_block, get_menu_key(item))
        sitemap_str = get_sitemap_content(content_block, get_menu_key(item))

        context = {
            "frontmatter": frontmatter or "",
            "menu": menu_str,
            "content": content,
            "timestamp": timestamp,
            "sitemap": sitemap_str,
        }

        # Expand placeholders
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
    try:
        main()
    except ValueError as e:
        if "Invalid YAML" in str(e) or "Config file not found" in str(e):
            print(e, file=sys.stderr)
            sys.exit(1)
        else:
            raise