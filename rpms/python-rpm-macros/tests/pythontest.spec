%global basedir /opt/test/byte_compilation

# We have 3 different ways of bytecompiling: for 3.9+, 3.4-3.8, and 2.7
# Test with a representative of each, except 2.7 which we no longer have
%global python36_sitelib /usr/lib/python3.6/site-packages

Name:           pythontest
Version:        0
Release:        0%{?dist}
Summary:        ...
License:        MIT
BuildRequires:  python3-devel
BuildRequires:  python3.6

%description
...

%install
mkdir -p %{buildroot}%{basedir}/directory/to/test/recursion

echo "print()" > %{buildroot}%{basedir}/file.py
echo "print()" > %{buildroot}%{basedir}/directory/to/test/recursion/file_in_dir.py

%py_byte_compile %{python3} %{buildroot}%{basedir}/file.py
%py_byte_compile %{python3} %{buildroot}%{basedir}/directory

# Files in sitelib are compiled automatically by brp-python-bytecompile
mkdir -p %{buildroot}%{python3_sitelib}/directory/
echo "print()" > %{buildroot}%{python3_sitelib}/directory/file.py

mkdir -p %{buildroot}%{python36_sitelib}/directory/
echo "print()" > %{buildroot}%{python36_sitelib}/directory/file.py

%check
LOCATIONS="
    %{buildroot}%{basedir}
    %{buildroot}%{python3_sitelib}/directory/
    %{buildroot}%{python36_sitelib}/directory/
"

# Count .py and .pyc files
PY=$(find $LOCATIONS -name "*.py" | wc -l)
PYC=$(find $LOCATIONS -name "*.py[co]" | wc -l)

# We should have 4 .py files (3 for python3, one for 3.6)
test $PY -eq 4

# Every .py file should be byte-compiled to two .pyc files (optimization level 0 and 1)
# so we should have two times more .pyc files than .py files
test $(expr $PY \* 2) -eq $PYC

# In this case the .pyc files should be identical across omtimization levels
# (they don't use docstrings and assert staements)
# So they should be hardlinked; the number of distinct inodes should match the
# number of source files. (Or be smaller, if the dupe detection is done
# across all files.)

INODES=$(stat --format %i $(find $LOCATIONS -name "*.py[co]") | sort -u | wc -l)
test $PY -ge $INODES


%files
%pycached %{basedir}/file.py
%pycached %{basedir}/directory/to/test/recursion/file_in_dir.py
%pycached %{python3_sitelib}/directory/file.py
%pycached %{python36_sitelib}/directory/file.py


%changelog
* Thu Jan 01 2015 Fedora Packager <nobody@fedoraproject.org> - 0-0
- This changelog entry exists and is deliberately set in the past
