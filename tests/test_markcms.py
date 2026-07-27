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
        assert "*" in result

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
        assert "](" in result


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
