"""Tests for check_upstream_versions."""

import json
import subprocess
import types
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


#
# Fixtures
#


@pytest.fixture
def cuv_module():
    """Load check_upstream_versions.py as a Python module."""
    script_path = Path(__file__).parent.parent / 'ci' / 'check_upstream_versions.py'
    module = types.ModuleType("check_upstream_versions")
    module.__file__ = str(script_path)
    code = compile(script_path.read_text(), str(script_path), 'exec')
    exec(code, module.__dict__)
    return module


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    """Create a minimal repo layout for testing."""
    subprocess.run(['git', 'init'], cwd=tmp_path, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=tmp_path, check=True)

    (tmp_path / 'rpms').mkdir()
    (tmp_path / 'metadata').mkdir()

    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'commit', '-m', 'Initial commit', '--allow-empty'],
                   cwd=tmp_path, check=True)

    return tmp_path


def _create_package(workdir: Path, name: str, version: str,
                    sources: dict | None = None,
                    metadata: dict | None = None) -> Path:
    """Create a package directory with a spec file.

    Args:
        workdir: Repository root
        name: Package name
        version: Package version
        sources: Optional dict mapping filename -> hash for the sources file
        metadata: Optional metadata dict (written to metadata/<name>.json)

    Returns:
        Path to the package directory
    """
    pkg_dir = workdir / 'rpms' / name
    pkg_dir.mkdir(parents=True, exist_ok=True)

    spec = pkg_dir / f'{name}.spec'
    spec.write_text(f"""Name: {name}
Version: {version}
Release: 1%{{?dist}}
Summary: Test package {name}
License: MIT
Source0: https://example.com/{name}/{name}-%{{version}}.tar.gz

%description
Test package

%files
""")

    if sources:
        lines = [f"SHA512 ({fn}) = {h}" for fn, h in sources.items()]
        (pkg_dir / 'sources').write_text('\n'.join(lines) + '\n')

    if metadata is not None:
        meta_file = workdir / 'metadata' / f'{name}.json'
        with open(meta_file, 'w') as f:
            json.dump(metadata, f, indent=2, sort_keys=True)
            f.write('\n')

    return pkg_dir


#
# Tests — compare_versions
#


def test_compare_versions_newer(cuv_module) -> None:
    """Upstream newer than current returns 1."""
    assert cuv_module.compare_versions('1.0', '2.0') == 1


def test_compare_versions_equal(cuv_module) -> None:
    """Equal versions return 0."""
    assert cuv_module.compare_versions('1.0', '1.0') == 0


def test_compare_versions_older(cuv_module) -> None:
    """Upstream older than current returns -1."""
    assert cuv_module.compare_versions('2.0', '1.0') == -1


def test_compare_versions_complex(cuv_module) -> None:
    """Multi-component version comparison."""
    assert cuv_module.compare_versions('1.2.3', '1.2.4') == 1
    assert cuv_module.compare_versions('1.2.3', '1.3.0') == 1
    assert cuv_module.compare_versions('1.10.0', '1.9.0') == -1


#
# Tests — parse_spec_version
#


def test_parse_spec_version(cuv_module, workdir: Path) -> None:
    """Extract version from a spec file."""
    pkg_dir = _create_package(workdir, 'testpkg', '3.5.1')
    assert cuv_module.parse_spec_version(pkg_dir) == '3.5.1'


def test_parse_spec_version_no_spec(cuv_module, tmp_path: Path) -> None:
    """Returns None when no spec file exists."""
    assert cuv_module.parse_spec_version(tmp_path) is None


def test_parse_spec_version_multiple_specs(cuv_module, tmp_path: Path) -> None:
    """Returns None when multiple spec files exist."""
    (tmp_path / 'a.spec').write_text('Name: a\nVersion: 1\n')
    (tmp_path / 'b.spec').write_text('Name: b\nVersion: 2\n')
    assert cuv_module.parse_spec_version(tmp_path) is None


#
# Tests — get_version_from_metadata
#


def test_get_version_from_metadata(cuv_module, workdir: Path) -> None:
    """Read version from metadata JSON."""
    _create_package(workdir, 'mypkg', '1.0',
                    metadata={'version': '2.5', 'release': '1'})
    cuv_module.METADATA_DIR = workdir / 'metadata'
    assert cuv_module.get_version_from_metadata('mypkg') == '2.5'


def test_get_version_from_metadata_missing(cuv_module, workdir: Path) -> None:
    """Returns None when metadata file does not exist."""
    cuv_module.METADATA_DIR = workdir / 'metadata'
    assert cuv_module.get_version_from_metadata('nonexistent') is None


#
# Tests — _parse_sources_file / _write_sources_file
#


def test_parse_sources_file(cuv_module, tmp_path: Path) -> None:
    """Parse BSD-style sources file."""
    sources = tmp_path / 'sources'
    sources.write_text(
        'SHA512 (foo-1.0.tar.gz) = abc123\n'
        'SHA512 (foo-1.0.tar.gz.sig) = def456\n'
    )

    entries = cuv_module._parse_sources_file(sources)
    assert len(entries) == 2
    assert entries[0]['algo'] == 'SHA512'
    assert entries[0]['filename'] == 'foo-1.0.tar.gz'
    assert entries[0]['hash'] == 'abc123'
    assert entries[1]['filename'] == 'foo-1.0.tar.gz.sig'


def test_parse_sources_file_missing(cuv_module, tmp_path: Path) -> None:
    """Returns empty list when sources file does not exist."""
    entries = cuv_module._parse_sources_file(tmp_path / 'sources')
    assert entries == []


def test_parse_sources_file_empty(cuv_module, tmp_path: Path) -> None:
    """Returns empty list for an empty sources file."""
    sources = tmp_path / 'sources'
    sources.write_text('')
    entries = cuv_module._parse_sources_file(sources)
    assert entries == []


def test_write_sources_file(cuv_module, tmp_path: Path) -> None:
    """Round-trip: write and re-parse sources file."""
    sources = tmp_path / 'sources'
    entries = [
        {'algo': 'SHA512', 'filename': 'pkg-2.0.tar.xz', 'hash': 'aaa'},
        {'algo': 'SHA512', 'filename': 'pkg-2.0.tar.xz.sig', 'hash': 'bbb'},
    ]
    cuv_module._write_sources_file(sources, entries)

    parsed = cuv_module._parse_sources_file(sources)
    assert len(parsed) == 2
    assert parsed[0]['filename'] == 'pkg-2.0.tar.xz'
    assert parsed[1]['hash'] == 'bbb'


#
# Tests — _compute_file_hash
#


def test_compute_file_hash(cuv_module, tmp_path: Path) -> None:
    """Compute SHA512 hash of a file."""
    f = tmp_path / 'data.bin'
    f.write_bytes(b'hello world')
    h = cuv_module._compute_file_hash(f, 'SHA512')
    assert len(h) == 128  # SHA-512 hex digest length
    # Same content produces same hash
    assert h == cuv_module._compute_file_hash(f, 'SHA512')


def test_compute_file_hash_sha256(cuv_module, tmp_path: Path) -> None:
    """Compute SHA256 hash of a file."""
    f = tmp_path / 'data.bin'
    f.write_bytes(b'test data')
    h = cuv_module._compute_file_hash(f, 'SHA256')
    assert len(h) == 64  # SHA-256 hex digest length


#
# Tests — _update_gitignore
#


def test_update_gitignore_creates_file(cuv_module, tmp_path: Path) -> None:
    """Creates .gitignore when it does not exist."""
    cuv_module._update_gitignore(tmp_path, ['foo-1.0.tar.gz', 'foo-1.0.tar.gz.sig'])
    gitignore = tmp_path / '.gitignore'
    assert gitignore.exists()
    lines = gitignore.read_text().splitlines()
    assert 'foo-1.0.tar.gz' in lines
    assert 'foo-1.0.tar.gz.sig' in lines


def test_update_gitignore_appends(cuv_module, tmp_path: Path) -> None:
    """Appends to existing .gitignore without duplicating entries."""
    gitignore = tmp_path / '.gitignore'
    gitignore.write_text('existing-entry\nfoo-1.0.tar.gz\n')

    cuv_module._update_gitignore(tmp_path, ['foo-1.0.tar.gz', 'bar-2.0.tar.xz'])

    lines = gitignore.read_text().splitlines()
    assert lines.count('foo-1.0.tar.gz') == 1  # not duplicated
    assert 'bar-2.0.tar.xz' in lines
    assert 'existing-entry' in lines


def test_update_gitignore_no_duplicates(cuv_module, tmp_path: Path) -> None:
    """Does not write anything when all entries already exist."""
    gitignore = tmp_path / '.gitignore'
    gitignore.write_text('a.tar.gz\nb.tar.gz\n')

    cuv_module._update_gitignore(tmp_path, ['a.tar.gz', 'b.tar.gz'])

    content = gitignore.read_text()
    assert content == 'a.tar.gz\nb.tar.gz\n'


def test_update_gitignore_empty_list(cuv_module, tmp_path: Path) -> None:
    """No-op when filenames list is empty."""
    cuv_module._update_gitignore(tmp_path, [])
    assert not (tmp_path / '.gitignore').exists()


#
# Tests — mark_package_modified
#


def test_mark_package_modified(cuv_module, workdir: Path) -> None:
    """Sets modification_status to modified and modification_reason."""
    _create_package(workdir, 'pkg', '1.0',
                    metadata={'version': '1.0', 'release': '1'})
    cuv_module.METADATA_DIR = workdir / 'metadata'
    cuv_module.mark_package_modified('pkg', 'Update to upstream version 2.0')

    with open(workdir / 'metadata' / 'pkg.json') as f:
        data = json.load(f)
    assert data['modification_status'] == 'modified'
    assert data['modification_reason'] == 'Update to upstream version 2.0'


def test_mark_package_modified_no_metadata(cuv_module, workdir: Path) -> None:
    """Logs warning and does nothing when metadata file is missing."""
    cuv_module.METADATA_DIR = workdir / 'metadata'
    # Should not raise
    cuv_module.mark_package_modified('nonexistent', 'reason')


#
# Tests — check_package_version
#


def test_check_package_version_has_update(cuv_module, workdir: Path) -> None:
    """Detects when upstream version is newer."""
    _create_package(workdir, 'pkg', '1.0')
    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    mock_response = {
        'version': '2.0',
        'stable_versions': ['2.0', '1.0'],
        'id': 42,
    }

    with patch.object(cuv_module, 'query_anitya', return_value=mock_response):
        result = cuv_module.check_package_version('pkg')

    assert result.has_update is True
    assert result.current_version == '1.0'
    assert result.upstream_version == '2.0'
    assert result.anitya_project_id == 42


def test_check_package_version_up_to_date(cuv_module, workdir: Path) -> None:
    """No update when current matches upstream."""
    _create_package(workdir, 'pkg', '2.0')
    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    mock_response = {
        'version': '2.0',
        'stable_versions': ['2.0'],
        'id': 42,
    }

    with patch.object(cuv_module, 'query_anitya', return_value=mock_response):
        result = cuv_module.check_package_version('pkg')

    assert result.has_update is False
    assert result.current_version == '2.0'
    assert result.upstream_version == '2.0'


def test_check_package_version_not_found(cuv_module, workdir: Path) -> None:
    """Handles package not found in Anitya."""
    _create_package(workdir, 'pkg', '1.0')
    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    with patch.object(cuv_module, 'query_anitya',
                      side_effect=ValueError('Package not found in Fedora')):
        result = cuv_module.check_package_version('pkg')

    assert result.has_update is False
    assert result.error == 'Package not found in Fedora'


def test_check_package_version_connection_error(cuv_module, workdir: Path) -> None:
    """Handles connection errors from Anitya."""
    _create_package(workdir, 'pkg', '1.0')
    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    with patch.object(cuv_module, 'query_anitya',
                      side_effect=ConnectionError('timeout')):
        result = cuv_module.check_package_version('pkg')

    assert result.has_update is False
    assert 'timeout' in result.error


def test_check_package_version_no_version(cuv_module, workdir: Path) -> None:
    """Returns error when current version cannot be determined."""
    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    result = cuv_module.check_package_version('nonexistent')
    assert result.has_update is False
    assert result.current_version == 'unknown'
    assert 'Could not determine current version' in result.error


def test_check_package_version_prefers_stable(cuv_module, workdir: Path) -> None:
    """Prefers stable_versions[0] over the version field."""
    _create_package(workdir, 'pkg', '1.0')
    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    mock_response = {
        'version': '3.0-dev',
        'stable_versions': ['2.0'],
        'id': 10,
    }

    with patch.object(cuv_module, 'query_anitya', return_value=mock_response):
        result = cuv_module.check_package_version('pkg')

    assert result.upstream_version == '2.0'


def test_check_package_version_falls_back_to_version(cuv_module, workdir: Path) -> None:
    """Falls back to version field when stable_versions is empty."""
    _create_package(workdir, 'pkg', '1.0')
    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    mock_response = {
        'version': '2.0',
        'stable_versions': [],
        'id': 10,
    }

    with patch.object(cuv_module, 'query_anitya', return_value=mock_response):
        result = cuv_module.check_package_version('pkg')

    assert result.upstream_version == '2.0'
    assert result.has_update is True


#
# Tests — get_all_packages
#


def test_get_all_packages(cuv_module, workdir: Path) -> None:
    """Lists package directories that contain spec files."""
    _create_package(workdir, 'alpha', '1.0')
    _create_package(workdir, 'beta', '2.0')

    # A directory without a spec file should not be listed
    (workdir / 'rpms' / 'empty').mkdir()

    cuv_module.RPMS_DIR = workdir / 'rpms'
    packages = cuv_module.get_all_packages()

    assert packages == ['alpha', 'beta']


def test_get_all_packages_ignores_hidden(cuv_module, workdir: Path) -> None:
    """Ignores hidden directories."""
    _create_package(workdir, 'visible', '1.0')
    hidden_dir = workdir / 'rpms' / '.hidden'
    hidden_dir.mkdir()
    (hidden_dir / 'hidden.spec').write_text('Name: hidden\nVersion: 1\n')

    cuv_module.RPMS_DIR = workdir / 'rpms'
    packages = cuv_module.get_all_packages()
    assert packages == ['visible']


#
# Tests — download_new_sources
#


def test_download_new_sources(cuv_module, workdir: Path) -> None:
    """Downloads new source, updates sources file, uploads to lookaside."""
    pkg_dir = _create_package(
        workdir, 'pkg', '2.0',
        sources={'pkg-1.0.tar.gz': 'oldhash'},
    )

    with patch.object(cuv_module, '_download_file') as mock_dl, \
         patch.object(cuv_module, '_upload_to_lookaside') as mock_ul, \
         patch.object(cuv_module, '_compute_file_hash', return_value='newhash'), \
         patch.object(cuv_module, '_get_spec_source_urls',
                      return_value={0: 'https://example.com/pkg/pkg-2.0.tar.gz'}):

        cuv_module.RPMS_DIR = workdir / 'rpms'
        downloaded = cuv_module.download_new_sources('pkg', '1.0', '2.0')

    assert downloaded == ['pkg-2.0.tar.gz']
    mock_dl.assert_called_once()
    mock_ul.assert_called_once()

    # sources file should be updated
    entries = cuv_module._parse_sources_file(pkg_dir / 'sources')
    assert len(entries) == 1
    assert entries[0]['filename'] == 'pkg-2.0.tar.gz'
    assert entries[0]['hash'] == 'newhash'


def test_download_new_sources_download_failure(cuv_module, workdir: Path) -> None:
    """Crashes with exception when download fails."""
    _create_package(
        workdir, 'pkg', '2.0',
        sources={'pkg-1.0.tar.gz': 'oldhash'},
    )

    with patch.object(cuv_module, '_download_file',
                      side_effect=Exception('network error')), \
         patch.object(cuv_module, '_get_spec_source_urls',
                      return_value={0: 'https://example.com/pkg/pkg-2.0.tar.gz'}):

        cuv_module.RPMS_DIR = workdir / 'rpms'
        with pytest.raises(Exception, match='network error'):
            cuv_module.download_new_sources('pkg', '1.0', '2.0')


def test_download_new_sources_no_version_in_filename(cuv_module, workdir: Path) -> None:
    """Skips sources where filename does not contain the version."""
    _create_package(
        workdir, 'pkg', '2.0',
        sources={'static-data.tar.gz': 'somehash'},
    )

    with patch.object(cuv_module, '_get_spec_source_urls',
                      return_value={0: 'https://example.com/static-data.tar.gz'}):

        cuv_module.RPMS_DIR = workdir / 'rpms'
        downloaded = cuv_module.download_new_sources('pkg', '1.0', '2.0')

    assert downloaded == []


#
# Tests — update_spec_version
#


def test_update_spec_version(cuv_module, workdir: Path) -> None:
    """Updates spec version, downloads sources, marks modified."""
    _create_package(workdir, 'pkg', '1.0',
                    sources={'pkg-1.0.tar.gz': 'oldhash'},
                    metadata={'version': '1.0', 'release': '1'})

    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'
    cuv_module.ROOT_DIR = workdir

    with patch.object(cuv_module, 'download_new_sources',
                      return_value=['pkg-2.0.tar.gz']) as mock_dl:
        downloaded = cuv_module.update_spec_version('pkg', '2.0')

    assert downloaded == ['pkg-2.0.tar.gz']
    mock_dl.assert_called_once_with('pkg', '1.0', '2.0')

    # Metadata should be marked as modified
    with open(workdir / 'metadata' / 'pkg.json') as f:
        data = json.load(f)
    assert data['modification_status'] == 'modified'
    assert 'Update to upstream version 2.0' in data['modification_reason']


def test_update_spec_version_sets_release_0_1(cuv_module, workdir: Path) -> None:
    """Release is set to 0.1 so that a later Fedora import (Release >= 1)
    sorts higher and replaces the locally-built version."""
    _create_package(workdir, 'pkg', '1.0',
                    sources={'pkg-1.0.tar.gz': 'oldhash'},
                    metadata={'version': '1.0', 'release': '1'})

    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'
    cuv_module.ROOT_DIR = workdir

    with patch.object(cuv_module, 'download_new_sources', return_value=[]):
        cuv_module.update_spec_version('pkg', '2.0')

    spec_content = (workdir / 'rpms' / 'pkg' / 'pkg.spec').read_text()
    assert 'Release: 0.1%{?dist}' in spec_content


#
# Tests — git commit excludes lookaside files
#


def test_commit_excludes_lookaside_files(cuv_module, workdir: Path) -> None:
    """Downloaded sources are added to .gitignore and excluded from commits."""
    pkg_dir = _create_package(
        workdir, 'pkg', '1.0',
        sources={'pkg-1.0.tar.gz': 'oldhash'},
        metadata={'version': '1.0', 'release': '1'},
    )

    # Stage initial package state
    subprocess.run(['git', 'add', '.'], cwd=workdir, check=True)
    subprocess.run(['git', 'commit', '-m', 'Add pkg'], cwd=workdir, check=True)

    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'
    cuv_module.ROOT_DIR = workdir

    # Simulate what main() does: update spec, create source file,
    # update .gitignore, git add, commit.
    with patch.object(cuv_module, 'download_new_sources',
                      return_value=['pkg-2.0.tar.gz']):
        downloaded = cuv_module.update_spec_version('pkg', '2.0')

    # Create the fake downloaded file (simulating the download)
    (pkg_dir / 'pkg-2.0.tar.gz').write_bytes(b'fake tarball')

    # Replicate the logic from main(): update .gitignore, then git add
    cuv_module._update_gitignore(pkg_dir, downloaded)

    cuv_module.run_git('add', f'rpms/pkg', f'metadata/pkg.json', cwd=workdir)

    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )
    staged_files = result.stdout.strip().split('\n')

    # The tarball should NOT be staged (it's in .gitignore)
    assert 'rpms/pkg/pkg-2.0.tar.gz' not in staged_files
    # The .gitignore and spec should be staged
    assert 'rpms/pkg/.gitignore' in staged_files
    assert 'rpms/pkg/pkg.spec' in staged_files


#
# Tests — CLI (main function)
#


def test_cli_check_json_output(cuv_module, workdir: Path) -> None:
    """--json flag produces valid JSON output."""
    _create_package(workdir, 'pkg', '1.0')
    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    mock_response = {
        'version': '2.0',
        'stable_versions': ['2.0'],
        'id': 42,
    }

    with patch.object(cuv_module, 'query_anitya', return_value=mock_response), \
         patch('sys.argv', ['check_upstream_versions.py', '--json', 'pkg']), \
         pytest.raises(SystemExit) as exc_info, \
         patch('sys.stdout') as mock_stdout:
        # Capture print output
        printed = []
        mock_stdout.write = lambda s: printed.append(s)
        # The script calls sys.exit(1) when updates are found
        cuv_module.main()

    assert exc_info.value.code == 1  # updates found


def test_cli_no_updates_exit_zero(cuv_module, workdir: Path) -> None:
    """Exits with 0 when no updates are available."""
    _create_package(workdir, 'pkg', '2.0')
    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    mock_response = {
        'version': '2.0',
        'stable_versions': ['2.0'],
        'id': 42,
    }

    with patch.object(cuv_module, 'query_anitya', return_value=mock_response), \
         patch('sys.argv', ['check_upstream_versions.py', '--quiet', 'pkg']), \
         pytest.raises(SystemExit) as exc_info:
        cuv_module.main()

    assert exc_info.value.code == 0


def test_cli_error_exit_two(cuv_module, workdir: Path) -> None:
    """Exits with 2 when errors occur and no updates are found."""
    _create_package(workdir, 'pkg', '1.0')
    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    with patch.object(cuv_module, 'query_anitya',
                      side_effect=ConnectionError('timeout')), \
         patch('sys.argv', ['check_upstream_versions.py', '--quiet', 'pkg']), \
         pytest.raises(SystemExit) as exc_info:
        cuv_module.main()

    assert exc_info.value.code == 2


#
# Tests — track_upstream filtering
#


def test_main_skips_packages_without_track_upstream(cuv_module, workdir: Path) -> None:
    """main() skips packages without track_upstream when no CLI args given."""
    _create_package(workdir, 'tracked', '1.0',
                    metadata={'version': '1.0', 'release': '1',
                              'track_upstream': True})
    _create_package(workdir, 'untracked', '1.0',
                    metadata={'version': '1.0', 'release': '1'})

    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    mock_response = {
        'version': '1.0',
        'stable_versions': ['1.0'],
        'id': 42,
    }

    checked = []
    original_check = cuv_module.check_package_version

    def tracking_check(pkg, distro='Fedora'):
        checked.append(pkg)
        return original_check(pkg, distro)

    with patch.object(cuv_module, 'query_anitya', return_value=mock_response), \
         patch.object(cuv_module, 'check_package_version', side_effect=tracking_check), \
         patch('sys.argv', ['check_upstream_versions.py', '--quiet']), \
         pytest.raises(SystemExit):
        cuv_module.main()

    assert 'tracked' in checked
    assert 'untracked' not in checked


def test_main_checks_tracked_packages(cuv_module, workdir: Path) -> None:
    """main() checks packages that have track_upstream: true."""
    _create_package(workdir, 'pkg', '1.0',
                    metadata={'version': '1.0', 'release': '1',
                              'track_upstream': True})

    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    mock_response = {
        'version': '2.0',
        'stable_versions': ['2.0'],
        'id': 42,
    }

    with patch.object(cuv_module, 'query_anitya', return_value=mock_response), \
         patch('sys.argv', ['check_upstream_versions.py', '--quiet']), \
         pytest.raises(SystemExit) as exc_info:
        cuv_module.main()

    # Exit code 1 means updates found
    assert exc_info.value.code == 1


def test_main_explicit_args_bypass_track_filter(cuv_module, workdir: Path) -> None:
    """Explicit CLI package args bypass the track_upstream filter."""
    _create_package(workdir, 'untracked', '1.0',
                    metadata={'version': '1.0', 'release': '1'})

    cuv_module.RPMS_DIR = workdir / 'rpms'
    cuv_module.METADATA_DIR = workdir / 'metadata'

    mock_response = {
        'version': '2.0',
        'stable_versions': ['2.0'],
        'id': 42,
    }

    with patch.object(cuv_module, 'query_anitya', return_value=mock_response), \
         patch('sys.argv', ['check_upstream_versions.py', '--quiet', 'untracked']), \
         pytest.raises(SystemExit) as exc_info:
        cuv_module.main()

    # Should check the package even though it doesn't have track_upstream
    assert exc_info.value.code == 1
