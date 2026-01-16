import os
import subprocess
import platform
import re
import sys
import textwrap

import pytest

X_Y = f'{sys.version_info[0]}.{sys.version_info[1]}'
XY = f'{sys.version_info[0]}{sys.version_info[1]}'

# Handy environment variable you can use to run the tests
# with modified macros files. Multiple files should be
# separated by colon.
# You can use * if you escape it from your Shell:
# TESTED_FILES='macros.*' pytest -v
# Remember that some tests might need more macros files than just
# the local ones. You might need to use:
# TESTED_FILES='/usr/lib/rpm/macros:/usr/lib/rpm/platform/x86_64-linux/macros:macros.*'
TESTED_FILES = os.getenv("TESTED_FILES", None)


def rpm_eval(expression, fails=False, **kwargs):
    if isinstance(expression, str):
        expression = [expression]
    cmd = ['rpmbuild']
    if TESTED_FILES:
        cmd += ['--macros', TESTED_FILES]
    for var, value in kwargs.items():
        if value is None:
            cmd += ['--undefine', var]
        else:
            cmd += ['--define', f'{var} {value}']
    for e in expression:
        cmd += ['--eval', e]
    cp = subprocess.run(cmd, text=True, env={**os.environ, 'LANG': 'C.utf-8'},
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if fails:
        assert cp.returncode != 0, cp.stdout
    elif fails is not None:
        assert cp.returncode == 0, cp.stdout
    return cp.stdout.strip().splitlines()


@pytest.fixture(scope="session")
def lib():
    lib_eval = rpm_eval("%_lib")[0]
    if lib_eval == "%_lib" and TESTED_FILES:
        raise ValueError(
            "%_lib is not resolved to an actual value. "
            "You may want to include /usr/lib/rpm/platform/x86_64-linux/macros to TESTED_FILES."
        )
    return lib_eval


def get_alt_x_y():
    """
    Some tests require alternate Python version to be installed.
    In order to allow any Python version (or none at all),
    this function/fixture exists.
    You can control the behavior by setting the $ALTERNATE_PYTHON_VERSION
    environment variable to X.Y (e.g. 3.6) or SKIP.
    The environment variable must be set.
    """
    env_name = "ALTERNATE_PYTHON_VERSION"
    alternate_python_version = os.getenv(env_name, "")
    if alternate_python_version.upper() == "SKIP":
        pytest.skip(f"${env_name} set to SKIP")
    if not alternate_python_version:
        raise ValueError(f"${env_name} must be set, "
                         f"set it to SKIP if you want to skip tests that "
                         f"require alternate Python version.")
    if not re.match(r"^\d+\.\d+$", alternate_python_version):
        raise ValueError(f"${env_name} must be X.Y")
    return alternate_python_version


def get_alt_xy():
    """
    Same as get_alt_x_y() but without a dot
    """
    return get_alt_x_y().replace(".", "")


# We don't use decorators, to be able to call the functions directly
alt_x_y = pytest.fixture(scope="session")(get_alt_x_y)
alt_xy = pytest.fixture(scope="session")(get_alt_xy)


# https://fedoraproject.org/wiki/Changes/PythonSafePath
def safe_path_flag(x_y):
    return 'P' if tuple(int(i) for i in x_y.split('.')) >= (3, 11) else ''


def shell_stdout(script):
    return subprocess.check_output(script,
                                   env={**os.environ, 'LANG': 'C.utf-8'},
                                   text=True,
                                   shell=True).rstrip()


@pytest.mark.parametrize('macro', ['%__python3', '%python3'])
def test_python3(macro):
    assert rpm_eval(macro) == ['/usr/bin/python3']


@pytest.mark.parametrize('macro', ['%__python3', '%python3'])
@pytest.mark.parametrize('pkgversion', ['3', '3.9', '3.12'])
def test_python3_with_pkgversion(macro, pkgversion):
    assert rpm_eval(macro, python3_pkgversion=pkgversion) == [f'/usr/bin/python{pkgversion}']


@pytest.mark.parametrize('argument, result', [
    ('a', 'a'),
    ('a-a', 'a-a'),
    ('a_a', 'a-a'),
    ('a.a', 'a-a'),
    ('a---a', 'a-a'),
    ('a-_-a', 'a-a'),
    ('a-_-a', 'a-a'),
    ('a[b]', 'a[b]'),
    ('Aha[Boom]', 'aha[boom]'),
    ('a.a[b.b]', 'a-a[b-b]'),
])
def test_pydist_name(argument, result):
    assert rpm_eval(f'%py_dist_name {argument}') == [result]


def test_py2_dist():
    assert rpm_eval(f'%py2_dist Aha[Boom] a') == ['python2dist(aha[boom]) python2dist(a)']


def test_py3_dist():
    assert rpm_eval(f'%py3_dist Aha[Boom] a') == ['python3dist(aha[boom]) python3dist(a)']


def test_py3_dist_with_python3_pkgversion_redefined(alt_x_y):
    assert rpm_eval(f'%py3_dist Aha[Boom] a', python3_pkgversion=alt_x_y) == [f'python{alt_x_y}dist(aha[boom]) python{alt_x_y}dist(a)']


def test_python_provide_python():
    assert rpm_eval('%python_provide python-foo') == []


def test_python_provide_python3():
    lines = rpm_eval('%python_provide python3-foo', version='6', release='1.fc66')
    assert 'Obsoletes: python-foo < 6-1.fc66' in lines
    assert 'Provides: python-foo = 6-1.fc66' in lines
    assert f'Provides: python{X_Y}-foo = 6-1.fc66' in lines
    assert len(lines) == 3


def test_python_provide_python3_epoched():
    lines = rpm_eval('%python_provide python3-foo', epoch='1', version='6', release='1.fc66')
    assert 'Obsoletes: python-foo < 1:6-1.fc66' in lines
    assert 'Provides: python-foo = 1:6-1.fc66' in lines
    assert f'Provides: python{X_Y}-foo = 1:6-1.fc66' in lines
    assert len(lines) == 3


def test_python_provide_python3X():
    lines = rpm_eval(f'%python_provide python{X_Y}-foo', version='6', release='1.fc66')
    assert 'Obsoletes: python-foo < 6-1.fc66' in lines
    assert 'Provides: python-foo = 6-1.fc66' in lines
    assert 'Provides: python3-foo = 6-1.fc66' in lines
    assert len(lines) == 3


def test_python_provide_python3X_epoched():
    lines = rpm_eval(f'%python_provide python{X_Y}-foo', epoch='1', version='6', release='1.fc66')
    assert 'Obsoletes: python-foo < 1:6-1.fc66' in lines
    assert 'Provides: python-foo = 1:6-1.fc66' in lines
    assert 'Provides: python3-foo = 1:6-1.fc66' in lines
    assert len(lines) == 3


def test_python_provide_doubleuse():
    lines = rpm_eval('%{python_provide python3-foo}%{python_provide python3-foo}',
                     version='6', release='1.fc66')
    assert 'Obsoletes: python-foo < 6-1.fc66' in lines
    assert 'Provides: python-foo = 6-1.fc66' in lines
    assert f'Provides: python{X_Y}-foo = 6-1.fc66' in lines
    assert len(lines) == 6
    assert len(set(lines)) == 3


@pytest.mark.parametrize('rhel', [None, 10])
def test_py_provides_python(rhel):
    lines = rpm_eval('%py_provides python-foo', version='6', release='1.fc66', rhel=rhel)
    assert 'Provides: python-foo = 6-1.fc66' in lines
    assert len(lines) == 1


@pytest.mark.parametrize('rhel', [None, 12])
def test_py_provides_whatever(rhel):
    lines = rpm_eval('%py_provides whatever', version='6', release='1.fc66', rhel=rhel)
    assert 'Provides: whatever = 6-1.fc66' in lines
    assert len(lines) == 1


@pytest.mark.parametrize('rhel', [None, 9])
def test_py_provides_python3(rhel):
    lines = rpm_eval('%py_provides python3-foo', version='6', release='1.fc66', rhel=rhel)
    assert 'Provides: python3-foo = 6-1.fc66' in lines
    assert 'Provides: python-foo = 6-1.fc66' in lines
    assert f'Provides: python{X_Y}-foo = 6-1.fc66' in lines
    if rhel:
        assert f'Obsoletes: python{X_Y}-foo < 6-1.fc66' in lines
        assert len(lines) == 4
    else:
        assert len(lines) == 3


@pytest.mark.parametrize('rhel', [None, 9])
def test_py_provides_python3_with_isa(rhel):
    lines = rpm_eval('%py_provides python3-foo(x86_64)', version='6', release='1.fc66', rhel=rhel)
    assert 'Provides: python3-foo(x86_64) = 6-1.fc66' in lines
    assert 'Provides: python-foo(x86_64) = 6-1.fc66' in lines
    assert f'Provides: python{X_Y}-foo(x86_64) = 6-1.fc66' in lines
    assert f'Obsoletes: python{X_Y}-foo(x86_64) < 6-1.fc66' not in lines
    assert len(lines) == 3


@pytest.mark.parametrize('rhel', [None, 13])
def test_py_provides_python3_epoched(rhel):
    lines = rpm_eval('%py_provides python3-foo', epoch='1', version='6', release='1.fc66', rhel=rhel)
    assert 'Provides: python3-foo = 1:6-1.fc66' in lines
    assert 'Provides: python-foo = 1:6-1.fc66' in lines
    assert f'Provides: python{X_Y}-foo = 1:6-1.fc66' in lines
    if rhel:
        assert f'Obsoletes: python{X_Y}-foo < 1:6-1.fc66' in lines
        assert len(lines) == 4
    else:
        assert len(lines) == 3


@pytest.mark.parametrize('rhel', [None, 13])
def test_py_provides_python3X(rhel):
    lines = rpm_eval(f'%py_provides python{X_Y}-foo', version='6', release='1.fc66', rhel=rhel)
    assert f'Provides: python{X_Y}-foo = 6-1.fc66' in lines
    assert 'Provides: python-foo = 6-1.fc66' in lines
    assert 'Provides: python3-foo = 6-1.fc66' in lines
    assert len(lines) == 3


@pytest.mark.parametrize('rhel', [None, 27])
def test_py_provides_python3X_epoched(rhel):
    lines = rpm_eval(f'%py_provides python{X_Y}-foo', epoch='1', version='6', release='1.fc66', rhel=rhel)
    assert f'Provides: python{X_Y}-foo = 1:6-1.fc66' in lines
    assert 'Provides: python-foo = 1:6-1.fc66' in lines
    assert 'Provides: python3-foo = 1:6-1.fc66' in lines
    assert len(lines) == 3


@pytest.mark.parametrize('rhel', [None, 2])
def test_py_provides_doubleuse(rhel):
    lines = rpm_eval('%{py_provides python3-foo}%{py_provides python3-foo}',
                     version='6', release='1.fc66', rhel=rhel)
    assert 'Provides: python3-foo = 6-1.fc66' in lines
    assert 'Provides: python-foo = 6-1.fc66' in lines
    assert f'Provides: python{X_Y}-foo = 6-1.fc66' in lines
    if rhel:
        assert f'Obsoletes: python{X_Y}-foo < 6-1.fc66' in lines
        assert len(lines) == 8
        assert len(set(lines)) == 4
    else:
        assert len(lines) == 6
        assert len(set(lines)) == 3


@pytest.mark.parametrize('rhel', [None, 2])
def test_py_provides_with_evr(rhel):
    lines = rpm_eval('%py_provides python3-foo 123',
                     version='6', release='1.fc66', rhel=rhel)
    assert 'Provides: python3-foo = 123' in lines
    assert 'Provides: python-foo = 123' in lines
    assert f'Provides: python{X_Y}-foo = 123' in lines
    if rhel:
        assert f'Obsoletes: python{X_Y}-foo < 123' in lines
        assert len(lines) == 4
    else:
        assert len(lines) == 3


def test_python_wheel_pkg_prefix():
    assert rpm_eval('%python_wheel_pkg_prefix', fedora='44', rhel=None, eln=None) == ['python']
    assert rpm_eval('%python_wheel_pkg_prefix', fedora='44', rhel=None, eln=None, python3_pkgversion='3.9') == ['python']
    assert rpm_eval('%python_wheel_pkg_prefix', fedora=None, rhel='1', eln='1') == ['python']
    assert rpm_eval('%python_wheel_pkg_prefix', fedora=None, rhel='1', eln=None) == ['python3']
    assert rpm_eval('%python_wheel_pkg_prefix', fedora=None, rhel='1', eln=None, python3_pkgversion='3.10') == ['python3.10']
    assert rpm_eval('%python_wheel_pkg_prefix', fedora=None, rhel='1', eln=None, python3_pkgversion='3.11') == ['python3.11']


def test_python_wheel_dir():
    assert rpm_eval('%python_wheel_dir', fedora='44', rhel=None, eln=None) == ['/usr/share/python-wheels']
    assert rpm_eval('%python_wheel_dir', fedora='44', rhel=None, eln=None, python3_pkgversion='3.9') == ['/usr/share/python-wheels']
    assert rpm_eval('%python_wheel_dir', fedora=None, rhel='1', eln='1') == ['/usr/share/python-wheels']
    assert rpm_eval('%python_wheel_dir', fedora=None, rhel='1', eln=None) == ['/usr/share/python3-wheels']
    assert rpm_eval('%python_wheel_dir', fedora=None, rhel='1', eln=None, python3_pkgversion='3.10') == ['/usr/share/python3.10-wheels']
    assert rpm_eval('%python_wheel_dir', fedora=None, rhel='1', eln=None, python3_pkgversion='3.11') == ['/usr/share/python3.11-wheels']


def test_pytest_passes_options_naturally():
    lines = rpm_eval('%pytest -k foo')
    assert '/usr/bin/pytest -k foo' in lines[-1]


def test_pytest_different_command():
    lines = rpm_eval('%pytest', __pytest='pytest-3')
    assert 'pytest-3' in lines[-1]


def test_pytest_command_suffix():
    lines = rpm_eval('%pytest -v')
    assert '/usr/bin/pytest -v' in lines[-1]

# this test does not require alternate Pythons to be installed
@pytest.mark.parametrize('version', ['3.6', '3.7', '3.12'])
def test_pytest_command_suffix_alternate_pkgversion(version):
    lines = rpm_eval('%pytest -v', python3_pkgversion=version, python3_version=version)
    assert f'/usr/bin/pytest-{version} -v' in lines[-1]


def test_pytest_sets_pytest_xdist_auto_num_workers():
    lines = rpm_eval('%pytest', _smp_build_ncpus=2)
    assert 'PYTEST_XDIST_AUTO_NUM_WORKERS="${PYTEST_XDIST_AUTO_NUM_WORKERS:-2}"' in '\n'.join(lines)


def test_pytest_undefined_addopts_are_not_set():
    lines = rpm_eval('%pytest', __pytest_addopts=None)
    assert 'PYTEST_ADDOPTS' not in '\n'.join(lines)


def test_pytest_defined_addopts_are_set():
    lines = rpm_eval('%pytest', __pytest_addopts="--ignore=stuff")
    assert 'PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} --ignore=stuff"' in '\n'.join(lines)


@pytest.mark.parametrize('__pytest_addopts', ['--macronized-option', 'x y z', None])
def test_pytest_addopts_preserves_envvar(__pytest_addopts):
    # this is the line a packager might put in the spec file before running %pytest:
    spec_line = 'export PYTEST_ADDOPTS="--exported-option1 --exported-option2"'

    # instead of actually running /usr/bin/pytest,
    # we run a small shell script that echoes the tested value for inspection
    lines = rpm_eval('%pytest', __pytest_addopts=__pytest_addopts,
                     __pytest="sh -c 'echo $PYTEST_ADDOPTS'")

    echoed = shell_stdout('\n'.join([spec_line] + lines))

    # assert all values were echoed
    assert '--exported-option1' in echoed
    assert '--exported-option2' in echoed
    if __pytest_addopts is not None:
        assert __pytest_addopts in echoed

    # assert the options are separated
    assert 'option--' not in echoed
    assert 'z--' not in echoed


@pytest.mark.parametrize('__pytest_addopts', ['-X', None])
def test_py3_test_envvars(lib, __pytest_addopts):
    lines = rpm_eval('%{py3_test_envvars}\\\n%{python3} -m unittest',
                     buildroot='BUILDROOT',
                     _smp_build_ncpus='3',
                     __pytest_addopts=__pytest_addopts)
    assert all(l.endswith('\\') for l in lines[:-1])
    stripped_lines = [l.strip(' \\') for l in lines]
    sitearch = f'BUILDROOT/usr/{lib}/python{X_Y}/site-packages'
    sitelib = f'BUILDROOT/usr/lib/python{X_Y}/site-packages'
    assert f'PYTHONPATH="${{PYTHONPATH:-{sitearch}:{sitelib}}}"' in stripped_lines
    assert 'PATH="BUILDROOT/usr/bin:$PATH"' in stripped_lines
    assert 'CFLAGS="${CFLAGS:-${RPM_OPT_FLAGS}}" LDFLAGS="${LDFLAGS:-${RPM_LD_FLAGS}}"' in stripped_lines
    assert 'PYTHONDONTWRITEBYTECODE=1' in stripped_lines
    assert 'PYTEST_XDIST_AUTO_NUM_WORKERS="${PYTEST_XDIST_AUTO_NUM_WORKERS:-3}"' in stripped_lines
    if __pytest_addopts:
        assert f'PYTEST_ADDOPTS="${{PYTEST_ADDOPTS:-}} {__pytest_addopts}"' in stripped_lines
    else:
        assert 'PYTEST_ADDOPTS' not in ''.join(lines)
    assert stripped_lines[-1] == '/usr/bin/python3 -m unittest'


def test_pypi_source_default_name():
    urls = rpm_eval('%pypi_source',
                    name='foo', version='6')
    assert urls == ['https://files.pythonhosted.org/packages/source/f/foo/foo-6.tar.gz']


def test_pypi_source_default_srcname():
    urls = rpm_eval('%pypi_source',
                    name='python-foo', srcname='foo', version='6')
    assert urls == ['https://files.pythonhosted.org/packages/source/f/foo/foo-6.tar.gz']


def test_pypi_source_default_pypi_name():
    urls = rpm_eval('%pypi_source',
                    name='python-foo', pypi_name='foo', version='6')
    assert urls == ['https://files.pythonhosted.org/packages/source/f/foo/foo-6.tar.gz']


def test_pypi_source_default_name_uppercase():
    urls = rpm_eval('%pypi_source',
                    name='Foo', version='6')
    assert urls == ['https://files.pythonhosted.org/packages/source/F/Foo/Foo-6.tar.gz']


def test_pypi_source_provided_name():
    urls = rpm_eval('%pypi_source foo',
                    name='python-bar', pypi_name='bar', version='6')
    assert urls == ['https://files.pythonhosted.org/packages/source/f/foo/foo-6.tar.gz']


def test_pypi_source_provided_name_version():
    urls = rpm_eval('%pypi_source foo 6',
                    name='python-bar', pypi_name='bar', version='3')
    assert urls == ['https://files.pythonhosted.org/packages/source/f/foo/foo-6.tar.gz']


def test_pypi_source_provided_name_version_ext():
    url = rpm_eval('%pypi_source foo 6 zip',
                   name='python-bar', pypi_name='bar', version='3')
    assert url == ['https://files.pythonhosted.org/packages/source/f/foo/foo-6.zip']


def test_pypi_source_prerelease():
    urls = rpm_eval('%pypi_source',
                    name='python-foo', pypi_name='foo', version='6~b2')
    assert urls == ['https://files.pythonhosted.org/packages/source/f/foo/foo-6b2.tar.gz']


def test_pypi_source_explicit_tilde():
    urls = rpm_eval('%pypi_source foo 6~6',
                    name='python-foo', pypi_name='foo', version='6')
    assert urls == ['https://files.pythonhosted.org/packages/source/f/foo/foo-6~6.tar.gz']


def test_py3_shebang_fix():
    cmd = rpm_eval('%py3_shebang_fix arg1 arg2 arg3')[-1].strip()
    assert cmd == '/usr/bin/python3 -B /usr/lib/rpm/redhat/pathfix.py -pni /usr/bin/python3 $shebang_flags arg1 arg2 arg3'


def test_py3_shebang_fix_default_shebang_flags():
    lines = rpm_eval('%py3_shebang_fix arg1 arg2')
    lines[-1] = 'echo $shebang_flags'
    assert shell_stdout('\n'.join(lines)) == f'-kas{safe_path_flag(X_Y)}'


def test_py3_shebang_fix_custom_shebang_flags():
    lines = rpm_eval('%py3_shebang_fix arg1 arg2', py3_shebang_flags='Es')
    lines[-1] = 'echo $shebang_flags'
    assert shell_stdout('\n'.join(lines)) == '-kaEs'


@pytest.mark.parametrize('_py3_shebang_s', [None, '%{nil}'])
def test_py3_shebang_fix_undefined_py3_shebang_s(_py3_shebang_s):
    lines = rpm_eval('%py3_shebang_fix arg1 arg2', _py3_shebang_s=_py3_shebang_s)
    lines[-1] = 'echo $shebang_flags'
    expected = f'-ka{safe_path_flag(X_Y)}' if safe_path_flag(X_Y) else '-k'
    assert shell_stdout('\n'.join(lines)) == expected


@pytest.mark.parametrize('_py3_shebang_P', [None, '%{nil}'])
def test_py3_shebang_fix_undefined_py3_shebang_P(_py3_shebang_P):
    lines = rpm_eval('%py3_shebang_fix arg1 arg2', _py3_shebang_P=_py3_shebang_P)
    lines[-1] = 'echo $shebang_flags'
    assert shell_stdout('\n'.join(lines)) == '-kas'


@pytest.mark.parametrize('_py3_shebang_s', [None, '%{nil}'])
@pytest.mark.parametrize('_py3_shebang_P', [None, '%{nil}'])
def test_py3_shebang_fix_undefined_py3_shebang_sP(_py3_shebang_s, _py3_shebang_P):
    lines = rpm_eval('%py3_shebang_fix arg1 arg2',
                     _py3_shebang_s=_py3_shebang_s,
                     _py3_shebang_P=_py3_shebang_P)
    lines[-1] = 'echo $shebang_flags'
    assert shell_stdout('\n'.join(lines)) == '-k'


@pytest.mark.parametrize('flags', [None, '%{nil}'])
def test_py3_shebang_fix_no_shebang_flags(flags):
    lines = rpm_eval('%py3_shebang_fix arg1 arg2', py3_shebang_flags=flags)
    lines[-1] = 'echo $shebang_flags'
    assert shell_stdout('\n'.join(lines)) == '-k'


def test_py_shebang_fix_custom_python():
    cmd = rpm_eval('%py_shebang_fix arg1 arg2 arg3', __python='/usr/bin/pypy')[-1].strip()
    assert cmd == '/usr/bin/pypy -B /usr/lib/rpm/redhat/pathfix.py -pni /usr/bin/pypy $shebang_flags arg1 arg2 arg3'


def test_pycached_in_sitelib():
    lines = rpm_eval('%pycached %{python3_sitelib}/foo*.py')
    assert lines == [
        f'/usr/lib/python{X_Y}/site-packages/foo*.py',
        f'/usr/lib/python{X_Y}/site-packages/__pycache__/foo*.cpython-{XY}{{,.opt-?}}.pyc'
    ]


def test_pycached_in_sitearch(lib):
    lines = rpm_eval('%pycached %{python3_sitearch}/foo*.py')
    assert lines == [
        f'/usr/{lib}/python{X_Y}/site-packages/foo*.py',
        f'/usr/{lib}/python{X_Y}/site-packages/__pycache__/foo*.cpython-{XY}{{,.opt-?}}.pyc'
    ]


# this test does not require alternate Pythons to be installed
@pytest.mark.parametrize('version', ['3.6', '3.7', '3.12'])
def test_pycached_with_alternate_version(version):
    version_nodot = version.replace('.', '')
    lines = rpm_eval(f'%pycached /usr/lib/python{version}/site-packages/foo*.py')
    assert lines == [
        f'/usr/lib/python{version}/site-packages/foo*.py',
        f'/usr/lib/python{version}/site-packages/__pycache__/foo*.cpython-{version_nodot}{{,.opt-?}}.pyc'
    ]


def test_pycached_in_custom_dir():
    lines = rpm_eval('%pycached /bar/foo*.py')
    assert lines == [
        '/bar/foo*.py',
        '/bar/__pycache__/foo*.cpython-3*{,.opt-?}.pyc'
    ]


def test_pycached_with_exclude():
    lines = rpm_eval('%pycached %exclude %{python3_sitelib}/foo*.py')
    assert lines == [
        f'%exclude /usr/lib/python{X_Y}/site-packages/foo*.py',
        f'%exclude /usr/lib/python{X_Y}/site-packages/__pycache__/foo*.cpython-{XY}{{,.opt-?}}.pyc'
    ]


def test_pycached_fails_with_extension_glob():
    lines = rpm_eval('%pycached %{python3_sitelib}/foo.py*', fails=True)
    assert lines[0] == 'error: %pycached can only be used with paths explicitly ending with .py'


def test_python_extras_subpkg_i():
    lines = rpm_eval('%python_extras_subpkg -n python3-setuptools_scm -i %{python3_sitelib}/*.egg-info toml yaml',
                     version='6', release='7')
    expected = textwrap.dedent(f"""
        %package -n python3-setuptools_scm+toml
        Summary: Metapackage for python3-setuptools_scm: toml extras
        Requires: python3-setuptools_scm = 6-7
        %description -n python3-setuptools_scm+toml
        This is a metapackage bringing in toml extras requires for
        python3-setuptools_scm.
        It makes sure the dependencies are installed.

        %files -n python3-setuptools_scm+toml
        %ghost %dir /usr/lib/python{X_Y}/site-packages/*.egg-info

        %package -n python3-setuptools_scm+yaml
        Summary: Metapackage for python3-setuptools_scm: yaml extras
        Requires: python3-setuptools_scm = 6-7
        %description -n python3-setuptools_scm+yaml
        This is a metapackage bringing in yaml extras requires for
        python3-setuptools_scm.
        It makes sure the dependencies are installed.

        %files -n python3-setuptools_scm+yaml
        %ghost %dir /usr/lib/python{X_Y}/site-packages/*.egg-info
        """).lstrip().splitlines()
    assert lines == expected


def test_python_extras_subpkg_f():
    lines = rpm_eval('%python_extras_subpkg -n python3-setuptools_scm -f ghost_filelist toml yaml',
                     version='6', release='7')
    expected = textwrap.dedent(f"""
        %package -n python3-setuptools_scm+toml
        Summary: Metapackage for python3-setuptools_scm: toml extras
        Requires: python3-setuptools_scm = 6-7
        %description -n python3-setuptools_scm+toml
        This is a metapackage bringing in toml extras requires for
        python3-setuptools_scm.
        It makes sure the dependencies are installed.

        %files -n python3-setuptools_scm+toml -f ghost_filelist

        %package -n python3-setuptools_scm+yaml
        Summary: Metapackage for python3-setuptools_scm: yaml extras
        Requires: python3-setuptools_scm = 6-7
        %description -n python3-setuptools_scm+yaml
        This is a metapackage bringing in yaml extras requires for
        python3-setuptools_scm.
        It makes sure the dependencies are installed.

        %files -n python3-setuptools_scm+yaml -f ghost_filelist
        """).lstrip().splitlines()
    assert lines == expected


def test_python_extras_subpkg_F():
    lines = rpm_eval('%python_extras_subpkg -n python3-setuptools_scm -F toml yaml',
                     version='6', release='7')
    expected = textwrap.dedent(f"""
        %package -n python3-setuptools_scm+toml
        Summary: Metapackage for python3-setuptools_scm: toml extras
        Requires: python3-setuptools_scm = 6-7
        %description -n python3-setuptools_scm+toml
        This is a metapackage bringing in toml extras requires for
        python3-setuptools_scm.
        It makes sure the dependencies are installed.



        %package -n python3-setuptools_scm+yaml
        Summary: Metapackage for python3-setuptools_scm: yaml extras
        Requires: python3-setuptools_scm = 6-7
        %description -n python3-setuptools_scm+yaml
        This is a metapackage bringing in yaml extras requires for
        python3-setuptools_scm.
        It makes sure the dependencies are installed.
        """).lstrip().splitlines()
    assert lines == expected


def test_python_extras_subpkg_a():
    lines = rpm_eval('%python_extras_subpkg -n python3-setuptools_scm -a -F toml',
                     version='6', release='7')
    expected = textwrap.dedent(f"""
        %package -n python3-setuptools_scm+toml
        Summary: Metapackage for python3-setuptools_scm: toml extras
        Requires: python3-setuptools_scm = 6-7
        BuildArch: noarch
        %description -n python3-setuptools_scm+toml
        This is a metapackage bringing in toml extras requires for
        python3-setuptools_scm.
        It makes sure the dependencies are installed.
        """).lstrip().splitlines()
    assert lines == expected


def test_python_extras_subpkg_A():
    lines = rpm_eval('%python_extras_subpkg -n python3-setuptools_scm -A -F toml',
                     version='6', release='7')
    expected = textwrap.dedent(f"""
        %package -n python3-setuptools_scm+toml
        Summary: Metapackage for python3-setuptools_scm: toml extras
        Requires: python3-setuptools_scm = 6-7
        %description -n python3-setuptools_scm+toml
        This is a metapackage bringing in toml extras requires for
        python3-setuptools_scm.
        It makes sure the dependencies are installed.
        """).lstrip().splitlines()
    assert lines == expected


def test_python_extras_subpkg_aA():
    lines = rpm_eval('%python_extras_subpkg -n python3-setuptools_scm -a -A -F toml',
                     version='6', release='7', fails=True)
    assert lines[0] == ('error: %python_extras_subpkg: simultaneous -a '
                        '(insert BuildArch: noarch) and -A (do not insert '
                        'BuildArch: noarch (default)) options are not possible')


def test_python_extras_subpkg_v():
    lines = rpm_eval('%python_extras_subpkg -n python3-setuptools_scm -A -v 1.2.3 -F toml',
                     version='6', release='7')
    expected = textwrap.dedent(f"""
        %package -n python3-setuptools_scm+toml
        Summary: Metapackage for python3-setuptools_scm: toml extras
        Requires: python3-setuptools_scm = 1.2.3
        %description -n python3-setuptools_scm+toml
        This is a metapackage bringing in toml extras requires for
        python3-setuptools_scm.
        It makes sure the dependencies are installed.
        """).lstrip().splitlines()
    assert lines == expected


def test_python_extras_subpkg_underscores():
    lines = rpm_eval('%python_extras_subpkg -n python3-webscrapbook -F adhoc_ssl',
                     version='0.33.3', release='1.fc33')
    expected = textwrap.dedent(f"""
        %package -n python3-webscrapbook+adhoc_ssl
        Summary: Metapackage for python3-webscrapbook: adhoc_ssl extras
        Requires: python3-webscrapbook = 0.33.3-1.fc33
        %description -n python3-webscrapbook+adhoc_ssl
        This is a metapackage bringing in adhoc_ssl extras requires for
        python3-webscrapbook.
        It makes sure the dependencies are installed.
        """).lstrip().splitlines()
    assert lines == expected


@pytest.mark.parametrize('sep', [pytest.param(('', ' ', ' ', ''), id='spaces'),
                                 pytest.param(('', ',', ',', ''), id='commas'),
                                 pytest.param(('', ',', ',', ','), id='commas-trailing'),
                                 pytest.param((',', ',', ',', ''), id='commas-leading'),
                                 pytest.param((',', ',', ',', ','), id='commas-trailing-leading'),
                                 pytest.param(('', ',', ' ', ''), id='mixture'),
                                 pytest.param(('  ', '   ', '\t\t, ', '\t'), id='chaotic-good'),
                                 pytest.param(('', '\t ,, \t\r ', ',,\t  , ', ',,'), id='chaotic-evil')])
def test_python_extras_subpkg_arg_separators(sep):
    lines = rpm_eval('%python_extras_subpkg -n python3-hypothesis -F {}cli{}ghostwriter{}pytz{}'.format(*sep),
                     version='6.6.0', release='1.fc35')
    expected = textwrap.dedent(f"""
        %package -n python3-hypothesis+cli
        Summary: Metapackage for python3-hypothesis: cli extras
        Requires: python3-hypothesis = 6.6.0-1.fc35
        %description -n python3-hypothesis+cli
        This is a metapackage bringing in cli extras requires for python3-hypothesis.
        It makes sure the dependencies are installed.



        %package -n python3-hypothesis+ghostwriter
        Summary: Metapackage for python3-hypothesis: ghostwriter extras
        Requires: python3-hypothesis = 6.6.0-1.fc35
        %description -n python3-hypothesis+ghostwriter
        This is a metapackage bringing in ghostwriter extras requires for
        python3-hypothesis.
        It makes sure the dependencies are installed.



        %package -n python3-hypothesis+pytz
        Summary: Metapackage for python3-hypothesis: pytz extras
        Requires: python3-hypothesis = 6.6.0-1.fc35
        %description -n python3-hypothesis+pytz
        This is a metapackage bringing in pytz extras requires for python3-hypothesis.
        It makes sure the dependencies are installed.
        """).lstrip().splitlines()
    assert lines == expected


@pytest.mark.parametrize('basename_len', [1, 10, 30, 45, 78])
@pytest.mark.parametrize('extra_len', [1, 13, 28, 52, 78])
def test_python_extras_subpkg_description_wrapping(basename_len, extra_len):
    basename = 'x' * basename_len
    extra = 'y' * extra_len
    lines = rpm_eval(f'%python_extras_subpkg -n {basename} -F {extra}',
                     version='6', release='7')
    for idx, line in enumerate(lines):
        if line.startswith('%description'):
            start = idx + 1
    lines = lines[start:]
    assert all(len(l) < 80 for l in lines)
    assert len(lines) < 6
    if len(" ".join(lines[:-1])) < 80:
        assert len(lines) == 2
    expected_singleline = (f"This is a metapackage bringing in {extra} extras "
                           f"requires for {basename}. "
                           f"It makes sure the dependencies are installed.")
    description_singleline = " ".join(lines)
    assert description_singleline == expected_singleline


unversioned_macros = pytest.mark.parametrize('macro', [
    '%__python',
    '%python',
    '%python_version',
    '%python_version_nodots',
    '%python_sitelib',
    '%python_sitearch',
    '%python_platform',
    '%python_platform_triplet',
    '%python_ext_suffix',
    '%python_cache_tag',
    '%py_shebang_fix',
    '%py_build',
    '%py_build_wheel',
    '%py_install',
    '%py_install_wheel',
    '%py_check_import',
    '%py_test_envvars',
])


@unversioned_macros
def test_unversioned_python_errors(macro):
    lines = rpm_eval(macro, fails=True)
    # strip the deprecation message
    if 'deprecated' in lines[0]:
        lines = lines[1:]
    assert lines[0] == (
        'error: attempt to use unversioned python, '
        'define %__python to /usr/bin/python2 or /usr/bin/python3 explicitly'
    )
    # when the macros are %global, the error is longer
    # we deliberately allow this extra line to be optional
    if len(lines) > 1 and "error: lua script failed" not in lines[1]:
        # the failed macro is not unnecessarily our tested macro
        pattern = r'error: Macro %\S+ failed to expand'
        assert re.match(pattern, lines[1])
    # but there should be no more lines
    assert len(lines) < 3


@unversioned_macros
def test_unversioned_python_works_when_defined(macro):
    macro3 = macro.replace('python', 'python3').replace('py_', 'py3_')
    unverisoned = rpm_eval(macro, __python='/usr/bin/python3')
    expected = [l.replace(macro3, macro) for l in rpm_eval(macro3)]
    assert unverisoned == expected


# we could rework the test for multiple architectures, but the Fedora CI currently only runs on x86_64
x86_64_only = pytest.mark.skipif(platform.machine() != "x86_64", reason="works on x86_64 only")


@x86_64_only
def test_platform_triplet():
    assert rpm_eval("%python3_platform_triplet") == ["x86_64-linux-gnu"]


@x86_64_only
def test_ext_suffix():
    assert rpm_eval("%python3_ext_suffix") == [f".cpython-{XY}-x86_64-linux-gnu.so"]


def test_cache_tag():
    assert rpm_eval("%python3_cache_tag") == [f"cpython-{XY}"]


def test_cache_tag_alternate_python(alt_x_y, alt_xy):
    assert rpm_eval("%python_cache_tag", __python=f"/usr/bin/python{alt_x_y}") == [f"cpython-{alt_xy}"]


def test_cache_tag_alternate_python3(alt_x_y, alt_xy):
    assert rpm_eval("%python3_cache_tag", __python3=f"/usr/bin/python{alt_x_y}") == [f"cpython-{alt_xy}"]


def test_python_sitelib_value_python3():
    macro = '%python_sitelib'
    assert rpm_eval(macro, __python='%__python3') == [f'/usr/lib/python{X_Y}/site-packages']


def test_python_sitelib_value_alternate_python(alt_x_y):
    macro = '%python_sitelib'
    assert rpm_eval(macro, __python=f'/usr/bin/python{alt_x_y}') == [f'/usr/lib/python{alt_x_y}/site-packages']


def test_python3_sitelib_value_default():
    macro = '%python3_sitelib'
    assert rpm_eval(macro) == [f'/usr/lib/python{X_Y}/site-packages']


def test_python3_sitelib_value_alternate_python(alt_x_y):
    macro = '%python3_sitelib'
    assert (rpm_eval(macro, __python3=f'/usr/bin/python{alt_x_y}') ==
            rpm_eval(macro, python3_pkgversion=alt_x_y) ==
            [f'/usr/lib/python{alt_x_y}/site-packages'])


def test_python3_sitelib_value_alternate_prefix():
    macro = '%python3_sitelib'
    assert rpm_eval(macro, _prefix='/app') == [f'/app/lib/python{X_Y}/site-packages']


def test_python_sitearch_value_python3(lib):
    macro = '%python_sitearch'
    assert rpm_eval(macro, __python='%__python3') == [f'/usr/{lib}/python{X_Y}/site-packages']


def test_python_sitearch_value_alternate_python(lib, alt_x_y):
    macro = '%python_sitearch'
    assert rpm_eval(macro, __python=f'/usr/bin/python{alt_x_y}') == [f'/usr/{lib}/python{alt_x_y}/site-packages']


def test_python3_sitearch_value_default(lib):
    macro = '%python3_sitearch'
    assert rpm_eval(macro) == [f'/usr/{lib}/python{X_Y}/site-packages']


def test_python3_sitearch_value_alternate_python(lib, alt_x_y):
    macro = '%python3_sitearch'
    assert (rpm_eval(macro, __python3=f'/usr/bin/python{alt_x_y}') ==
            rpm_eval(macro, python3_pkgversion=alt_x_y) ==
            [f'/usr/{lib}/python{alt_x_y}/site-packages'])


def test_python3_sitearch_value_alternate_prefix(lib):
    macro = '%python3_sitearch'
    assert rpm_eval(macro, _prefix='/app') == [f'/app/{lib}/python{X_Y}/site-packages']


@pytest.mark.parametrize(
    'args, expected_args',
    [
        ('six', 'six'),
        ('-f foo.txt', '-f foo.txt'),
        ('-t -f foo.txt six, seven', '-t -f foo.txt six, seven'),
        ('-e "foo*" -f foo.txt six, seven', '-e "foo*" -f foo.txt six, seven'),
        ('six.quarter six.half,, SIX', 'six.quarter six.half,, SIX'),
        ('-f foo.txt six\nsix.half\nSIX', '-f foo.txt six six.half SIX'),
        ('six \\ -e six.half', 'six -e six.half'),
    ]
)
@pytest.mark.parametrize('__python3',
                         [None,
                          f'/usr/bin/python{X_Y}',
                          '/usr/bin/pythonX.Y'])
def test_py3_check_import(args, expected_args, __python3, lib):
    x_y = X_Y
    macros = {
        'buildroot': 'BUILDROOT',
        '_rpmconfigdir': 'RPMCONFIGDIR',
    }
    if __python3 is not None:
        if 'X.Y' in __python3:
            __python3 = __python3.replace('X.Y', get_alt_x_y())
        macros['__python3'] = __python3
        # If the __python3 command has version at the end, parse it and expect it.
        # Note that the command is used to determine %python3_sitelib and %python3_sitearch,
        # so we only test known CPython schemes here and not PyPy for simplicity.
        if (match := re.match(r'.+python(\d+\.\d+)$', __python3)):
            x_y = match.group(1)

    invocation = '%{py3_check_import ' + args +'}'
    lines = rpm_eval(invocation, **macros)

    # An equality check is a bit inflexible here,
    # every time we change the macro we need to change this test.
    # However actually executing it and verifying the result is much harder :/
    # At least, let's make the lines saner to check:
    lines = [line.rstrip('\\').strip() for line in lines]
    expected = textwrap.dedent(fr"""
        PATH="BUILDROOT/usr/bin:$PATH"
        PYTHONPATH="${{PYTHONPATH:-BUILDROOT/usr/{lib}/python{x_y}/site-packages:BUILDROOT/usr/lib/python{x_y}/site-packages}}"
        _PYTHONSITE="BUILDROOT/usr/{lib}/python{x_y}/site-packages:BUILDROOT/usr/lib/python{x_y}/site-packages"
        PYTHONDONTWRITEBYTECODE=1
        {__python3 or '/usr/bin/python3'} -s{safe_path_flag(x_y)} RPMCONFIGDIR/redhat/import_all_modules.py {expected_args}
        """)
    assert lines == expected.splitlines()


@pytest.mark.parametrize(
    'shebang_flags_value, expected_shebang_flags',
    [
        ('sP', '-sP'),
        ('s', '-s'),
        ('%{nil}', ''),
        (None, ''),
        ('Es', '-Es'),
    ]
)
def test_py3_check_import_respects_shebang_flags(shebang_flags_value, expected_shebang_flags, lib):
    macros = {
        '_rpmconfigdir': 'RPMCONFIGDIR',
        '__python3': '/usr/bin/python3',
        'py3_shebang_flags': shebang_flags_value,
    }
    lines = rpm_eval('%py3_check_import sys', **macros)
    # Compare the last line of the command, that's where lua part is evaluated
    expected = f'/usr/bin/python3 {expected_shebang_flags} RPMCONFIGDIR/redhat/import_all_modules.py sys'
    assert  lines[-1].strip() == expected


def test_multi_python(alt_x_y):
    """
    Ensure memoized %python_version works when switching %__python back
    and forth.
    """
    versions = ['3', alt_x_y, X_Y, '3']
    evals = []
    for version in versions:
        evals.extend((f'%global __python /usr/bin/python{version}', '%python_version'))
    lines = rpm_eval(evals)
    lines = [l for l in  lines if l]  # strip empty lines generated by %global
    assert lines == [X_Y, alt_x_y, X_Y, X_Y]


def test_multi_python3(alt_x_y):
    """
    Ensure memoized %python3_version works when switching %__python3 back
    and forth.
    """
    versions = ['3', alt_x_y, X_Y, '3']
    evals = []
    for version in versions:
        evals.extend((f'%global __python3 /usr/bin/python{version}', '%python3_version'))
    lines = rpm_eval(evals)
    lines = [l for l in  lines if l]  # strip empty lines generated by %global
    assert lines == [X_Y, alt_x_y, X_Y, X_Y]


@pytest.mark.parametrize('macro', [
    '%py3_build',
    '%py3_build_wheel',
    '%py3_install',
])
def test_deprecation(macro):
    lines = rpm_eval(macro)
    assert "is deprecated" in lines[0]
    assert f"{macro} " in lines[0]


def test_multiple_deprecation():
    source = '%{py3_build}' * 10 + '%{py3_build_wheel}' * 10 + '%{py3_install}' * 10 + '%{py3_build}'
    lines = rpm_eval(source)

    assert "is deprecated" in lines[0]
    assert "%py3_build " in lines[0]

    assert "is deprecated" in lines[1]
    assert "%py3_build_wheel " in lines[1]

    assert "is deprecated" in lines[2]
    assert "%py3_install " in lines[2]

    assert "is deprecated" not in '\n'.join(lines[3:])
