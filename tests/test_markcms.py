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
