Name:           escape_paths
Version:        0.1
Release:        0
Summary:        ...
License:        MIT
BuildArch:      noarch

%description
This spec file verifies that escaping percentage signs in paths is possible via
exactly 8 (or 2) percentage signs in a filelist and directly in the %%files section.
It also verifies other path escaping assumptions on RPM 4.19+.
It serves as a regression test for pyproject_save_files:escape_rpm_path().
When this breaks, the function needs to be adapted.


%prep
cat > pyproject.toml << EOF
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
EOF

cat > setup.cfg << EOF
[metadata]
name = escape_paths
version = 0.1
[options]
packages =
    escape_paths
[options.package_data]
escape_paths =
    *
EOF

mkdir -p escape_paths
touch escape_paths/__init__.py
# the paths on disk will have 1 percentage sign if we type 2 in the spec
# we use the word 'version' after the sign, as that is a known existing macro
touch 'escape_paths/one%%version'
%if v"0%{?rpmversion}" >= v"4.18.90"
touch 'escape_paths/path with spaces'
touch 'escape_paths/path with spaces and "quotes'
touch 'escape_paths/path_with_?*[!globs]!'
touch 'escape_paths/path_with_\backslash'
touch 'escape_paths/path_with_{curly,brackets}'
touch 'escape_paths/path with spaces and ?*[!globs]! and \backslash'
%endif


%generate_buildrequires
%pyproject_buildrequires


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files -L escape_paths
touch '%{buildroot}/two%%version'
%if v"0%{?rpmversion}" >= v"4.18.90"
touch '%{buildroot}/another_path with spaces'
touch '%{buildroot}/another_path with spaces and "quotes'
touch '%{buildroot}/another_path_with_?*[!globs]!'
touch '%{buildroot}/another_path_with_\backslash'
touch '%{buildroot}/another_path_with_{curly,brackets}'
touch '%{buildroot}/another_path with spaces and ?*[!globs]! and \backslash'
%endif


%check
grep '/escape_paths/one' %{pyproject_files}



%files -f %{pyproject_files}
%if v"0%{?rpmversion}" >= v"4.18.90"
/two%%version
/another_path\ with\ spaces
/another_path\ with\ spaces\ and\ \"quotes
/another_path_with_\?\*\[\!globs\]\!
/another_path_with_\\backslash
/another_path_with_\{curly,brackets\}
/another_path\ with\ spaces\ and\ \?\*\[\!globs\]\!\ and\ \\backslash
%else
/two%%%%%%%%version
%endif
