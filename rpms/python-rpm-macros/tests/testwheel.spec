Name:           testwheel
Epoch:          42
Version:        1
Release:        0%{?dist}
Summary:        ...
License:        MIT
BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools >= 61
BuildRequires:  python3-pip

%description
This builds and installs a wheel which we can then use as a test for
%%python_wheel_inject_sbom.


%prep
cat > pyproject.toml << EOF
[project]
name = "testwheel"
version = "1"

[build-system]
requires = ["setuptools >= 61"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
include-package-data = true

[tool.setuptools.packages.find]
include = ["testwheel*"]
EOF
# create a secondary dist-info folder in the project
# we need to ensure this file is not altered
mkdir -p testwheel/_vendor/dependency-2.2.2.dist-info
touch testwheel/_vendor/dependency-2.2.2.dist-info/RECORD
echo 'recursive-include testwheel/_vendor *' > MANIFEST.in


%build
export PIP_CONFIG_FILE=/dev/null
%{python3} -m pip wheel . --no-build-isolation

# The macro should happily alter multiple wheels, let's make more
for i in {1..5}; do
  mkdir ${i}
  cp -a *.whl ${i}
done

# using relative paths should succeed
%python_wheel_inject_sbom {1..5}/*.whl

# repetitive use should bail out and fail (SBOM is already there)
%{python_wheel_inject_sbom {1..5}/*.whl} && exit 1 || true

# each wheel should already have it, all should fail individually as well
for i in {1..5}; do
  %{python_wheel_inject_sbom ${i}/*.whl} && exit 1 || true
done


%install
mkdir -p %{buildroot}%{python_wheel_dir}
cp -a *.whl %{buildroot}%{python_wheel_dir}

# using absolute paths should work
%python_wheel_inject_sbom %{buildroot}%{python_wheel_dir}/*.whl

# and fail when repeated
%{python_wheel_inject_sbom %{buildroot}%{python_wheel_dir}/*.whl} && exit 1 || true


%check
%define venvsite venv/lib/python%{python3_version}/site-packages
%{python3} -m venv venv
venv/bin/pip install --no-index --no-cache-dir %{buildroot}%{python_wheel_dir}/*.whl

test -f %{venvsite}/testwheel-1.dist-info/RECORD
test -f %{venvsite}/testwheel-1.dist-info/sboms/bom.json
grep '^testwheel-1.dist-info/sboms/bom.json,' %{venvsite}/testwheel-1.dist-info/RECORD
# a more specific grep. we don't care about CRLF line ends (pip uses those? without the sed the $ doesn't match line end)
sed 's/\r//g' %{venvsite}/testwheel-1.dist-info/RECORD | grep -E '^testwheel-1.dist-info/sboms/bom.json,sha256=[a-f0-9]{64},[0-9]+$'

test -f %{venvsite}/testwheel/_vendor/dependency-2.2.2.dist-info/RECORD
test -f %{venvsite}/testwheel/_vendor/dependency-2.2.2.dist-info/sboms/bom.json && exit 1 || true

# this deliberately uses a different mechanism than the macro
# if you are running this test on a different distro, adjust it
%define ns %{?fedora:fedora}%{?eln:fedora}%{?epel:epel}%{!?eln:%{!?epel:%{?rhel:redhat}}}

PYTHONOPTIMIZE=0 %{python3} -c "
import json
with open('%{venvsite}/testwheel-1.dist-info/sboms/bom.json') as fp:
    sbom = json.load(fp)
assert len(sbom['components']) == 1
assert sbom['components'][0]['type'] == 'library'
assert sbom['components'][0]['name'] == 'testwheel'
assert sbom['components'][0]['version'] == '1-0%{?dist}'
assert sbom['components'][0]['purl'] == 'pkg:rpm/%{ns}/testwheel@1-0%{?dist}?epoch=42&arch=src'
"

# replace the installation with the original unaltered wheel
venv/bin/pip install --force-reinstall --no-index --no-cache-dir *.whl
test -f %{venvsite}/testwheel-1.dist-info/RECORD
# no SBOM
test ! -e %{venvsite}/testwheel-1.dist-info/sboms/bom.json
grep '^testwheel-1.dist-info/sboms/bom.json,' %{venvsite}/testwheel-1.dist-info/RECORD  && exit 1 || true


%files
%{python_wheel_dir}/*.whl


%changelog
* Wed Aug 13 2025 Miro Hrončok <mhroncok@redhat.com> - 42:1-0
- A static changelog with a date, so we can clamp mtimes
