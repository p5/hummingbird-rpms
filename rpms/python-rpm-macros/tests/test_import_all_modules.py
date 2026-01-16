from import_all_modules import argparser, exclude_unwanted_module_globs, import_modules
from import_all_modules import main as modules_main
from import_all_modules import read_modules_from_cli, filter_top_level_modules_only

from pathlib import Path

import pytest
import shlex
import sys


@pytest.fixture(autouse=True)
def preserve_sys_path():
    original_sys_path = list(sys.path)
    yield
    sys.path = original_sys_path


@pytest.fixture(autouse=True)
def preserve_sys_modules():
    original_sys_modules = dict(sys.modules)
    yield
    sys.modules = original_sys_modules


@pytest.mark.parametrize(
    'args, imports',
    [
        ('six', ['six']),
        ('five  six seven', ['five', 'six', 'seven']),
        ('six,seven, eight', ['six', 'seven', 'eight']),
        ('six.quarter  six.half,, SIX', ['six.quarter', 'six.half', 'SIX']),
        ('six.quarter  six.half,, SIX \\ ', ['six.quarter', 'six.half', 'SIX']),
    ]
)
def test_read_modules_from_cli(args, imports):
    argv = shlex.split(args)
    cli_args = argparser().parse_args(argv)
    assert read_modules_from_cli(cli_args.modules) == imports


@pytest.mark.parametrize(
    'all_mods, imports',
    [
        (['six'], ['six']),
        (['five', 'six', 'seven'], ['five', 'six', 'seven']),
        (['six.seven', 'eight'], ['eight']),
        (['SIX', 'six.quarter', 'six.half.and.sth', 'seven'], ['SIX', 'seven']),
    ],
)
def test_filter_top_level_modules_only(all_mods, imports):
    assert filter_top_level_modules_only(all_mods) == imports


@pytest.mark.parametrize(
    'globs, expected',
    [
        (['*.*'], ['foo', 'boo']),
        (['?oo'], ['foo.bar', 'foo.bar.baz', 'foo.baz']),
        (['*.baz'], ['foo', 'foo.bar', 'boo']),
        (['foo'], ['foo.bar', 'foo.bar.baz', 'foo.baz', 'boo']),
        (['foo*'], ['boo']),
        (['foo*', '*bar'], ['boo']),
        (['foo', 'bar'], ['foo.bar', 'foo.bar.baz', 'foo.baz', 'boo']),
        (['*'], []),
    ]
)
def test_exclude_unwanted_module_globs(globs, expected):
    my_modules = ['foo', 'foo.bar', 'foo.bar.baz', 'foo.baz', 'boo']
    tested = exclude_unwanted_module_globs(globs, my_modules)
    assert tested == expected


def test_cli_with_all_args():
    '''A smoke test, all args must be parsed correctly.'''
    mods = ['foo', 'foo.bar', 'baz']
    files = ['-f', './foo']
    top = ['-t']
    exclude = ['-e', 'foo*']
    cli_args = argparser().parse_args([*mods, *files, *top, *exclude])

    assert cli_args.filename == [Path('foo')]
    assert cli_args.top_level is True
    assert cli_args.modules == ['foo', 'foo.bar', 'baz']
    assert cli_args.exclude == ['foo*']


def test_cli_without_filename_toplevel():
    '''Modules provided on command line (without files) must be parsed correctly.'''
    mods = ['foo', 'foo.bar', 'baz']
    cli_args = argparser().parse_args(mods)

    assert cli_args.filename is None
    assert cli_args.top_level is False
    assert cli_args.modules == ['foo', 'foo.bar', 'baz']


def test_cli_with_filename_no_cli_mods():
    '''Files (without any modules provided on command line) must be parsed correctly.'''

    files = ['-f', './foo', '-f', './bar', '-f', './baz']
    cli_args = argparser().parse_args(files)

    assert cli_args.filename == [Path('foo'), Path('./bar'), Path('./baz')]
    assert not cli_args.top_level


def test_main_raises_error_when_no_modules_provided():
    '''If no filename nor modules were provided, ValueError is raised.'''

    with pytest.raises(ValueError):
        modules_main([])


def test_import_all_modules_does_not_import():
    '''Ensure the files from /usr/lib/rpm/redhat cannot be imported and
    checked for import'''

    # We already imported it in this file once, make sure it's not imported
    # from the cache
    sys.modules.pop('import_all_modules')
    with pytest.raises(SystemExit):
        modules_main(['import_all_modules'])


def test_modules_from_cwd_not_found(tmp_path, monkeypatch):
    test_module = tmp_path / 'this_is_a_module_in_cwd.py'
    test_module.write_text('')
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        modules_main(['this_is_a_module_in_cwd'])


def test_modules_from_sys_path_found(tmp_path):
    test_module = tmp_path / 'this_is_a_module_in_sys_path.py'
    test_module.write_text('')
    sys.path.append(str(tmp_path))
    modules_main(['this_is_a_module_in_sys_path'])
    assert 'this_is_a_module_in_sys_path' in sys.modules


def test_modules_from_file_are_found(tmp_path):
    test_file = tmp_path / 'this_is_a_file_in_tmp_path.txt'
    test_file.write_text('math\nwave\ncsv\n')

    # Make sure the tested modules are not already in sys.modules
    for m in ('math', 'wave', 'csv'):
        sys.modules.pop(m, None)

    modules_main(['-f', str(test_file)])

    assert 'csv' in sys.modules
    assert 'math' in sys.modules
    assert 'wave' in sys.modules


def test_modules_from_files_are_found(tmp_path):
    test_file_1 = tmp_path / 'this_is_a_file_in_tmp_path_1.txt'
    test_file_2 = tmp_path / 'this_is_a_file_in_tmp_path_2.txt'
    test_file_3 = tmp_path / 'this_is_a_file_in_tmp_path_3.txt'

    test_file_1.write_text('math\nwave\n')
    test_file_2.write_text('csv\nnetrc\n')
    test_file_3.write_text('logging\ncsv\n')

    # Make sure the tested modules are not already in sys.modules
    for m in ('math', 'wave', 'csv', 'netrc', 'logging'):
        sys.modules.pop(m, None)

    modules_main(['-f', str(test_file_1), '-f', str(test_file_2), '-f', str(test_file_3), ])
    for module in ('csv', 'math', 'wave', 'netrc', 'logging'):
        assert module in sys.modules


def test_nonexisting_modules_raise_exception_on_import(tmp_path):
    test_file = tmp_path / 'this_is_a_file_in_tmp_path.txt'
    test_file.write_text('nonexisting_module\nanother\n')
    with pytest.raises(SystemExit):
        modules_main(['-f', str(test_file)])


def test_nested_modules_found_when_expected(tmp_path, monkeypatch, capsys):

    # This one is supposed to raise an error
    cwd_path = tmp_path / 'test_cwd'
    Path.mkdir(cwd_path)
    test_module_1 = cwd_path / 'this_is_a_module_in_cwd.py'

    # Nested structure that is supposed to be importable
    nested_path_1 = tmp_path / 'nested'
    nested_path_2 = nested_path_1 / 'more_nested'

    for path in (nested_path_1, nested_path_2):
        Path.mkdir(path)

    test_module_2 = tmp_path / 'this_is_a_module_in_level_0.py'
    test_module_3 = nested_path_1 / 'this_is_a_module_in_level_1.py'
    test_module_4 = nested_path_2 / 'this_is_a_module_in_level_2.py'

    for module in (test_module_1, test_module_2, test_module_3, test_module_4):
        module.write_text('')

    sys.path.append(str(tmp_path))
    monkeypatch.chdir(cwd_path)

    with pytest.raises(SystemExit):
        modules_main([
            'this_is_a_module_in_level_0',
            'nested.this_is_a_module_in_level_1',
            'nested.more_nested.this_is_a_module_in_level_2',
            'this_is_a_module_in_cwd'])

    _, err = capsys.readouterr()
    assert 'Check import: this_is_a_module_in_level_0' in err
    assert 'Check import: nested.this_is_a_module_in_level_1' in err
    assert 'Check import: nested.more_nested.this_is_a_module_in_level_2' in err
    assert 'Check import: this_is_a_module_in_cwd' in err


def test_modules_both_from_files_and_cli_are_imported(tmp_path):
    test_file_1 = tmp_path / 'this_is_a_file_in_tmp_path_1.txt'
    test_file_1.write_text('this_is_a_module_in_tmp_path_1')

    test_file_2 = tmp_path / 'this_is_a_file_in_tmp_path_2.txt'
    test_file_2.write_text('this_is_a_module_in_tmp_path_2')

    test_module_1 = tmp_path / 'this_is_a_module_in_tmp_path_1.py'
    test_module_2 = tmp_path / 'this_is_a_module_in_tmp_path_2.py'
    test_module_3 = tmp_path / 'this_is_a_module_in_tmp_path_3.py'

    for module in (test_module_1, test_module_2, test_module_3):
        module.write_text('')

    sys.path.append(str(tmp_path))
    modules_main([
        '-f', str(test_file_1),
        'this_is_a_module_in_tmp_path_3',
        '-f', str(test_file_2),
    ])

    expected = (
        'this_is_a_module_in_tmp_path_1',
        'this_is_a_module_in_tmp_path_2',
        'this_is_a_module_in_tmp_path_3',
    )
    for module in expected:
        assert module in sys.modules


def test_non_existing_module_raises_exception(tmp_path):

    test_module_1 = tmp_path / 'this_is_a_module_in_tmp_path_1.py'
    test_module_1.write_text('')
    sys.path.append(str(tmp_path))

    with pytest.raises(SystemExit):
        modules_main([
            'this_is_a_module_in_tmp_path_1',
            'this_is_a_module_in_tmp_path_2',
        ])


def test_import_module_returns_failed_modules(tmp_path):
    test_module_1 = tmp_path / 'this_is_a_module_in_tmp_path_1.py'
    test_module_1.write_text('')
    sys.path.append(str(tmp_path))

    failed_modules = import_modules([
        'this_is_a_module_in_tmp_path_1',
        'this_is_a_module_in_tmp_path_2',
    ])

    assert failed_modules == ['this_is_a_module_in_tmp_path_2']


def test_module_with_error_propagates_exception(tmp_path, capsys):

    test_module_1 = tmp_path / 'this_is_a_module_in_tmp_path_1.py'
    test_module_1.write_text('0/0')
    sys.path.append(str(tmp_path))

    with pytest.raises(SystemExit):
        modules_main([
            'this_is_a_module_in_tmp_path_1',
        ])
    _, err = capsys.readouterr()
    assert "ZeroDivisionError" in err


def test_import_module_returns_empty_list_when_no_modules_failed(tmp_path):
    test_module_1 = tmp_path / 'this_is_a_module_in_tmp_path_1.py'
    test_module_1.write_text('')
    sys.path.append(str(tmp_path))

    failed_modules = import_modules(['this_is_a_module_in_tmp_path_1'])
    assert failed_modules == []


def test_all_modules_are_imported(tmp_path, capsys):
    test_module_1 = tmp_path / 'this_is_a_module_in_tmp_path_1.py'
    test_module_2 = tmp_path / 'this_is_a_module_in_tmp_path_2.py'
    test_module_3 = tmp_path / 'this_is_a_module_in_tmp_path_3.py'

    for module in (test_module_1, test_module_2, test_module_3):
        module.write_text('')

    sys.path.append(str(tmp_path))

    with pytest.raises(SystemExit):
        modules_main([
            'this_is_a_module_in_tmp_path_1',
            'missing_module',
            'this_is_a_module_in_tmp_path_2',
            'this_is_a_module_in_tmp_path_3',
        ])
    _, err = capsys.readouterr()
    for i in range(1, 4):
        assert f"Check import: this_is_a_module_in_tmp_path_{i}" in err
    assert "Failed to import: missing_module" in err


def test_correct_modules_are_excluded(tmp_path):
    test_module_1 = tmp_path / 'module_in_tmp_path_1.py'
    test_module_2 = tmp_path / 'module_in_tmp_path_2.py'
    test_module_3 = tmp_path / 'module_in_tmp_path_3.py'

    for module in (test_module_1, test_module_2, test_module_3):
        module.write_text('')

    sys.path.append(str(tmp_path))
    test_file_1 = tmp_path / 'a_file_in_tmp_path_1.txt'
    test_file_1.write_text('module_in_tmp_path_1\nmodule_in_tmp_path_2\nmodule_in_tmp_path_3\n')

    modules_main([
        '-e', 'module_in_tmp_path_2',
        '-f', str(test_file_1),
        '-e', 'module_in_tmp_path_3',
        ])

    assert 'module_in_tmp_path_1' in sys.modules
    assert 'module_in_tmp_path_2' not in sys.modules
    assert 'module_in_tmp_path_3' not in sys.modules


def test_excluding_all_modules_raises_error(tmp_path):
    test_module_1 = tmp_path / 'module_in_tmp_path_1.py'
    test_module_2 = tmp_path / 'module_in_tmp_path_2.py'
    test_module_3 = tmp_path / 'module_in_tmp_path_3.py'

    for module in (test_module_1, test_module_2, test_module_3):
        module.write_text('')

    sys.path.append(str(tmp_path))
    test_file_1 = tmp_path / 'a_file_in_tmp_path_1.txt'
    test_file_1.write_text('module_in_tmp_path_1\nmodule_in_tmp_path_2\nmodule_in_tmp_path_3\n')

    with pytest.raises(ValueError):
        modules_main([
            '-e', 'module_in_tmp_path*',
            '-f', str(test_file_1),
            ])


def test_only_toplevel_modules_found(tmp_path):

    # Nested structure that is supposed to be importable
    nested_path_1 = tmp_path / 'nested'
    nested_path_2 = nested_path_1 / 'more_nested'

    for path in (nested_path_1, nested_path_2):
        Path.mkdir(path)

    test_module_1 = tmp_path / 'this_is_a_module_in_level_0.py'
    test_module_2 = nested_path_1 / 'this_is_a_module_in_level_1.py'
    test_module_3 = nested_path_2 / 'this_is_a_module_in_level_2.py'

    for module in (test_module_1, test_module_2, test_module_3):
        module.write_text('')

    sys.path.append(str(tmp_path))

    modules_main([
        'this_is_a_module_in_level_0',
        'nested.this_is_a_module_in_level_1',
        'nested.more_nested.this_is_a_module_in_level_2',
        '-t'])

    assert 'nested.this_is_a_module_in_level_1' not in sys.modules
    assert 'nested.more_nested.this_is_a_module_in_level_2' not in sys.modules


def test_only_toplevel_included_modules_found(tmp_path):

    # Nested structure that is supposed to be importable
    nested_path_1 = tmp_path / 'nested'
    nested_path_2 = nested_path_1 / 'more_nested'

    for path in (nested_path_1, nested_path_2):
        Path.mkdir(path)

    test_module_1 = tmp_path / 'this_is_a_module_in_level_0.py'
    test_module_4 = tmp_path / 'this_is_another_module_in_level_0.py'

    test_module_2 = nested_path_1 / 'this_is_a_module_in_level_1.py'
    test_module_3 = nested_path_2 / 'this_is_a_module_in_level_2.py'

    for module in (test_module_1, test_module_2, test_module_3, test_module_4):
        module.write_text('')

    sys.path.append(str(tmp_path))

    modules_main([
        'this_is_a_module_in_level_0',
        'this_is_another_module_in_level_0',
        'nested.this_is_a_module_in_level_1',
        'nested.more_nested.this_is_a_module_in_level_2',
        '-t',
        '-e', '*another*'
    ])

    assert 'nested.this_is_a_module_in_level_1' not in sys.modules
    assert 'nested.more_nested.this_is_a_module_in_level_2' not in sys.modules
    assert 'this_is_another_module_in_level_0' not in sys.modules
    assert 'this_is_a_module_in_level_0' in sys.modules


def test_module_list_from_relative_path(tmp_path, monkeypatch):

    monkeypatch.chdir(tmp_path)
    test_file_1 = Path('this_is_a_file_in_cwd.txt')
    test_file_1.write_text('wave')

    sys.modules.pop('wave', None)

    modules_main([
        '-f', 'this_is_a_file_in_cwd.txt'
    ])

    assert 'wave' in sys.modules


@pytest.mark.parametrize('arch_in_path', [True, False])
def test_pth_files_are_read_from__PYTHONSITE(arch_in_path, tmp_path, monkeypatch, capsys):
    sitearch = tmp_path / 'lib64'
    sitearch.mkdir()
    sitelib = tmp_path / 'lib'
    sitelib.mkdir()

    for where, word in (sitearch, "ARCH"), (sitelib, "LIB"), (sitelib, "MOD"):
        module = where / f'print{word}.py'
        module.write_text(f'print("{word}")')

    pth_sitearch = sitearch / 'ARCH.pth'
    pth_sitearch.write_text('import printARCH\n')

    pth_sitelib = sitelib / 'LIB.pth'
    pth_sitelib.write_text('import printLIB\n')

    if arch_in_path:
        sys.path.append(str(sitearch))
    sys.path.append(str(sitelib))

    # we always add sitearch to _PYTHONSITE
    # but when not in sys.path, it should not be processed for .pth files
    monkeypatch.setenv('_PYTHONSITE', f'{sitearch}:{sitelib}')

    modules_main(['printMOD'])
    out, err = capsys.readouterr()
    if arch_in_path:
        assert out == 'ARCH\nLIB\nMOD\n'
    else:
        assert out == 'LIB\nMOD\n'
