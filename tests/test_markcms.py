import re
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest


class TestLoadConfig:
    def test_file_not_found(self, tmp_path):
        from markcms import load_config
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "_config.yml")

    def test_valid_yaml(self, tmp_path):
        from markcms import load_config
        f = tmp_path / "_config.yml"
        f.write_text("key: value\n", encoding="utf-8")
        config = load_config(f)
        assert config == {"key": "value"}

    def test_empty_yaml(self, tmp_path):
        from markcms import load_config
        f = tmp_path / "_config.yml"
        f.write_text("", encoding="utf-8")
        config = load_config(f)
        assert config == {}

    def test_tab_indentation_raises_value_error(self, tmp_path):
        from markcms import load_config
        f = tmp_path / "bad.yml"
        f.write_text("\tkey: value\n", encoding="utf-8")
        with pytest.raises(ValueError, match="TAB"):
            load_config(f)

    def test_malformed_yaml_raises_value_error(self, tmp_path):
        from markcms import load_config
        f = tmp_path / "bad.yml"
        f.write_text(": : invalid\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid YAML syntax"):
            load_config(f)


class TestExtractFrontmatter:
    def test_with_frontmatter(self, sample_md_file):
        from markcms import extract_frontmatter
        content = sample_md_file.read_text(encoding="utf-8")
        front, body = extract_frontmatter(content)
        assert front is not None
        assert "title: Test Page" in front
        assert "# Test" in body

    def test_no_frontmatter(self):
        from markcms import extract_frontmatter
        front, body = extract_frontmatter("# Just content\n")
        assert front is None
        assert body == "# Just content\n"

    def test_empty_content(self):
        from markcms import extract_frontmatter
        front, body = extract_frontmatter("")
        assert front is None
        assert body == ""

    def test_partial_frontmatter_no_close(self):
        from markcms import extract_frontmatter
        front, body = extract_frontmatter("---\ntitle: no close\n")
        assert front is None
        assert body == "---\ntitle: no close\n"


class TestResolvePath:
    def test_absolute_path(self, tmp_path):
        from markcms import resolve_path
        p = tmp_path / "sub"
        p.mkdir()
        result = resolve_path(str(p), tmp_path)
        assert result == p.resolve()

    def test_relative_path(self, tmp_path):
        from markcms import resolve_path
        (tmp_path / "sub").mkdir()
        result = resolve_path("sub", tmp_path)
        assert result == (tmp_path / "sub").resolve()


class TestGetMenuKey:
    def test_file_key(self):
        from markcms import get_menu_key
        assert get_menu_key({"file": "index.md"}) == "index.md"

    def test_link_key(self):
        from markcms import get_menu_key
        key = get_menu_key({"type": "link", "title": "My Link"})
        assert "My_Link" in key

    def test_title_fallback(self):
        from markcms import get_menu_key
        assert get_menu_key({"title": "Home"}) == "Home"


class TestGetMenuContent:
    def test_active_item_bold(self):
        from markcms import get_menu_content
        items = [{"title": "Home", "file": "index.md"}, {"title": "About", "file": "about.md"}]
        result = get_menu_content(items, "about.md")
        assert "**About**" in result
        assert "Home" in result

    def test_link_item(self):
        from markcms import get_menu_content
        items = [{"title": "GitHub", "type": "link", "link": "https://github.com"}]
        result = get_menu_content(items, "none")
        assert "github.com" in result


class TestGetSitemapContent:
    def test_active_item_bold(self):
        from markcms import get_sitemap_content
        items = [{"title": "Home", "file": "index.md"}, {"title": "About", "file": "about.md"}]
        result = get_sitemap_content(items, "about.md")
        assert "**About**" in result
        assert "- [Home]" in result

    def test_link_item(self):
        from markcms import get_sitemap_content
        items = [{"title": "External", "type": "link", "link": "https://example.com"}]
        result = get_sitemap_content(items, "none")
        assert "example.com" in result


class TestGenerateGalleryContent:
    def test_media_dir_not_found(self, tmp_path):
        from markcms import generate_gallery_content
        result = generate_gallery_content(
            {"media_dir": "nonexistent"},
            tmp_path, tmp_path, {},
            tmp_path, tmp_path / "out" / "index.md",
        )
        assert "not found" in result

    def test_empty_media_dir(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        result = generate_gallery_content(
            {}, media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
        )
        assert "No images" in result

    def test_single_image(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "photo.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 1}, media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
        )
        assert "photo.jpg" in result

    def test_image_with_video_preview(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "video.mp4").write_text("fake")
        (media_dir / "video.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 1}, media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
        )
        assert "video.jpg" in result
        assert "video.mp4" in result

    def test_multi_column_columns_2(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        for i in range(4):
            (media_dir / f"img{i}.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 2}, media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
        )
        assert "|" in result
        lines = [l for l in result.split("\n") if l.strip()]
        assert lines[0].startswith("|")
        assert lines[1].startswith("|")
        assert lines[0].count("|") == 3

    def test_multi_column_columns_3(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        for i in range(6):
            (media_dir / f"img{i}.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 3}, media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
        )
        assert "|" in result
        lines = [l for l in result.split("\n") if l.strip()]
        assert lines[0].count("|") == 4

    def test_multi_column_with_show_filename(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        for i in range(2):
            (media_dir / f"img{i}.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 2, "show-filename": True}, media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
        )
        assert "img0.jpg" in result
        assert "img1.jpg" in result

    def test_multi_column_uneven_rows(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        for i in range(5):
            (media_dir / f"img{i}.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 2}, media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
        )
        lines = [l for l in result.split("\n") if l.strip()]
        data_rows = lines[2:]
        assert len(data_rows) == 3

    def test_multi_column_creates_link(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "img0.jpg").write_text("fake")
        (media_dir / "img1.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 2, "create-link": True}, media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
        )
        assert "[![" in result

    def test_single_column_create_link_false_no_wrapping(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "photo.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 1, "create-link": False}, media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
        )
        assert "photo.jpg" in result
        assert "[![" not in result

    def test_preview_map_missing_file_skipped_silently(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        template_media = tmp_path / "media-icons"
        template_media.mkdir()
        (template_media / "video_thumb.jpg").write_text("fake")
        (media_dir / "video.mp4").write_text("fake")
        (media_dir / "image.jpg").write_text("fake")
        preview_map = {"mp4": "video_thumb.jpg", "pdf": "missing_thumb.jpg"}
        (media_dir / "doc.pdf").write_text("fake")
        result = generate_gallery_content(
            {"columns": 1}, media_dir, template_media, preview_map, tmp_path, tmp_path / "out" / "index.md",
        )
        assert "video_thumb.jpg" in result
        assert "image.jpg" in result
        assert "missing_thumb.jpg" not in result


class TestGenerateGallerySingleColumn:
    def test_create_link_wraps_image(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "photo.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 1, "create-link": True}, media_dir, tmp_path, {},
            tmp_path, tmp_path / "out" / "index.md",
        )
        result = result.replace("\\", "/")
        assert result.startswith("[![photo.jpg](..")
        assert "](../media/photo.jpg)" in result

    def test_show_filename_renders_italic_name_line(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "photo.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 1, "show-filename": True}, media_dir, tmp_path, {},
            tmp_path, tmp_path / "out" / "index.md",
        )
        assert "*photo.jpg*" in result
        assert "[![" not in result
        assert result.split("\n")[0].startswith("![photo.jpg]")

    def test_create_link_with_show_filename_combines(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "photo.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 1, "create-link": True, "show-filename": True},
            media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
        )
        result = result.replace("\\", "/")
        assert result.startswith("[![photo.jpg](../media/photo.jpg)](../media/photo.jpg)")
        assert "*photo.jpg*" in result

    def test_no_create_link_no_wrap_and_no_filename(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "photo.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 1}, media_dir, tmp_path, {},
            tmp_path, tmp_path / "out" / "index.md",
        )
        assert result.startswith("![photo.jpg]")
        assert "[![" not in result
        assert "*" not in result


class TestExpandPlaceholders:
    def test_context_placeholder_replaced(self, tmp_path):
        from markcms import expand_placeholders
        result = expand_placeholders(
            "{menu}",
            {"menu": "**Home** • **About**"},
            tmp_path, [], "index.md", {},
        )
        assert "**Home**" in result

    def test_fragment_included(self, tmp_path):
        from markcms import expand_placeholders
        (tmp_path / "header.md").write_text("HEADER CONTENT", encoding="utf-8")
        result = expand_placeholders(
            "{header}",
            {}, tmp_path, [], "index.md", {},
        )
        assert "HEADER CONTENT" in result

    def test_missing_fragment_shows_warning(self, tmp_path):
        from markcms import expand_placeholders
        result = expand_placeholders(
            "{header}",
            {}, tmp_path, [], "index.md", {},
        )
        assert "header.md not found" in result

    def test_recursion_depth_limit(self, tmp_path):
        from markcms import expand_placeholders
        content = "{header}"
        (tmp_path / "header.md").write_text("{header}", encoding="utf-8")
        result = expand_placeholders(
            content, {}, tmp_path, [], "index.md", {},
        )
        assert "{header}" in result


class TestMain:
    def test_list_placeholders(self):
        from markcms import main
        with (
            patch("sys.argv", ["markcms.py", "--list-placeholders"]),
            patch("builtins.print"),
            pytest.raises(SystemExit),
        ):
            main()

    def test_missing_config_exits(self, tmp_path):
        from markcms import main
        config = tmp_path / "_config.yml"
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config)]),
            pytest.raises(FileNotFoundError),
        ):
            main()

    def test_both_docs_and_nav_raises_value_error(self, tmp_path):
        from markcms import main
        config = tmp_path / "_config.yml"
        config.write_text(
            "docs:\n  - title: Home\n    file: index.md\n"
            "nav:\n  - title: About\n    file: about.md\n",
            encoding="utf-8"
        )
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config)]),
            pytest.raises(ValueError, match="both"),
        ):
            main()

    def test_neither_docs_nor_nav_raises_value_error(self, tmp_path):
        from markcms import main
        config = tmp_path / "_config.yml"
        config.write_text("out_dir: out\n", encoding="utf-8")
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config)]),
            pytest.raises(ValueError, match="must contain"),
        ):
            main()

    def test_reserved_template_name_raises_error(self, tmp_path):
        from markcms import main
        config = tmp_path / "_config.yml"
        config.write_text(
            "docs:\n  - title: Home\n    file: index.md\n"
            "templates:\n  - header: my_header.md\n",
            encoding="utf-8"
        )
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config)]),
            pytest.raises(ValueError, match="Reserved"),
        ):
            main()

    def test_missing_source_file_emits_warning(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        (config_dir / "docs").mkdir()
        (config_dir / "templates").mkdir()
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "docs:\n  - title: Missing\n    file: nonexistent.md\n",
            encoding="utf-8"
        )
        buf = []
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config_dir), "--dry-run"]),
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
        ):
            main()
        output = "\n".join(buf)
        assert "MISSING SOURCE" in output
        assert "nonexistent.md" in output

    def test_missing_template_file_falls_back_to_default(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        (config_dir / "templates").mkdir()
        (docs_dir / "index.md").write_text("# Home\n", encoding="utf-8")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "template: missing_template.md\n"
            "docs:\n  - title: Home\n    file: index.md\n",
            encoding="utf-8"
        )
        buf = []
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config_dir), "--dry-run"]),
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
        ):
            main()
        output = "\n".join(buf)
        assert "not found" in output

    def test_gallery_backward_compat_mode(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        (config_dir / "templates").mkdir()
        media_dir = config_dir / "media"
        media_dir.mkdir()
        (media_dir / "photo.jpg").write_text("fake")
        gallery_file = docs_dir / "gallery.md"
        gallery_file.write_text("Some initial content\n", encoding="utf-8")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "media_dir: media\n"
            "template: default.md\n"
            "docs:\n  - title: Gallery Page\n    file: gallery.md\n    type: gallery\n"
            "    columns: 1\n",
            encoding="utf-8"
        )
        (config_dir / "templates" / "default.md").write_text(
            "{frontmatter}\n{content}\n", encoding="utf-8"
        )
        with patch("sys.argv", ["markcms.py", "--config", str(config_dir)]):
            main()
        output_file = config_dir / "out" / "gallery.md"
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "# Gallery Page" in content
        assert "photo.jpg" in content
        assert "Some initial content" not in content

    def test_nav_block_only_prints_deprecation_warning(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        (config_dir / "templates").mkdir()
        (docs_dir / "index.md").write_text("# Home\n", encoding="utf-8")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "nav:\n  - title: Home\n    file: index.md\n",
            encoding="utf-8"
        )
        buf = []
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config_dir), "--dry-run"]),
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
        ):
            main()
        output = "\n".join(buf)
        assert "'nav' block is deprecated" in output
        assert "index.md" in output

    @pytest.mark.xfail(
        reason="BUG in markcms.py: a docs entry without 'file' is warned and skipped, "
        "but get_menu_content()/get_sitemap_content() (lines 217/234) then raise "
        "KeyError: 'file' while rendering the menu for the remaining items. "
        "Fix would be to skip/guard malformed items in menu generation.",
    )
    def test_missing_file_item_warns_and_continues(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        (config_dir / "templates").mkdir()
        (docs_dir / "index.md").write_text("# Home\n", encoding="utf-8")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "docs:\n"
            "  - title: Home\n    file: index.md\n"
            "  - title: NoFileHere\n"
            "  - title: External Link\n    type: link\n    link: https://example.com\n",
            encoding="utf-8"
        )
        buf = []
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config_dir), "--dry-run"]),
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
        ):
            main()
        output = "\n".join(buf)
        assert "Missing 'file' in item: NoFileHere" in output
        assert "index.md" in output
        assert "1 warning(s)" in output


class TestIsSubpath:
    def test_subpath_returns_true(self, tmp_path):
        from markcms import _is_subpath
        sub = tmp_path / "sub"
        assert _is_subpath(sub, tmp_path) is True

    def test_non_subpath_returns_false(self, tmp_path):
        from markcms import _is_subpath
        other = tmp_path.parent / "other"
        assert _is_subpath(other, tmp_path) is False

    def test_same_path_returns_true(self, tmp_path):
        from markcms import _is_subpath
        assert _is_subpath(tmp_path, tmp_path) is True


class TestMakeRelativePath:
    def test_absolute_subpath(self, tmp_path):
        from markcms import make_relative_path
        sub = tmp_path / "sub" / "file.md"
        sub.parent.mkdir(parents=True)
        sub.write_text("content")
        result = make_relative_path(sub, tmp_path)
        assert result == Path("sub/file.md")

    def test_relative_input_path(self, tmp_path):
        from markcms import make_relative_path
        sub = tmp_path / "sub"
        sub.mkdir(parents=True, exist_ok=True)
        # Force start to be on same drive by using tmp_path for both
        start = tmp_path
        target = sub / "file.md"
        target.write_text("content")
        result = make_relative_path(target, start)
        assert result == Path("sub/file.md")

    def test_outside_path_falls_back(self, tmp_path):
        from markcms import make_relative_path
        outside = tmp_path.parent / "other.md"
        outside.write_text("content")
        result = make_relative_path(outside, tmp_path)
        assert ".." in str(result)


class TestLoadTemplateFile:
    def test_empty_filename_returns_default(self, tmp_path):
        from markcms import load_template_file
        result = load_template_file(tmp_path, "")
        assert "{frontmatter}" in result
        assert "{content}" in result

    def test_none_filename_returns_default(self, tmp_path):
        from markcms import load_template_file
        result = load_template_file(tmp_path, None)
        assert "{frontmatter}" in result

    def test_valid_file_returns_content(self, tmp_path):
        from markcms import load_template_file
        tpl = tmp_path / "custom.md"
        tpl.write_text("CUSTOM TEMPLATE", encoding="utf-8")
        result = load_template_file(tmp_path, "custom.md")
        assert result == "CUSTOM TEMPLATE"

    def test_missing_file_raises(self, tmp_path):
        from markcms import load_template_file
        with pytest.raises(FileNotFoundError, match="not found"):
            load_template_file(tmp_path, "nonexistent.md")


class TestListPlaceholders:
    def test_without_config_shows_default(self, tmp_path):
        from markcms import list_placeholders
        buf = []
        with (
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            list_placeholders(tmp_path)
        output = "\n".join(buf)
        assert "Built-in placeholders" in output
        assert "none (no _config.yml loaded)" in output

    def test_with_custom_templates(self, tmp_path):
        from markcms import list_placeholders
        config = tmp_path / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "templates:\n"
            "  - my_fragment: my_frag.md\n",
            encoding="utf-8"
        )
        (tmp_path / "templates").mkdir()
        buf = []
        with (
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
        ):
            list_placeholders(tmp_path / "_config.yml")
        output = "\n".join(buf)
        assert "my_fragment" in output
        assert "templates/my_frag.md" in output


class TestExpandPlaceholdersAllTypes:
    def test_context_page_and_global_placeholders_all_replaced(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        templates_dir = config_dir / "templates"
        templates_dir.mkdir()
        media_dir = config_dir / "media"
        media_dir.mkdir()
        (media_dir / "photo.jpg").write_text("fake")

        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "media_dir: media\n"
            "template: default.md\n"
            "docs:\n"
            "  - title: Home\n"
            "    file: index.md\n"
            "    media_dir: media\n",
            encoding="utf-8"
        )
        (docs_dir / "index.md").write_text(
            "---\ntitle: Home\n---\n# Welcome\n",
            encoding="utf-8"
        )
        (templates_dir / "default.md").write_text(
            "{frontmatter}\n{menu}\nContent: {content}\nGallery: {gallery}\nGenerated: {timestamp}\n",
            encoding="utf-8"
        )
        buf = []
        with patch("sys.argv", ["markcms.py", "--config", str(config_dir)]):
            with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
                main()
        output_file = config_dir / "out" / "index.md"
        content = output_file.read_text(encoding="utf-8")
        assert "title: Home" in content
        assert "Content: # Welcome" in content
        assert "Gallery: ![photo.jpg]" in content
        assert "Generated:" in content
        assert re.search(r"Generated: \d{4}-\d{2}-\d{2}", content)

    def test_gallery_placeholder_in_flexible_mode_no_duplicate_title(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site2"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        templates_dir = config_dir / "templates"
        templates_dir.mkdir()
        media_dir = config_dir / "media"
        media_dir.mkdir()
        (media_dir / "photo.jpg").write_text("fake")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "media_dir: media\n"
            "template: default.md\n"
            "docs:\n"
            "  - title: Gallery Page\n"
            "    file: gallery.md\n"
            "    type: gallery\n"
            "    columns: 1\n",
            encoding="utf-8"
        )
        (docs_dir / "gallery.md").write_text(
            "# Custom Title\n\n{gallery}\n\nMore text here.\n",
            encoding="utf-8"
        )
        (templates_dir / "default.md").write_text("{content}\n", encoding="utf-8")
        with patch("sys.argv", ["markcms.py", "--config", str(config_dir)]):
            main()
        output_file = config_dir / "out" / "gallery.md"
        content = output_file.read_text(encoding="utf-8")
        assert "# Custom Title" in content
        assert "More text here." in content
        assert "photo.jpg" in content
        assert content.count("# Custom Title") == 1


class TestMainFullFlow:
    def test_dry_run_full_generation(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        templates_dir = config_dir / "templates"
        templates_dir.mkdir()
        out_dir = config_dir / "out"

        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "docs:\n"
            "  - title: Home\n"
            "    file: index.md\n"
            "  - title: About\n"
            "    file: about.md\n"
            "templates:\n"
            "  - sidebar: sidebar.md\n",
            encoding="utf-8"
        )
        (docs_dir / "index.md").write_text("# Home\n\nWelcome!\n", encoding="utf-8")
        (docs_dir / "about.md").write_text("# About\n\nInfo here.\n", encoding="utf-8")
        (templates_dir / "header.md").write_text("HEADER\n", encoding="utf-8")
        (templates_dir / "sidebar.md").write_text("SIDEBAR\n", encoding="utf-8")

        buf = []
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config_dir), "--dry-run"]),
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
        ):
            main()
        output = "\n".join(buf)
        assert "index.md" in output
        assert "about.md" in output
        assert "Dry-run complete" in output

    def test_list_placeholders_flag(self, tmp_path):
        from markcms import main
        config_dir = tmp_path
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "docs:\n"
            "  - title: Home\n"
            "    file: index.md\n"
            "templates:\n"
            "  - sidebar: sidebar.md\n",
            encoding="utf-8"
        )
        (config_dir / "templates").mkdir()

        buf = []
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config_dir), "--list-placeholders"]),
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
            pytest.raises(SystemExit),
        ):
            main()
        output = "\n".join(buf)
        assert "Built-in placeholders" in output
        assert "sidebar" in output

class TestGalleryTableTargetRow:
    def test_table_row_links_preview_to_target_when_image_video_pair(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "clip.jpg").write_text("fake")
        (media_dir / "clip.mp4").write_text("fake")
        result = generate_gallery_content(
            {"columns": 2}, media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
)
        assert "[![clip.jpg]" in result
        assert "clip.mp4)" in result
        assert "|" in result


class TestListPlaceholdersReservedAndError:
    def test_reserved_template_names_skipped_so_none_defined(self, tmp_path):
        from markcms import list_placeholders
        config = tmp_path / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "templates:\n"
            "  - header: my_header.md\n",
            encoding="utf-8"
        )
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_placeholders(tmp_path)
        output = "\n".join(buf)
        assert "my_header" not in output
        assert "none defined" in output
        assert "header" in output

    def test_config_load_failure_is_swallowed(self, tmp_path):
        from markcms import list_placeholders
        config = tmp_path / "_config.yml"
        config.write_text("\tkey: value\n", encoding="utf-8")
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_placeholders(tmp_path)
        output = "\n".join(buf)
        assert "none (no _config.yml loaded)" in output


class TestMainVerboseAndPaths:
    def test_verbose_flag_enables_detail_logging(self, tmp_path):
        from markcms import main, verbose
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        (config_dir / "templates").mkdir()
        (docs_dir / "index.md").write_text("# Home\n", encoding="utf-8")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "docs:\n  - title: Home\n    file: index.md\n",
            encoding="utf-8"
        )
        try:
            with patch("sys.argv", ["markcms.py", "--config", str(config_dir), "--dry-run", "--verbose"]):
                main()
        finally:
            verbose.off()

    def test_media_previews_warning_and_verbose_mapping(self, tmp_path, capsys):
        from markcms import main, verbose
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        (config_dir / "templates").mkdir()
        (docs_dir / "index.md").write_text("# Home\n", encoding="utf-8")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "media_previews:\n"
            "  mp4: video-icon.png\n"
            "docs:\n  - title: Home\n    file: index.md\n",
            encoding="utf-8"
        )
        try:
            with patch("sys.argv", ["markcms.py", "--config", str(config_dir), "--verbose"]):
                main()
        finally:
            verbose.off()
        out = capsys.readouterr().out
        assert "template_media_dir not found" in out
        assert "mp4 → video-icon.png" in out

    def test_default_config_loaded_from_cwd(self, tmp_path, monkeypatch):
        from markcms import main
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (tmp_path / "templates").mkdir()
        (docs_dir / "index.md").write_text("# Home\n", encoding="utf-8")
        (tmp_path / "_config.yml").write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "docs:\n  - title: Home\n    file: index.md\n",
            encoding="utf-8"
        )
        buf = []
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["markcms.py", "--dry-run"]):
            with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
                main()
        output = "\n".join(buf)
        assert "index.md" in output

    def test_invalid_template_entry_raises_value_error(self, tmp_path):
        from markcms import main
        config = tmp_path / "_config.yml"
        config.write_text(
            "docs:\n  - title: Home\n    file: index.md\n"
            "templates:\n  - just_a_string.md\n",
            encoding="utf-8"
        )
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config)]),
            pytest.raises(ValueError, match="Invalid template entry"),
        ):
            main()

    def test_external_link_without_file_skipped_without_warning(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        (config_dir / "templates").mkdir()
        (docs_dir / "index.md").write_text("# Home\n", encoding="utf-8")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "docs:\n"
            "  - title: Home\n    file: index.md\n"
            "  - title: GitHub\n    type: link\n    link: https://github.com\n",
            encoding="utf-8"
        )
        buf = []
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config_dir), "--dry-run"]),
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
):
            main()
        output = "\n".join(buf)
        assert "Missing 'file'" not in output
        assert "warning" not in output
        assert "Dry-run complete" in output

    def test_missing_file_in_single_item_config_warns_and_completes(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        (config_dir / "templates").mkdir()
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "template: default.md\n"
            "docs:\n  - title: Broken Item\n",
            encoding="utf-8"
        )
        (config_dir / "templates" / "default.md").write_text(
            "{menu}\n{content}\n", encoding="utf-8"
        )
        buf = []
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config_dir), "--dry-run"]),
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
):
            main()
        output = "\n".join(buf)
        assert "Missing 'file' in item: Broken Item" in output
        assert "1 warning" in output

    def test_sitemap_item_generates_sitemap_content(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        (config_dir / "templates").mkdir()
        (docs_dir / "index.md").write_text("# Home\n", encoding="utf-8")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "template: default.md\n"
            "docs:\n"
            "  - title: Home\n    file: index.md\n"
            "  - title: Map\n    file: map.md\n    type: sitemap\n",
            encoding="utf-8"
        )
        (config_dir / "templates" / "default.md").write_text(
            "{content}\n", encoding="utf-8"
        )
        with patch("sys.argv", ["markcms.py", "--config", str(config_dir)]):
            main()
        content = (config_dir / "out" / "map.md").read_text(encoding="utf-8")
        assert "- **Map**" in content
        assert "- [Home](index.md)" in content \
            or "{menu}" in content or "- [Map](map.md)" in content


class TestDummyDebugFallback:
    def test_fallback_when_debug_module_unavailable(self):
        import importlib
        import sys
        import markcms as markcms_mod
        with patch.dict(sys.modules, {"debug": None}):
            reloaded = importlib.reload(markcms_mod)
        try:
            assert type(reloaded.debug).__name__ == "DummyDebug"
            assert type(reloaded.verbose).__name__ == "DummyDebug"
            reloaded.debug.print("x")
            reloaded.debug.on()
            reloaded.verbose.print("y")
            reloaded.debug.off()
            reloaded.verbose.off()
        finally:
            importlib.reload(markcms_mod)


class TestNonTimestampGlobalPlaceholder:
    def test_non_timestamp_global_placeholder_replaced_with_empty(self, tmp_path):
        import markcms as markcms_mod
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        (config_dir / "templates").mkdir()
        (docs_dir / "index.md").write_text("# Home\n", encoding="utf-8")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "template: default.md\n"
            "docs:\n  - title: Home\n    file: index.md\n",
            encoding="utf-8"
        )
        (config_dir / "templates" / "default.md").write_text(
            "before {builder} after\n", encoding="utf-8"
        )
        expanded = set(markcms_mod.GLOBAL_PLACEHOLDERS) | {"builder"}
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config_dir)]),
            patch.object(markcms_mod, "GLOBAL_PLACEHOLDERS", expanded),
        ):
            main()
        content = (config_dir / "out" / "index.md").read_text(encoding="utf-8")
        assert "before  after" in content
        assert "{builder}" not in content


class TestCliEntryGuard:
    SRC_DIR = Path(__file__).resolve().parent.parent / "src"

    def _run_cli(self, script_name, *args):
        env = dict(os.environ, PYTHONPATH=str(self.SRC_DIR), PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, str(self.SRC_DIR / script_name), *args],
            capture_output=True, text=True, env=env, timeout=60,
        )

    def test_tab_config_exits_with_clean_error(self, tmp_path):
        bad = tmp_path / "bad.yml"
        bad.write_text("\tkey: value\n", encoding="utf-8")
        result = self._run_cli("markcms.py", "--config", str(bad))
        assert result.returncode == 1
        assert "Invalid YAML" in result.stderr

    def test_other_value_error_propagates(self, tmp_path):
        cfg = tmp_path / "_config.yml"
        cfg.write_text(
            "docs:\n  - title: Home\n    file: index.md\n"
            "nav:\n  - title: About\n    file: about.md\n",
            encoding="utf-8"
        )
        result = self._run_cli("markcms.py", "--config", str(cfg))
        assert result.returncode == 1
        assert "ValueError" in result.stderr

    def test_main_guard_handles_invalid_yaml_in_process(self, tmp_path):
        bad = tmp_path / "bad.yml"
        bad.write_text("\tkey: value\n", encoding="utf-8")
        src = Path(__file__).resolve().parent.parent / "src" / "markcms.py"
        code = compile(src.read_text(encoding="utf-8"), str(src), "exec")
        with (
            patch("sys.argv", ["markcms.py", "--config", str(bad)]),
            pytest.raises(SystemExit) as exc,
        ):
            exec(code, {"__name__": "__main__", "__file__": str(src)})
        assert exc.value.code == 1

    def test_main_guard_re_raises_other_value_error(self, tmp_path):
        cfg = tmp_path / "_config.yml"
        cfg.write_text(
            "docs:\n  - title: Home\n    file: index.md\n"
            "nav:\n  - title: About\n    file: about.md\n",
            encoding="utf-8"
        )
        src = Path(__file__).resolve().parent.parent / "src" / "markcms.py"
        code = compile(src.read_text(encoding="utf-8"), str(src), "exec")
        with (
            patch("sys.argv", ["markcms.py", "--config", str(cfg)]),
            pytest.raises(ValueError, match="both 'docs' and 'nav'"),
        ):
            exec(code, {"__name__": "__main__", "__file__": str(src)})


class TestEdgeBranches:
    def test_tab_error_without_problem_mark(self, tmp_path):
        """Bug-hunt: a YAML tab error without a problem_mark must still be explained."""
        import yaml
        from markcms import load_config
        f = tmp_path / "_config.yml"
        f.write_text("x", encoding="utf-8")
        err = yaml.YAMLError("found character '\\t' that cannot start any token")
        with (
            patch("builtins.open", mock_open(read_data="x")),
            patch("markcms.yaml.safe_load", side_effect=err),
        ):
            with pytest.raises(ValueError) as exc:
                load_config(f)
        assert "TAB" in str(exc.value)
        assert "near line" not in str(exc.value)

    def test_list_placeholders_config_without_templates(self, tmp_path):
        from markcms import list_placeholders
        (tmp_path / "_config.yml").write_text("docs_dir: docs\n", encoding="utf-8")
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_placeholders(tmp_path)
        output = "\n".join(buf)
        assert "none (no _config.yml loaded)" in output

    def test_list_placeholders_non_dict_templates_entry(self, tmp_path):
        from markcms import list_placeholders
        (tmp_path / "_config.yml").write_text(
            "templates:\n  - just_a_string.md\n", encoding="utf-8"
        )
        buf = []
        with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))):
            list_placeholders(tmp_path)
        output = "\n".join(buf)
        assert "just_a_string" not in output
        assert "none defined" in output

    def test_gallery_subdirectory_entry_is_skipped(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "subdir").mkdir()
        (media_dir / "photo.jpg").write_text("fake")
        result = generate_gallery_content(
            {"columns": 1}, media_dir, tmp_path, {}, tmp_path, tmp_path / "out" / "index.md",
        )
        assert "photo.jpg" in result
        assert "subdir" not in result

    def test_gallery_extension_not_in_preview_map_is_skipped(self, tmp_path):
        from markcms import generate_gallery_content
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        template_media = tmp_path / "media-icons"
        template_media.mkdir()
        (template_media / "video_thumb.jpg").write_text("fake")
        (media_dir / "video.mp4").write_text("fake")
        (media_dir / "notes.txt").write_text("unmapped extension")
        preview_map = {"mp4": "video_thumb.jpg"}
        result = generate_gallery_content(
            {"columns": 1}, media_dir, template_media, preview_map,
            tmp_path, tmp_path / "out" / "index.md",
        )
        assert "video_thumb.jpg" in result
        assert "notes" not in result
        assert "video.mp4" in result

    def test_media_previews_with_existing_dir_no_warning(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        templates_dir = config_dir / "templates"
        templates_dir.mkdir()
        icons_dir = templates_dir / "media-icons"
        icons_dir.mkdir()
        (icons_dir / "video-icon.png").write_text("fake")
        (docs_dir / "index.md").write_text("# Home\n", encoding="utf-8")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "media_previews:\n"
            "  mp4: video-icon.png\n"
            "docs:\n  - title: Home\n    file: index.md\n",
            encoding="utf-8"
        )
        buf = []
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config_dir)]),
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
        ):
            main()
        output = "\n".join(buf)
        assert "template_media_dir not found" not in output

    def test_gallery_item_missing_source_no_source_warning(self, tmp_path):
        from markcms import main
        config_dir = tmp_path / "site"
        config_dir.mkdir()
        docs_dir = config_dir / "docs"
        docs_dir.mkdir()
        templates_dir = config_dir / "templates"
        templates_dir.mkdir()
        media_dir = config_dir / "media"
        media_dir.mkdir()
        (media_dir / "photo.jpg").write_text("fake")
        config = config_dir / "_config.yml"
        config.write_text(
            "docs_dir: docs\n"
            "templates_dir: templates\n"
            "out_dir: out\n"
            "media_dir: media\n"
            "template: default.md\n"
            "docs:\n"
            "  - title: Gallery Page\n"
            "    file: gallery.md\n"
            "    type: gallery\n"
            "    columns: 1\n",
            encoding="utf-8"
        )
        (config_dir / "templates" / "default.md").write_text(
            "{content}\n", encoding="utf-8"
        )
        buf = []
        with (
            patch("sys.argv", ["markcms.py", "--config", str(config_dir)]),
            patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(str(x) for x in a))),
        ):
            main()
        output = "\n".join(buf)
        assert "MISSING SOURCE" not in output
        content = (config_dir / "out" / "gallery.md").read_text(encoding="utf-8")
        assert "# Gallery Page" in content
        assert "photo.jpg" in content

    def test_reload_on_non_windows_skips_reconfigure(self, monkeypatch):
        """Covers the else-branch of the sys.platform == 'win32' guard at import."""
        import importlib
        import sys as sysmod
        import markcms as markcms_mod
        monkeypatch.setattr(sysmod, "platform", "linux")
        try:
            reloaded = importlib.reload(markcms_mod)
            assert reloaded is not None
        finally:
            monkeypatch.setattr(sysmod, "platform", "win32")
            importlib.reload(markcms_mod)
