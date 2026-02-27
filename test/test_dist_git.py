"""Integration tests for dist_git importer."""

import json
import os
import subprocess
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

#
# Fixtures
#

@pytest.fixture
def dist_git_module():
    """Load the dist_git script as a Python module.

    For tests which need to mock internal functions.
    """
    script_path = Path(__file__).parent.parent / 'ci' / 'dist_git.py'
    module = types.ModuleType("dist_git")
    module.__file__ = str(script_path)
    code = compile(script_path.read_text(), str(script_path), 'exec')
    exec(code, module.__dict__)
    return module


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    """Shallow copy of the project with no imports"""

    subprocess.run(['git', 'init'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=tmp_path, check=True)

    # Copy dist_git script
    script_src = Path(__file__).parent.parent / 'ci' / 'dist_git.py'
    script_dst = tmp_path / 'ci' / 'dist_git.py'
    script_dst.parent.mkdir()
    script_dst.write_text(script_src.read_text())
    script_dst.chmod(0o755)

    (tmp_path / 'rpms').mkdir()
    (tmp_path / 'metadata').mkdir()

    # Create default upstream-releases.json for tests
    # Note: rawhide is not included as it's auto-resolved to the highest version
    (tmp_path / 'upstream-releases.json').write_text(
        json.dumps({'fedora': {'f40': 'f40', 'f99': 'f99'}}) + '\n'
    )

    # no-op generate_resources.py
    (tmp_path / 'ci' / 'generate_resources.py').write_text('# no-op for tests\n')
    (tmp_path / '.tekton').mkdir()
    (tmp_path / 'konflux-templates').mkdir()

    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=tmp_path, check=True)

    return tmp_path


@pytest.fixture
def upstream_repos(tmp_path: Path) -> dict[str, Path]:
    """Create two mock upstream dist_git repositories."""
    repos: dict[str, Path] = {}

    # Create first upstream repo: vanilla
    vanilla_dir = tmp_path / 'upstream' / 'vanilla.git'
    vanilla_dir.mkdir(parents=True)
    subprocess.run(['git', 'init', '--initial-branch=rawhide'], cwd=vanilla_dir, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=vanilla_dir, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=vanilla_dir, check=True)

    # Create a simple spec file
    (vanilla_dir / 'vanilla.spec').write_text("""Name: vanilla
Version: 1.0
Release: 1
Summary: Test package vanilla
License: MIT

%description
Test package

%files
""")
    subprocess.run(['git', 'add', 'vanilla.spec'], cwd=vanilla_dir, check=True)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=vanilla_dir, check=True)
    repos['vanilla'] = vanilla_dir

    # Create second upstream repo: chocolate with a stable branch
    chocolate_dir = tmp_path / 'upstream' / 'chocolate.git'
    chocolate_dir.mkdir(parents=True)
    subprocess.run(['git', 'init', '--initial-branch=rawhide'], cwd=chocolate_dir, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=chocolate_dir, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=chocolate_dir, check=True)

    choc_spec = chocolate_dir / 'chocolate.spec'
    choc_spec.write_text("""Name: chocolate
Version: 10
Release: 1
Summary: Test package chocolate
License: GPL

%description
Test package chocolate

%files
""")
    subprocess.run(['git', 'add', 'chocolate.spec'], cwd=chocolate_dir, check=True)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=chocolate_dir, check=True)

    # Create f40 branch
    subprocess.run(['git', 'checkout', '-b', 'f40'], cwd=chocolate_dir, check=True)
    choc_spec.write_text("""Name: chocolate
Version: 4
Release: 1
Summary: Test package chocolate
License: GPL

%description
Test package chocolate (f40)

%files
""")
    subprocess.run(['git', 'add', 'chocolate.spec'], cwd=chocolate_dir, check=True)
    subprocess.run(['git', 'commit', '-m', 'Update for f40'], cwd=chocolate_dir, check=True)
    subprocess.run(['git', 'checkout', 'rawhide'], cwd=chocolate_dir, check=True)

    repos['chocolate'] = chocolate_dir

    return repos


#
# Helpers
#

def add_upstream_commit(repo_path: Path, package_name: str, old_version: str, new_version: str) -> str:
    """Add a commit to an upstream repository updating the version.

    Returns the new commit SHA.
    """
    spec_file = repo_path / f'{package_name}.spec'
    spec_file.write_text(spec_file.read_text().replace(f'Version: {old_version}', f'Version: {new_version}'))
    subprocess.run(['git', 'add', f'{package_name}.spec'], cwd=repo_path, check=True)
    subprocess.run(['git', 'commit', '-m', f'Update to {new_version}-1'], cwd=repo_path, check=True)
    return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo_path,
                          text=True, stdout=subprocess.PIPE, check=True).stdout.strip()


def get_last_commit_info(workdir: Path) -> tuple[str, str]:
    """Get subject and body of the last commit.

    Returns (subject, body) tuple.
    """
    result = subprocess.run(['git', 'log', '-1', '--format=%s%n%n%b'], cwd=workdir,
                            text=True, stdout=subprocess.PIPE, check=True)
    lines = result.stdout.strip().split('\n')
    assert lines
    subject = lines[0]
    body = '\n'.join(lines[2:]) if len(lines) > 2 else ''
    return subject, body


#
# Tests
#

def test_import(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Import a new package."""
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, capture_output=True, check=True, text=True
    )

    assert "Successfully imported chocolate" in result.stderr

    chocolate_dir = workdir / 'rpms' / 'chocolate'
    assert (chocolate_dir / 'chocolate.spec').exists()
    assert not (chocolate_dir / '.git').exists()

    import_json_file = workdir / 'metadata' / 'chocolate.json'
    assert import_json_file.exists()
    with open(import_json_file) as f:
        import_data = json.load(f)
    assert import_data['branch'] == 'rawhide'
    assert import_data['version'] == '10'
    assert import_data['release'] == '1'

    subject, body = get_last_commit_info(workdir)
    assert subject == 'Import chocolate-10-1'
    assert 'Branch: rawhide' in body
    assert f"Upstream: {import_data['sha']}" in body


def test_import_dry_run(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """--dry-run prevents commits."""
    # Get initial commit (from fixture setup)
    initial_subject, _ = get_last_commit_info(workdir)

    # Import with --dry-run
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), '--dry-run', 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True, capture_output=True, text=True
    )

    assert "Successfully imported chocolate" in result.stderr

    # Verify files were imported
    chocolate_dir = workdir / 'rpms' / 'chocolate'
    assert (chocolate_dir / 'chocolate.spec').exists()

    # Verify metadata was created
    import_json_file = workdir / 'metadata' / 'chocolate.json'
    assert import_json_file.exists()
    with open(import_json_file) as f:
        import_data = json.load(f)
    assert import_data['version'] == '10'

    # Verify no commit was created (still at initial commit)
    subject, _ = get_last_commit_info(workdir)
    assert subject == initial_subject


def test_import_sign_off(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """--sign-off adds Signed-off-by trailer to commits."""
    # Import with --sign-off
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), '--sign-off', 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, capture_output=True, text=True, check=True
    )

    assert "Successfully imported vanilla" in result.stderr

    # Verify the import worked
    import_json_file = workdir / 'metadata' / 'vanilla.json'
    assert import_json_file.exists()
    with open(import_json_file) as f:
        import_data = json.load(f)
    assert import_data['version'] == '1.0'

    # Verify commit has sign-off trailer
    subject, body = get_last_commit_info(workdir)
    assert subject == 'Import vanilla-1.0-1'
    assert f"Upstream: {import_data['sha']}" in body
    assert 'Signed-off-by: Test <test@example.com>' in body


def test_import_with_branch(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Importing from a specific branch."""
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', '--branch', 'f40', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True,
    )

    # Check metadata has correct branch and version
    import_json_file = workdir / 'metadata' / 'chocolate.json'
    with open(import_json_file) as f:
        import_data = json.load(f)
    assert import_data['branch'] == 'f40'
    assert import_data['version'] == '4'
    assert import_data['release'] == '1'

    subject, body = get_last_commit_info(workdir)
    assert subject == 'Import chocolate-4-1'
    assert 'Branch: f40' in body
    assert f"Upstream: {import_data['sha']}" in body


def test_import_existing_package_fails(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Importing an existing package fails."""
    # Create vanilla directory to simulate existing package
    (workdir / 'rpms' / 'vanilla').mkdir()

    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, capture_output=True, text=True
    )

    assert result.returncode == 1
    assert "ERROR: Package directory rpms/vanilla/ already exists" in result.stderr


def test_import_with_ref(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Import with --ref to get an older commit, then update moves to latest."""
    # Get initial SHA of chocolate
    old_sha = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=upstream_repos["chocolate"], text=True, stdout=subprocess.PIPE, check=True
    ).stdout.strip()

    # Add new commits to upstream
    add_upstream_commit(upstream_repos["chocolate"], 'chocolate', '10', '11')
    new_sha = add_upstream_commit(upstream_repos["chocolate"], 'chocolate', '11', '12')

    # Import using --ref to get the old version
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', '--ref', old_sha, f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True,
    )

    # Check that we imported the old version
    import_json_file = workdir / 'metadata' / 'chocolate.json'
    with open(import_json_file) as f:
        import_data = json.load(f)
    assert import_data['sha'] == old_sha
    assert import_data['version'] == '10'
    assert import_data['branch'] == 'rawhide'

    # Verify commit message includes the old SHA
    subject, body = get_last_commit_info(workdir)
    assert subject == 'Import chocolate-10-1'
    assert f"Upstream: {old_sha}" in body

    # Now run update to move to latest version
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'update', '--skip-build-check', 'chocolate'],
        cwd=workdir, check=True,
    )

    # Check that we're now at the latest version
    with open(import_json_file) as f:
        import_data = json.load(f)
    assert import_data['sha'] == new_sha
    assert import_data['version'] == '12'

    # Verify update commit was created
    subject, body = get_last_commit_info(workdir)
    assert subject == 'Update chocolate from 10-1 to 12-1'
    assert f"Upstream: {new_sha}" in body


def test_update(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """update command"""
    # Case 1: Import vanilla (unmodified, current)
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Case 2: Import chocolate (unmodified, will become outdated)
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True,
    )
    # Get the sha that was imported
    chocolate_import_json = workdir / 'metadata' / 'chocolate.json'
    with open(chocolate_import_json) as f:
        chocolate_import_data = json.load(f)
    initial_sha = chocolate_import_data['sha']

    # Update upstream chocolate
    add_upstream_commit(upstream_repos["chocolate"], 'chocolate', '10', '11')

    # Case 3: Create a modified package (strawberry) - import old chocolate, modify it, then chocolate gets updated
    strawberry_dir = workdir / 'rpms' / 'strawberry'
    strawberry_dir.mkdir()
    chocolate_spec = (workdir / 'rpms' / 'chocolate' / 'chocolate.spec')
    # Copy chocolate spec to strawberry and modify it
    (strawberry_dir / 'chocolate.spec').write_text(chocolate_spec.read_text() + '\n# Local modification\n')
    # Add strawberry metadata (copy chocolate's old metadata, so it has an update available)
    strawberry_import_json = workdir / 'metadata' / 'strawberry.json'
    strawberry_import_data = chocolate_import_data.copy()
    with open(strawberry_import_json, 'w') as f:
        json.dump(strawberry_import_data, f, indent=2, sort_keys=True)
        f.write('\n')

    # Case 4: Downstream-only package (no metadata)
    mango_dir = workdir / 'rpms' / 'mango'
    mango_dir.mkdir()
    (mango_dir / 'mango.spec').write_text('Name: mango\nVersion: 1.0\nRelease: 1\n')

    # Let's not cover Koji check here
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'update', '--skip-build-check'],
        cwd=workdir, capture_output=True, text=True, check=True
    )

    # Check results
    with open(chocolate_import_json) as f:
        chocolate_import_data = json.load(f)

    # Case 1: vanilla should be unchanged (already up-to-date)
    assert "already up-to-date" in result.stderr or "vanilla" in result.stderr

    # Case 2: chocolate should be updated to new version
    assert chocolate_import_data['sha'] != initial_sha, "chocolate should have been updated"
    assert chocolate_import_data['version'] == '11', "chocolate should be at version 11"
    assert "Updating chocolate" in result.stderr

    # Verify commit was created for chocolate update
    subject, body = get_last_commit_info(workdir)
    assert subject == 'Update chocolate from 10-1 to 11-1'
    assert f"Upstream: {chocolate_import_data['sha']}" in body

    # Case 3: strawberry should be skipped (has upstream update but also has local modifications)
    assert "Skipping strawberry: package has local modifications" in result.stderr

    # Case 4: mango should not be mentioned (no metadata)
    assert "mango" not in result.stderr


def test_update_uses_ls_remote(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """update uses ls-remote optimization for up-to-date packages."""
    # Import vanilla
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Create a mock git wrapper that logs commands
    log_file = workdir / 'git_commands.log'
    bin_dir = workdir / 'bin'
    bin_dir.mkdir()
    mock_git = bin_dir / 'git'
    mock_git.write_text(f"""#!/bin/bash
echo "$@" >> {log_file}
exec /usr/bin/git "$@"
""")
    mock_git.chmod(0o755)

    # Update PATH to use mock git
    env = os.environ.copy()
    env['PATH'] = f"{bin_dir}:{env['PATH']}"

    # Run update with mock git
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'update', 'vanilla'],
        cwd=workdir, capture_output=True, text=True, check=True, env=env
    )

    assert "already up-to-date" in result.stderr

    # Should use ls-remote (not clone) to check if package is up-to-date
    git_commands = log_file.read_text().strip().split('\n')
    # Filter out config checks
    non_config_commands = [cmd for cmd in git_commands if not cmd.startswith('config ')]
    assert non_config_commands == ["ls-remote file://" + str(upstream_repos["vanilla"]) + " rawhide"]


def test_update_unbuilt(workdir: Path, upstream_repos: dict[str, Path], dist_git_module) -> None:
    """Update skips packages not built in Koji."""
    # Import chocolate
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True,
    )

    # Update upstream chocolate
    add_upstream_commit(upstream_repos["chocolate"], 'chocolate', '10', '11')

    # Mock Koji to return no build found (for both current and fallback)
    with patch('xmlrpc.client.ServerProxy') as mock_server_class:
        mock_server = MagicMock()
        mock_server.getBuild.return_value = None  # Build not found
        mock_server_class.return_value = mock_server

        # Run update in-process
        dist_git_module.ROOT_DIR = workdir
        dist_git_module.RPMS_DIR = workdir / 'rpms'
        dist_git_module.METADATA_DIR = workdir / 'metadata'
        dist_git_module.RELEASES_JSON = workdir / 'upstream-releases.json'
        dist_git_module.imports = dist_git_module.get_all_imported_packages()
        dist_git_module.releases = json.loads((workdir / 'upstream-releases.json').read_text())
        dist_git_module.update('chocolate')
        # Should try fc99 first, then fallback to fc40 (both not found)
        assert mock_server.getBuild.call_count == 2
        mock_server.getBuild.assert_any_call('chocolate-11-1.fc99')
        mock_server.getBuild.assert_any_call('chocolate-11-1.fc40')
        chocolate_import_json = workdir / 'metadata' / 'chocolate.json'
        with open(chocolate_import_json) as f:
            import_data = json.load(f)
        assert import_data['version'] == '10', "Should not update when build missing in Koji"


def test_update_built(workdir: Path, upstream_repos: dict[str, Path], dist_git_module) -> None:
    """Update proceeds when built in Koji."""
    # Import chocolate
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True,
    )
    chocolate_import_json = workdir / 'metadata' / 'chocolate.json'
    with open(chocolate_import_json) as f:
        initial_data = json.load(f)
    initial_sha = initial_data['sha']

    # Update upstream chocolate
    new_sha = add_upstream_commit(upstream_repos["chocolate"], 'chocolate', '10', '11')

    # Mock Koji to return a successful build with matching commit
    with patch('xmlrpc.client.ServerProxy') as mock_server_class:
        mock_server = MagicMock()
        mock_server.getBuild.return_value = {
            'build_id': 12345,
            'nvr': 'chocolate-11-1.fc99',
            'state': 1,  # COMPLETE
            'source': f'git+https://example.com/chocolate.git#{new_sha}'
        }
        mock_server_class.return_value = mock_server

        # Run update in-process
        dist_git_module.ROOT_DIR = workdir
        dist_git_module.RPMS_DIR = workdir / 'rpms'
        dist_git_module.METADATA_DIR = workdir / 'metadata'
        dist_git_module.RELEASES_JSON = workdir / 'upstream-releases.json'
        dist_git_module.imports = dist_git_module.get_all_imported_packages()
        dist_git_module.releases = json.loads((workdir / 'upstream-releases.json').read_text())
        dist_git_module.update('chocolate')
        mock_server.getBuild.assert_called_once_with('chocolate-11-1.fc99')
        with open(chocolate_import_json) as f:
            import_data = json.load(f)
        assert import_data['version'] == '11'
        assert import_data['sha'] == new_sha


def test_update_branch_dist_tag(workdir: Path, upstream_repos: dict[str, Path], dist_git_module) -> None:
    """Update uses correct dist tag for non-rawhide branches."""
    # Import chocolate from f40 branch
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', '--branch', 'f40', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True,
    )

    # Switch to f40 branch and update upstream chocolate
    subprocess.run(['git', 'checkout', 'f40'], cwd=upstream_repos["chocolate"], check=True)
    new_sha = add_upstream_commit(upstream_repos["chocolate"], 'chocolate', '4', '5')

    # Mock Koji to return a successful build
    with patch('xmlrpc.client.ServerProxy') as mock_server_class:
        mock_server = MagicMock()
        mock_server.getBuild.return_value = {
            'build_id': 12345,
            'nvr': 'chocolate-5-1.fc40',
            'state': 1,  # COMPLETE
            'source': f'git+https://example.com/chocolate.git#{new_sha}'
        }
        mock_server_class.return_value = mock_server

        # Run update in-process
        dist_git_module.ROOT_DIR = workdir
        dist_git_module.RPMS_DIR = workdir / 'rpms'
        dist_git_module.METADATA_DIR = workdir / 'metadata'
        dist_git_module.RELEASES_JSON = workdir / 'upstream-releases.json'
        dist_git_module.imports = dist_git_module.get_all_imported_packages()
        dist_git_module.releases = json.loads((workdir / 'upstream-releases.json').read_text())
        dist_git_module.update('chocolate')
        # Should query for .fc40 (from branch f40), not rawhide version
        mock_server.getBuild.assert_called_once_with('chocolate-5-1.fc40')
        chocolate_import_json = workdir / 'metadata' / 'chocolate.json'
        with open(chocolate_import_json) as f:
            import_data = json.load(f)
        assert import_data['version'] == '5'
        assert import_data['sha'] == new_sha


def test_update_rawhide_fallback(workdir: Path, upstream_repos: dict[str, Path], dist_git_module) -> None:
    """Update finds rawhide build with previous release dist tag when current not found."""
    # Import vanilla from rawhide
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Update upstream vanilla
    new_sha = add_upstream_commit(upstream_repos["vanilla"], 'vanilla', '1.0', '2.0')

    # Mock Koji to:
    # 1. Return None for fc99 (current rawhide)
    # 2. Return successful build for fc40 (previous release fallback)
    with patch('xmlrpc.client.ServerProxy') as mock_server_class:
        mock_server = MagicMock()

        def getBuild_side_effect(nvr):
            if nvr == 'vanilla-2.0-1.fc99':
                return None  # Current rawhide not found
            elif nvr == 'vanilla-2.0-1.fc40':
                return {
                    'build_id': 12345,
                    'nvr': 'vanilla-2.0-1.fc40',
                    'state': 1,  # COMPLETE
                    'source': f'git+https://example.com/vanilla.git#{new_sha}'
                }
            return None

        mock_server.getBuild.side_effect = getBuild_side_effect
        mock_server_class.return_value = mock_server

        # Run update in-process
        dist_git_module.ROOT_DIR = workdir
        dist_git_module.RPMS_DIR = workdir / 'rpms'
        dist_git_module.METADATA_DIR = workdir / 'metadata'
        dist_git_module.RELEASES_JSON = workdir / 'upstream-releases.json'
        dist_git_module.imports = dist_git_module.get_all_imported_packages()
        dist_git_module.releases = json.loads((workdir / 'upstream-releases.json').read_text())
        dist_git_module.update('vanilla')

        # Should have called getBuild twice: once for fc99, then fallback to fc40
        assert mock_server.getBuild.call_count == 2
        mock_server.getBuild.assert_any_call('vanilla-2.0-1.fc99')
        mock_server.getBuild.assert_any_call('vanilla-2.0-1.fc40')

        # Package should be updated using the fallback
        vanilla_import_json = workdir / 'metadata' / 'vanilla.json'
        with open(vanilla_import_json) as f:
            import_data = json.load(f)
        assert import_data['version'] == '2.0'
        assert import_data['sha'] == new_sha


def test_sync(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Sync discards local modifications."""
    # Import chocolate (automatically commits)
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True
    )

    # Make local modification and commit it
    choc_spec = workdir / 'rpms' / 'chocolate' / 'chocolate.spec'
    choc_spec.write_text(choc_spec.read_text() + '\n# Local modification\n')
    subprocess.run(['git', 'commit', '-a', '-m', 'Local modification'], cwd=workdir, check=True)

    new_sha = add_upstream_commit(upstream_repos["chocolate"], 'chocolate', '10', '11')

    # sync succeeds and discards local modifications (automatically commits)
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'sync', 'chocolate'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    choc_spec_content = choc_spec.read_text()
    assert '# Local modification' not in choc_spec_content

    chocolate_import_json = workdir / 'metadata' / 'chocolate.json'
    with open(chocolate_import_json) as f:
        import_data = json.load(f)
    assert import_data['sha'] == new_sha
    assert import_data['version'] == '11'

    # Verify sync commit was created
    subject, body = get_last_commit_info(workdir)
    assert subject == 'Sync chocolate from 10-1 to 11-1'
    assert f"Upstream: {new_sha}" in body

    # Add another upstream commit
    new_sha2 = add_upstream_commit(upstream_repos["chocolate"], 'chocolate', '11', '12')

    # Update should now pull in the new version
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'update', '--skip-build-check', 'chocolate'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    assert "Updating chocolate" in result.stderr

    with open(chocolate_import_json) as f:
        import_data = json.load(f)
    assert import_data['sha'] == new_sha2
    assert import_data['version'] == '12'

    # Verify update commit was created
    subject, body = get_last_commit_info(workdir)
    assert subject == 'Update chocolate from 11-1 to 12-1'
    assert f"Upstream: {new_sha2}" in body


def test_sync_already_in_sync(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Sync fails when already at upstream."""
    # Import chocolate (automatically commits)
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True,
    )

    # Sync without upstream changes fails
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'sync', 'chocolate'],
        cwd=workdir, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "already at upstream" in result.stderr


def test_git_config_required(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Fails with helpful message if git user/email not configured."""

    subprocess.run(['git', 'config', '--unset', 'user.name'], cwd=workdir, check=True)
    subprocess.run(['git', 'config', '--unset', 'user.email'], cwd=workdir, check=True)
    env = os.environ.copy()
    env['GIT_CONFIG_GLOBAL'] = '/dev/null'
    env['GIT_CONFIG_SYSTEM'] = '/dev/null'

    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, capture_output=True, text=True, env=env
    )

    assert result.returncode != 0
    assert "Please configure git:" in result.stderr
    assert "git config user.name" in result.stderr

    # No changes were made (rpms/ should be unchanged)
    assert not (workdir / 'rpms' / 'chocolate').exists(), "Package should not be imported"

    # --dry-run doesn't require git config
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), '--dry-run', 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, capture_output=True, text=True, env=env, check=True
    )
    assert "Successfully imported chocolate" in result.stderr


def test_update_releases(workdir: Path, dist_git_module) -> None:
    """update-releases fetches from Bodhi and writes upstream-releases.json.

    Rawhide should NOT be written to the JSON file since it's automatically
    resolved to the highest numbered Fedora release at runtime.
    """
    # mock curl response - rawhide is included but should be filtered out
    mock_bodhi_response = {
        'releases': [
            {'id_prefix': 'FEDORA', 'branch': 'f41', 'dist_tag': 'f41'},
            {'id_prefix': 'FEDORA', 'branch': 'f43', 'dist_tag': 'f43'},
            {'id_prefix': 'FEDORA', 'branch': 'f44', 'dist_tag': 'f44'},
            {'id_prefix': 'FEDORA', 'branch': 'rawhide', 'dist_tag': 'f45'},
            {'id_prefix': 'FEDORA', 'branch': 'eln', 'dist_tag': 'eln'},
            {'id_prefix': 'FEDORA-EPEL', 'branch': 'epel9', 'dist_tag': 'epel9'},
        ]
    }

    with patch('subprocess.check_output') as mock_check_output:
        mock_check_output.return_value = json.dumps(mock_bodhi_response)

        # Run update-releases in-process
        dist_git_module.ROOT_DIR = workdir
        dist_git_module.RELEASES_JSON = workdir / 'upstream-releases.json'
        dist_git_module.update_releases()

    # Rawhide should NOT be in the JSON file
    assert json.loads((workdir / 'upstream-releases.json').read_text()) == {
        'centos': {
            'c9s': 'el9',
            'c10s': 'el10',
        },
        'fedora': {
            'eln': 'eln',
            'f41': 'f41',
            'f43': 'f43',
            'f44': 'f44',
            # rawhide is NOT stored - it's auto-resolved at runtime
            # EPEL should be filtered out (not FEDORA id_prefix)
        },
    }


def test_get_dist_tag_rawhide_auto_resolution(dist_git_module) -> None:
    """get_dist_tag automatically resolves rawhide to the highest Fedora release."""
    # Set up releases with various Fedora versions (rawhide not in the dict)
    dist_git_module.releases = {
        'fedora': {
            'f40': 'f40',
            'f42': 'f42',
            'f43': 'f43',
            'eln': 'eln',
        },
    }

    # rawhide should resolve to f43 (highest numbered release)
    assert dist_git_module.get_dist_tag('rawhide') == 'f43'

    # Other branches should work normally
    assert dist_git_module.get_dist_tag('f40') == 'f40'
    assert dist_git_module.get_dist_tag('f42') == 'f42'
    assert dist_git_module.get_dist_tag('eln') == 'eln'

    # CentOS Stream branches should still work
    assert dist_git_module.get_dist_tag('c9s') == 'el9'
    assert dist_git_module.get_dist_tag('c10s') == 'el10'


def test_expand_url_shortcut(dist_git_module) -> None:
    """expand_url_shortcut resolves fedora/ and centos/ shortcuts."""
    # Fedora shortcut
    assert dist_git_module.expand_url_shortcut('fedora/bash') == \
        'https://src.fedoraproject.org/rpms/bash.git'

    # CentOS shortcut
    assert dist_git_module.expand_url_shortcut('centos/kernel') == \
        'https://gitlab.com/redhat/centos-stream/rpms/kernel.git'

    # Full URL passes through unchanged
    full_url = 'https://gitlab.com/redhat/centos-stream/rpms/golang.git'
    assert dist_git_module.expand_url_shortcut(full_url) == full_url


def test_update_of_rebuild(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Update proceeds when local changes only affect Release: field.

    This commonly happens for rebuilds.
    """
    # Import vanilla
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Modify the Release: field locally (bump it for a rebuild)
    vanilla_spec = workdir / 'rpms' / 'vanilla' / 'vanilla.spec'
    spec_content = vanilla_spec.read_text()
    modified_content = spec_content.replace('Release: 1', 'Release: 2')
    vanilla_spec.write_text(modified_content)
    subprocess.run(['git', 'commit', '-a', '-m', 'Rebuild because reasons'], cwd=workdir, check=True)

    # Add upstream commit with new version
    new_sha = add_upstream_commit(upstream_repos["vanilla"], 'vanilla', '1.0', '2.0')

    # Update should proceed despite local Release: modification
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'update', '--skip-build-check', 'vanilla'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    # Updates successfully
    assert "Updating vanilla" in result.stderr
    assert "local modifications" not in result.stderr
    vanilla_import_json = workdir / 'metadata' / 'vanilla.json'
    with open(vanilla_import_json) as f:
        import_data = json.load(f)
    assert import_data['sha'] == new_sha
    assert import_data['version'] == '2.0'
    subject, body = get_last_commit_info(workdir)
    assert subject == 'Update vanilla from 1.0-1 to 2.0-1'
    assert f"Upstream: {new_sha}" in body

def test_mark_modified_with_reason(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Mark a clean package as modified with a reason."""
    # Import vanilla package
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Verify it starts as clean
    metadata_file = workdir / 'metadata' / 'vanilla.json'
    with open(metadata_file) as f:
        metadata = json.load(f)
    assert metadata['modification_status'] == 'clean'
    assert 'modification_reason' not in metadata

    # Mark as modified with a reason
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'mark-modified', 'vanilla', '--modified',
         '--reason', 'Backport CVE fix from upstream'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    # Verify metadata updated
    with open(metadata_file) as f:
        metadata = json.load(f)
    assert metadata['modification_status'] == 'modified'
    assert metadata['modification_reason'] == 'Backport CVE fix from upstream'


def test_mark_clean(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Mark a modified package back to clean."""
    # Import vanilla package
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Mark as modified
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'mark-modified', 'vanilla', '--modified',
         '--reason', 'Test modification'],
        cwd=workdir, check=True,
    )

    metadata_file = workdir / 'metadata' / 'vanilla.json'
    with open(metadata_file) as f:
        metadata = json.load(f)
    assert metadata['modification_status'] == 'modified'
    assert 'modification_reason' in metadata

    # Mark back to clean
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'mark-modified', 'vanilla', '--clean'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    # Verify metadata updated
    with open(metadata_file) as f:
        metadata = json.load(f)
    assert metadata['modification_status'] == 'clean'
    assert 'modification_reason' not in metadata


def test_modified_package_blocks_update(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Verify that modified packages block automatic updates."""
    # Import vanilla package
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Mark as modified
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'mark-modified', 'vanilla', '--modified',
         '--reason', 'Local patch applied'],
        cwd=workdir, check=True,
    )

    # Add upstream commit with new version
    add_upstream_commit(upstream_repos["vanilla"], 'vanilla', '1.0', '2.0')

    # Update should fail
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'update', 'vanilla'],
        cwd=workdir, capture_output=True, text=True,
    )

    # Should exit with error
    assert result.returncode != 0
    assert "Cannot auto-update vanilla" in result.stderr
    assert "Status: modified" in result.stderr
    assert "Local patch applied" in result.stderr


def test_native_package_blocks_update(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Verify that native packages block automatic updates."""
    # Create a native package manually
    native_dir = workdir / 'rpms' / 'native-pkg'
    native_dir.mkdir()
    (native_dir / 'native-pkg.spec').write_text("""Name: native-pkg
Version: 1.0
Release: 1
Summary: Native package
License: MIT

%description
Native package

%files
""")

    # Create metadata for native package
    metadata_file = workdir / 'metadata' / 'native-pkg.json'
    with open(metadata_file, 'w') as f:
        json.dump({
            'version': '1.0',
            'release': '1',
            'modification_status': 'native',
        }, f, indent=2)

    subprocess.run(['git', 'add', '.'], cwd=workdir, check=True)
    subprocess.run(['git', 'commit', '-m', 'Add native package'], cwd=workdir, check=True)

    # Update should fail
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'update', 'native-pkg'],
        cwd=workdir, capture_output=True, text=True,
    )

    # Should exit with error
    assert result.returncode != 0
    assert "Cannot auto-update native-pkg" in result.stderr
    assert "Status: native" in result.stderr


def test_list_all_packages(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Test list command shows all packages."""
    # Import vanilla package
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Create a native package
    native_dir = workdir / 'rpms' / 'native-pkg'
    native_dir.mkdir()
    (native_dir / 'native-pkg.spec').write_text("""Name: native-pkg
Version: 1.0
Release: 1
Summary: Native package
License: MIT

%description
Native package

%files
""")

    metadata_file = workdir / 'metadata' / 'native-pkg.json'
    with open(metadata_file, 'w') as f:
        json.dump({
            'version': '1.0',
            'release': '1',
            'modification_status': 'native',
        }, f, indent=2)

    subprocess.run(['git', 'add', '.'], cwd=workdir, check=True)
    subprocess.run(['git', 'commit', '-m', 'Add native package'], cwd=workdir, check=True)

    # List all packages
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'list'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    # Should show both packages
    assert 'ALL PACKAGES (2)' in result.stdout
    assert 'vanilla' in result.stdout
    assert 'native-pkg' in result.stdout
    assert '[clean]' in result.stdout
    assert '[native]' in result.stdout


def test_list_modified_only(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Test list --modified shows only modified packages."""
    # Import vanilla package
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Mark as modified
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'mark-modified', 'vanilla', '--modified',
         '--reason', 'Test modification'],
        cwd=workdir, check=True,
    )

    # List modified packages
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'list', '--modified'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    # Should show modified package with reason
    assert 'MODIFIED PACKAGES (1)' in result.stdout
    assert 'vanilla' in result.stdout
    assert '[modified]' in result.stdout
    assert 'Test modification' in result.stdout


def test_list_clean_only(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Test list --clean shows only clean packages."""
    # Import vanilla and chocolate
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True,
    )

    # Mark vanilla as modified
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'mark-modified', 'vanilla', '--modified',
         '--reason', 'Test'],
        cwd=workdir, check=True,
    )

    # List clean packages
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'list', '--clean'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    # Should show only chocolate
    assert 'CLEAN PACKAGES (1)' in result.stdout
    assert 'chocolate' in result.stdout
    assert 'vanilla' not in result.stdout


def test_list_native_only(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Test list --native shows only native packages."""
    # Import vanilla package (clean)
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Create a native package
    native_dir = workdir / 'rpms' / 'native-pkg'
    native_dir.mkdir()
    (native_dir / 'native-pkg.spec').write_text("""Name: native-pkg
Version: 1.0
Release: 1
Summary: Native package
License: MIT

%description
Native package

%files
""")

    metadata_file = workdir / 'metadata' / 'native-pkg.json'
    with open(metadata_file, 'w') as f:
        json.dump({
            'version': '1.0',
            'release': '1',
            'modification_status': 'native',
        }, f, indent=2)

    subprocess.run(['git', 'add', '.'], cwd=workdir, check=True)
    subprocess.run(['git', 'commit', '-m', 'Add native package'], cwd=workdir, check=True)

    # List native packages
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'list', '--native'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    # Should show only native package
    assert 'NATIVE PACKAGES (1)' in result.stdout
    assert 'native-pkg' in result.stdout
    assert '[native]' in result.stdout
    assert 'vanilla' not in result.stdout


def test_diff_modified_package(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Test diff shows changes for modified package."""
    # Import vanilla
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Modify spec file
    vanilla_spec = workdir / 'rpms' / 'vanilla' / 'vanilla.spec'
    spec_content = vanilla_spec.read_text()
    modified_content = spec_content.replace('Version: 1.0', 'Version: 1.1')
    vanilla_spec.write_text(modified_content)
    subprocess.run(['git', 'commit', '-a', '-m', 'Bump version'], cwd=workdir, check=True)

    # Mark as modified
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'mark-modified', 'vanilla', '--modified',
         '--reason', 'Test modification'],
        cwd=workdir, check=True,
    )

    # Run diff command
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'diff', 'vanilla'],
        cwd=workdir, capture_output=True, text=True,
    )

    # Should show the modification
    assert result.returncode == 1  # Exit code 1 means diffs found
    assert 'Version: 1.0' in result.stdout
    assert 'Version: 1.1' in result.stdout


def test_diff_clean_package(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Test diff shows nothing for clean package."""
    # Import vanilla
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Run diff command
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'diff', 'vanilla'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    # Should show nothing and exit with 0
    assert result.returncode == 0
    assert result.stdout.strip() == ''


def test_diff_native_package(workdir: Path) -> None:
    """Test diff skips native packages with message."""
    # Create a native package
    native_dir = workdir / 'rpms' / 'native-pkg'
    native_dir.mkdir()
    (native_dir / 'native-pkg.spec').write_text("""Name: native-pkg
Version: 1.0
Release: 1
Summary: Native package
License: MIT

%description
Native package

%files
""")

    metadata_file = workdir / 'metadata' / 'native-pkg.json'
    with open(metadata_file, 'w') as f:
        json.dump({
            'version': '1.0',
            'release': '1',
            'modification_status': 'native',
        }, f, indent=2)

    subprocess.run(['git', 'add', '.'], cwd=workdir, check=True)
    subprocess.run(['git', 'commit', '-m', 'Add native package'], cwd=workdir, check=True)

    # Run diff command
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'diff', 'native-pkg'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    # Should skip with message
    assert result.returncode == 0
    assert 'Native package (no upstream to diff against)' in result.stdout


def test_diff_raw_mode(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Test --raw mode shows Release: changes."""
    # Import vanilla
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Bump Release only
    vanilla_spec = workdir / 'rpms' / 'vanilla' / 'vanilla.spec'
    spec_content = vanilla_spec.read_text()
    modified_content = spec_content.replace('Release: 1', 'Release: 2')
    vanilla_spec.write_text(modified_content)
    subprocess.run(['git', 'commit', '-a', '-m', 'Rebuild'], cwd=workdir, check=True)

    # Run diff without --raw (should show nothing)
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'diff', 'vanilla'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ''

    # Run diff with --raw (should show Release change)
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'diff', 'vanilla', '--raw'],
        cwd=workdir, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert 'Release: 1' in result.stdout
    assert 'Release: 2' in result.stdout


def test_diff_name_only_mode(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Test --name-only mode shows only filenames."""
    # Import vanilla
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Modify spec file
    vanilla_spec = workdir / 'rpms' / 'vanilla' / 'vanilla.spec'
    spec_content = vanilla_spec.read_text()
    modified_content = spec_content.replace('Version: 1.0', 'Version: 1.1')
    vanilla_spec.write_text(modified_content)
    subprocess.run(['git', 'commit', '-a', '-m', 'Bump version'], cwd=workdir, check=True)

    # Run diff --name-only
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'diff', 'vanilla', '--name-only'],
        cwd=workdir, capture_output=True, text=True,
    )

    # Should show only filename
    assert result.returncode == 1
    assert 'vanilla.spec' in result.stdout
    # Should NOT show diff content
    assert 'Version:' not in result.stdout or 'differ' in result.stdout


def test_diff_all_modified(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Test --all diffs all modified packages."""
    # Import multiple packages
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True,
    )

    # Mark vanilla as modified and modify it
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'mark-modified', 'vanilla', '--modified',
         '--reason', 'Test'],
        cwd=workdir, check=True,
    )
    vanilla_spec = workdir / 'rpms' / 'vanilla' / 'vanilla.spec'
    spec_content = vanilla_spec.read_text()
    modified_content = spec_content.replace('Version: 1.0', 'Version: 1.1')
    vanilla_spec.write_text(modified_content)
    subprocess.run(['git', 'commit', '-a', '-m', 'Bump vanilla version'], cwd=workdir, check=True)

    # Mark chocolate as modified and modify it
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'mark-modified', 'chocolate', '--modified',
         '--reason', 'Test2'],
        cwd=workdir, check=True,
    )
    chocolate_spec = workdir / 'rpms' / 'chocolate' / 'chocolate.spec'
    spec_content = chocolate_spec.read_text()
    modified_content = spec_content.replace('Version: 10', 'Version: 11')
    chocolate_spec.write_text(modified_content)
    subprocess.run(['git', 'commit', '-a', '-m', 'Bump chocolate version'], cwd=workdir, check=True)

    # Run diff --all
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'diff', '--all'],
        cwd=workdir, capture_output=True, text=True,
    )

    # Should show both modified packages
    assert result.returncode == 1
    assert '=== vanilla ===' in result.stdout
    assert '=== chocolate ===' in result.stdout
    assert 'Version: 1.1' in result.stdout
    assert 'Version: 11' in result.stdout


def test_is_prerelease_tilde_notation(dist_git_module) -> None:
    """Test pre-release detection for tilde notation."""
    assert dist_git_module.is_prerelease("5.3.0~rc1") == (True, "tilde pre-release marker (~rc1)")
    assert dist_git_module.is_prerelease("2.0~beta1")[0] is True
    assert dist_git_module.is_prerelease("1.0~alpha")[0] is True
    assert dist_git_module.is_prerelease("3.0~pre")[0] is True


def test_is_prerelease_suffix_notation(dist_git_module) -> None:
    """Test pre-release detection for suffix notation."""
    assert dist_git_module.is_prerelease("5.3.0-rc1")[0] is True
    assert dist_git_module.is_prerelease("2.0.beta1")[0] is True
    assert dist_git_module.is_prerelease("1.0-alpha")[0] is True
    assert dist_git_module.is_prerelease("3.0.dev")[0] is True


def test_is_prerelease_stable_versions(dist_git_module) -> None:
    """Test that stable versions are not flagged as pre-release."""
    assert dist_git_module.is_prerelease("1.0") == (False, None)
    assert dist_git_module.is_prerelease("2.5.3") == (False, None)
    assert dist_git_module.is_prerelease("10.11.12") == (False, None)
    # Edge case: package with "dev" in name shouldn't match
    assert dist_git_module.is_prerelease("1.0device") == (False, None)


def test_is_prerelease_in_release_field(dist_git_module) -> None:
    """Test pre-release detection in release field (e.g., kernel-headers pattern)."""
    # Kernel-style pre-release in release field (7.0.0-0.rc1.15)
    is_pre, pattern = dist_git_module.is_prerelease("7.0.0", "0.rc1.15")
    assert is_pre is True
    assert "rc1" in pattern
    assert "in release" in pattern

    # Other release field pre-release patterns
    assert dist_git_module.is_prerelease("2.5.0", "0.beta1")[0] is True
    assert dist_git_module.is_prerelease("3.0.0", "0.1.alpha")[0] is True
    assert dist_git_module.is_prerelease("1.0.0", "0.rc2.5")[0] is True

    # Stable version with stable release
    assert dist_git_module.is_prerelease("1.0", "1") == (False, None)
    assert dist_git_module.is_prerelease("2.5.3", "59") == (False, None)

    # Pre-release in version should still be detected
    is_pre, pattern = dist_git_module.is_prerelease("5.3.0~rc1", "1")
    assert is_pre is True
    assert "in release" not in pattern  # Should be detected in version, not release


def test_update_skips_prerelease(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Update skips pre-release versions by default."""
    # Import vanilla
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Update upstream to pre-release version
    vanilla_spec = upstream_repos["vanilla"] / 'vanilla.spec'
    spec_content = vanilla_spec.read_text()
    modified_content = spec_content.replace('Version: 1.0', 'Version: 2.0~rc1')
    vanilla_spec.write_text(modified_content)
    subprocess.run(['git', 'add', 'vanilla.spec'], cwd=upstream_repos["vanilla"], check=True)
    subprocess.run(['git', 'commit', '-m', 'Update to 2.0~rc1'], cwd=upstream_repos["vanilla"], check=True)

    # Update should skip
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'update', 'vanilla'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    assert "pre-release version detected" in result.stderr
    assert "2.0~rc1" in result.stderr

    # Verify package not updated
    vanilla_import_json = workdir / 'metadata' / 'vanilla.json'
    with open(vanilla_import_json) as f:
        import_data = json.load(f)
    assert import_data['version'] == '1.0'


def test_update_allow_prerelease_flag(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Update with --allow-prerelease accepts pre-release versions."""
    # Import vanilla
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Update upstream to pre-release version
    vanilla_spec = upstream_repos["vanilla"] / 'vanilla.spec'
    spec_content = vanilla_spec.read_text()
    modified_content = spec_content.replace('Version: 1.0', 'Version: 2.0~rc1')
    vanilla_spec.write_text(modified_content)
    subprocess.run(['git', 'add', 'vanilla.spec'], cwd=upstream_repos["vanilla"], check=True)
    subprocess.run(['git', 'commit', '-m', 'Update to 2.0~rc1'], cwd=upstream_repos["vanilla"], check=True)

    # Update with --allow-prerelease should proceed
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'update', '--skip-build-check',
         '--allow-prerelease', 'vanilla'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    assert "Updating vanilla" in result.stderr

    # Verify package updated
    vanilla_import_json = workdir / 'metadata' / 'vanilla.json'
    with open(vanilla_import_json) as f:
        import_data = json.load(f)
    assert import_data['version'] == '2.0~rc1'


def test_update_batch_continues_on_prerelease(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Batch update continues processing after encountering pre-release."""
    # Import vanilla and chocolate
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True,
    )

    # Update vanilla to pre-release
    vanilla_spec = upstream_repos["vanilla"] / 'vanilla.spec'
    spec_content = vanilla_spec.read_text()
    modified_content = spec_content.replace('Version: 1.0', 'Version: 2.0~rc1')
    vanilla_spec.write_text(modified_content)
    subprocess.run(['git', 'add', 'vanilla.spec'], cwd=upstream_repos["vanilla"], check=True)
    subprocess.run(['git', 'commit', '-m', 'Update to 2.0~rc1'], cwd=upstream_repos["vanilla"], check=True)

    # Update chocolate to stable version
    add_upstream_commit(upstream_repos["chocolate"], 'chocolate', '10', '11')

    # Batch update should skip vanilla but update chocolate
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'update', '--skip-build-check'],
        cwd=workdir, capture_output=True, text=True,
    )

    assert "Skipping vanilla" in result.stderr or "pre-release" in result.stderr
    assert "Updating chocolate" in result.stderr
    # Exit code may be non-zero if updates occurred, that's ok
    assert result.returncode in (0, 1)


def test_sync_bypasses_prerelease_check(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Sync command bypasses pre-release check."""
    # Import vanilla
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )

    # Update upstream to pre-release version
    vanilla_spec = upstream_repos["vanilla"] / 'vanilla.spec'
    spec_content = vanilla_spec.read_text()
    modified_content = spec_content.replace('Version: 1.0', 'Version: 2.0~rc1')
    vanilla_spec.write_text(modified_content)
    subprocess.run(['git', 'add', 'vanilla.spec'], cwd=upstream_repos["vanilla"], check=True)
    subprocess.run(['git', 'commit', '-m', 'Update to 2.0~rc1'], cwd=upstream_repos["vanilla"], check=True)

    # Sync should update despite pre-release version
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'sync', 'vanilla'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    assert "Syncing vanilla" in result.stderr

    # Verify package updated
    vanilla_import_json = workdir / 'metadata' / 'vanilla.json'
    with open(vanilla_import_json) as f:
        import_data = json.load(f)
    assert import_data['version'] == '2.0~rc1'


def test_list_prerelease_packages(workdir: Path, upstream_repos: dict[str, Path]) -> None:
    """Test list --prerelease shows only packages with pre-release versions."""
    # Import vanilla and chocolate
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["vanilla"]}'],
        cwd=workdir, check=True,
    )
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'import', f'file://{upstream_repos["chocolate"]}'],
        cwd=workdir, check=True,
    )

    # Update vanilla to pre-release version
    vanilla_spec = upstream_repos["vanilla"] / 'vanilla.spec'
    spec_content = vanilla_spec.read_text()
    modified_content = spec_content.replace('Version: 1.0', 'Version: 2.0~rc1')
    vanilla_spec.write_text(modified_content)
    subprocess.run(['git', 'add', 'vanilla.spec'], cwd=upstream_repos["vanilla"], check=True)
    subprocess.run(['git', 'commit', '-m', 'Update to 2.0~rc1'], cwd=upstream_repos["vanilla"], check=True)

    # Update vanilla package to pre-release
    subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'sync', 'vanilla'],
        cwd=workdir, check=True,
    )

    # List pre-release packages
    result = subprocess.run(
        [str(workdir / 'ci' / 'dist_git.py'), 'list', '--prerelease'],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    # Should only show vanilla, not chocolate
    assert 'vanilla' in result.stdout
    assert '2.0~rc1' in result.stdout
    assert 'chocolate' not in result.stdout
    assert 'PRE-RELEASE PACKAGES (1):' in result.stdout
