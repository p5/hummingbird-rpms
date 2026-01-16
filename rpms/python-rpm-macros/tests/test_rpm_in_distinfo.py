from pathlib import Path

import os
import pytest
import subprocess

@pytest.fixture
def create_test_files(tmp_path):
    def _create(subpath, installer_content):
        dir_path = tmp_path / subpath
        dir_path.mkdir(parents=True, exist_ok=True)
        installer_file = dir_path / "INSTALLER"
        installer_file.write_text(installer_content)
        record_file = dir_path / "RECORD"
        record_file.write_text("dummy content in RECORD file\n")
        return dir_path
    return _create

testdata = [
    ("usr/lib/python3.13/site-packages/zipp-3.19.2.dist-info/", "pip\n", "rpm\n", False),
    ("usr/lib64/python3.13/site-packages/zipp-3.19.2.dist-info/", "pip\n", "rpm\n", False),
    ("usr/lib/python3.13/site-packages/setuptools/_vendor/zipp-3.19.2.dist-info/", "pip\n", "pip\n", True),
    ("usr/lib64/python3.13/site-packages/setuptools/_vendor/zipp-3.19.2.dist-info/", "pip\n", "pip\n", True),
    ("usr/lib/python3.13/site-packages/zipp-3.19.2.dist-info/","not pip in INSTALLER\n", "not pip in INSTALLER\n", True),
    ("usr/lib64/python3.13/site-packages/zipp-3.19.2.dist-info/","not pip in INSTALLER\n", "not pip in INSTALLER\n", True),
]
@pytest.mark.parametrize("path, installer_content, expected_installer_content, record_file_exists", testdata)
def test_installer_file_was_correctly_modified(monkeypatch, create_test_files,
path, installer_content, expected_installer_content, record_file_exists):
    script_path = Path("/usr/lib/rpm/redhat/brp-python-rpm-in-distinfo")
    tmp_dir = create_test_files(path, installer_content)
    monkeypatch.setenv("RPM_BUILD_ROOT", str(tmp_dir))
    result = subprocess.run(
        [script_path],
        capture_output=True, text=True
    )

    assert result.returncode == 0
    assert (Path(tmp_dir) / "INSTALLER").read_text() == expected_installer_content
    assert Path(tmp_dir / "RECORD").exists() is record_file_exists

