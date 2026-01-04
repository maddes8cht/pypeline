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
- Custom template fragments via 'templates' section in _config.yml
- Reserved names protected
- GLOBAL PLACEHOLDERS like {timestamp} work everywhere
- NEW: --list-placeholders to list all available template placeholders
- NEW: {gallery} placeholder for flexible gallery placement (backward compatible)
- FIXED: Non-deterministic {gallery} behavior — now always replaced

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

# -------------------------------------------------------------------------
# UTF-8 Encoding Fix for Pipes on Windows
# -------------------------------------------------------------------------
# Forces UTF-8 for stdout and stderr to prevent UnicodeEncodeErrors when using pipes
# (e.g., | grep, > file) on Windows.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

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

# Context-dependent placeholders (replaced during template expansion)
CONTEXT_PLACEHOLDERS = {"frontmatter", "menu", "content", "sitemap"}

# Page-specific placeholders (replaced globally at the end, per-page)
PAGE_PLACEHOLDERS = {"gallery"}

# Global placeholders (same for all pages, replaced at the very end)
GLOBAL_PLACEHOLDERS = {"timestamp"}

# Hardcoded standard fragments (auto-loaded as {name}.md)
STANDARD_FRAGMENTS = {"header", "footer", "special"}

# Combined reserved names: context + global + standard fragments
# 'gallery' is not reserved as a custom template name
RESERVED_TEMPLATE_NAMES = CONTEXT_PLACEHOLDERS | GLOBAL_PLACEHOLDERS | STANDARD_FRAGMENTS

# Descriptions for built-in placeholders
BUILTIN_PLACEHOLDER_DESCRIPTIONS = {
    "timestamp": "current date (YYYY-MM-DD)",
    "frontmatter": "original YAML frontmatter block (if present)",
    "menu": "horizontal navigation bar (•-separated)",
    "sitemap": "vertical list of all pages (with links)",
    "content": "main body content of the current page",
    "gallery": "media gallery (rendered if media_dir or type: gallery is defined)",
    "header": "loaded from templates/header.md",
    "footer": "loaded from templates/footer.md",
    "special": "loaded from templates/special.md",
}


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


def list_placeholders(config_path_arg: Optional[Path]) -> None:
    """List all available placeholders (built-in and custom)."""
    print("Built-in placeholders (available everywhere):")
    all_builtin = sorted(CONTEXT_PLACEHOLDERS | PAGE_PLACEHOLDERS | GLOBAL_PLACEHOLDERS | STANDARD_FRAGMENTS)
    for ph in all_builtin:
        desc = BUILTIN_PLACEHOLDER_DESCRIPTIONS.get(ph, "no description")
        print(f"  {{{ph}}}{' ' * (18 - len(ph))}→ {desc}")

    # Try to load config to show custom placeholders
    config_path = None
    if config_path_arg:
        if config_path_arg.is_dir():
            config_path = config_path_arg / "_config.yml"
        else:
            config_path = config_path_arg
    else:
        config_path = Path.cwd() / "_config.yml"

    custom_fragments = {}
    templates_dir = Path.cwd()  # Fallback
    config_found = False
    if config_path and config_path.exists():
        try:
            config = load_config(config_path)
            config_dir = config_path.parent

            # Resolve templates_dir from config
            docs_dir = config.get("docs_dir", config_dir)
            templates_dir = config.get("templates_dir", docs_dir)
            templates_dir = resolve_path(str(templates_dir), config_dir)

            if "templates" in config:
                for frag_def in config["templates"]:
                    if isinstance(frag_def, dict) and len(frag_def) == 1:
                        name, filename = next(iter(frag_def.items()))
                        if name in (RESERVED_TEMPLATE_NAMES - {"gallery"}):
                            continue
                        custom_fragments[name] = filename
                config_found = True
        except Exception:
            pass

    print("\nCustom placeholders (from _config.yml):")
    if custom_fragments:
        for name, filename in sorted(custom_fragments.items()):
            full_path = templates_dir / filename
            suffix = "    (file missing)" if not full_path.exists() else ""
            print(f"  {{{name}}}{' ' * (18 - len(name))}→ templates/{filename}{suffix}")
    else:
        if config_found:
            print("  none defined")
        else:
            print("  none (no _config.yml loaded)")


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

    lines = []
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
    custom_fragments: Dict[str, str],
    depth: int = 0,
) -> str:
    if depth > 3:
        return template

    # Replace CONTEXT_PLACEHOLDERS (during template expansion)
    for placeholder in CONTEXT_PLACEHOLDERS:
        if f"{{{placeholder}}}" in template:
            value = context.get(placeholder, "")
            template = template.replace(f"{{{placeholder}}}", value)

    # Combine standard and custom fragments
    all_fragments = {}
    for name in STANDARD_FRAGMENTS:
        all_fragments[name] = f"{name}.md"
    all_fragments.update(custom_fragments)

    for frag_name, frag_file_name in all_fragments.items():
        if f"{{{frag_name}}}" in template:
            frag_file = templates_dir / frag_file_name
            if frag_file.exists():
                frag_content = frag_file.read_text(encoding="utf-8")
                frag_context = context.copy()
                frag_expanded = expand_placeholders(
                    frag_content,
                    frag_context,
                    templates_dir,
                    nav_items,
                    active_file,
                    custom_fragments,
                    depth + 1
                )
                template = template.replace(f"{{{frag_name}}}", frag_expanded)
            else:
                template = template.replace(f"{{{frag_name}}}", f"⚠️ {frag_file_name} not found")

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
    parser.add_argument(
        "--list-placeholders",
        action="store_true",
        help="List all available template placeholders (built-in and custom)",
    )
    args = parser.parse_args()

    if args.list_placeholders:
        list_placeholders(args.config)
        sys.exit(0)

    if args.verbose:
        verbose.on()

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

    custom_fragments = {}
    if "templates" in config:
        for frag_def in config["templates"]:
            if isinstance(frag_def, dict) and len(frag_def) == 1:
                name, filename = next(iter(frag_def.items()))
                if name in RESERVED_TEMPLATE_NAMES:
                    raise ValueError(
                        f"❌ Reserved template name not allowed: '{name}'\n"
                        f"   → Reserved names: {sorted(RESERVED_TEMPLATE_NAMES)}"
                    )
                custom_fragments[name] = filename
            else:
                raise ValueError(
                    f"❌ Invalid template entry: {frag_def}\n"
                    f"   → Expected format: '- name: filename.md'"
                )

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

    template_config = config.get("template", {})
    global_template_file = template_config.get("template")
    media_previews = config.get("media_previews", {})

    if media_previews and not args.dry_run:
        if not template_media_dir.exists():
            print(f"⚠️  template_media_dir not found (required for media_previews): {template_media_dir}")

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

    base_timestamp = datetime.now().strftime("%Y-%m-%d")
    warnings = 0

    for item in content_block:
        if item.get("type") == "link" and "file" not in item:
            continue

        if "file" not in item:
            print(f"⚠️  Missing 'file' in item: {item.get('title', 'unnamed')}")
            warnings += 1
            continue

        file_name = item["file"]
        output_file = out_dir / file_name

        page_template_file = item.get("template", global_template_file)
        try:
            template_content = load_template_file(templates_dir, page_template_file)
        except FileNotFoundError as e:
            print(f"⚠️  {e}")
            warnings += 1
            template_content = "{frontmatter}\n{menu}\n{content}\n{menu}"

        # ALWAYS load source file content (even for gallery)
        item_type = item.get("type")
        source_file = docs_dir / file_name
        if source_file.exists():
            raw_content = source_file.read_text(encoding="utf-8")
            frontmatter, body = extract_frontmatter(raw_content)
            content = body.strip()
        else:
            if item_type != "gallery":
                print(f"⚠️  MISSING SOURCE: {source_file}")
                warnings += 1
            frontmatter = None
            content = ""

        # Special handling for sitemap
        if item_type == "sitemap":
            content = get_sitemap_content(content_block, get_menu_key(item))

        # Generate gallery content if applicable
        has_gallery_config = (item_type == "gallery") or ("media_dir" in item)
        gallery_content = ""
        if has_gallery_config:
            gallery_content = generate_gallery_content(
                item,
                media_dir,
                template_media_dir,
                media_previews,
                config_dir,
                output_file,
            )

        # Backward compatibility: if type=gallery and no {gallery} in content, replace entire content
        if item_type == "gallery" and "{gallery}" not in content:
            # Add title header only in backward-compatible mode
            gallery_with_title = f"# {item['title']}\n\n{gallery_content}"
            content = gallery_with_title
        else:
            # In flexible mode, gallery_content has no title – user controls headings
            pass

        menu_str = get_menu_content(content_block, get_menu_key(item))
        sitemap_str = get_sitemap_content(content_block, get_menu_key(item))

        context = {
            "frontmatter": frontmatter or "",
            "menu": menu_str,
            "content": content,
            "sitemap": sitemap_str,
            "gallery": gallery_content,  # Always provide it
        }

        final_content = expand_placeholders(
            template_content,
            context,
            templates_dir,
            content_block,
            file_name,
            custom_fragments
        )

        # 🔥 FINAL STEP 1: Replace page-specific placeholders (like {gallery})
        for ph in PAGE_PLACEHOLDERS:
            placeholder_str = f"{{{ph}}}"
            if placeholder_str in final_content:
                value = context.get(ph, "")
                final_content = final_content.replace(placeholder_str, value)

        # 🔥 FINAL STEP 2: Replace global placeholders (like {timestamp})
        for ph in GLOBAL_PLACEHOLDERS:
            placeholder_str = f"{{{ph}}}"
            if placeholder_str in final_content:
                if ph == "timestamp":
                    value = base_timestamp
                else:
                    value = ""
                final_content = final_content.replace(placeholder_str, value)

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
        if "Invalid YAML" in str(e) or "Config file not found" in str(e) or "Reserved template name" in str(e):
            print(e, file=sys.stderr)
            sys.exit(1)
        else:
            raise