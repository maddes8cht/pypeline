import pytest


@pytest.fixture
def sample_cmd_file(tmp_path):
    content = (
        ':: cmd  : test_script.py\n'
        ':: env  : default\n'
        ':: This is a help comment\n'
        '@echo off\n'
        '"python" "C:\\scripts\\test_script.py" %*\n'
    )
    f = tmp_path / "test_script.cmd"
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def sample_cmd_file_with_env(tmp_path):
    content = (
        ':: cmd  : test_script.py\n'
        ':: env-name: myenv\n'
        ':: Help text\n'
        '@echo off\n'
        '"C:\\conda\\envs\\myenv\\python.exe" "C:\\scripts\\test_script.py" %*\n'
    )
    f = tmp_path / "test_script.cmd"
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def sample_script_file(tmp_path):
    f = tmp_path / "myscript.py"
    f.write_text('print("hello")', encoding="utf-8")
    return f


@pytest.fixture
def markcms_config_yml(tmp_path):
    content = (
        'docs_dir: docs\n'
        'templates_dir: templates\n'
        'out_dir: out\n'
        'docs:\n'
        '  - title: Home\n'
        '    file: index.md\n'
        '  - title: About\n'
        '    file: about.md\n'
        'templates:\n'
        '  - sidebar: sidebar.md\n'
    )
    f = tmp_path / "_config.yml"
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def markcms_config_with_tabs(tmp_path):
    content = '\tkey: value\n'
    f = tmp_path / "_config_bad.yml"
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def sample_md_file(tmp_path):
    content = (
        '---\n'
        'title: Test Page\n'
        '---\n'
        '# Test\n'
        'Some content here.\n'
    )
    f = tmp_path / "test.md"
    f.write_text(content, encoding="utf-8")
    return f
