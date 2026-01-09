%bcond_with ld_lld
%bcond_with clang

%if %{with ld_lld}
%global extra_ldflags -fuse-ld=lld
%global _package_note_linker lld
%endif
%if %{with clang}
%global toolchain clang
%endif

Name: test
Version: 1
Release: 1
Summary: Test package for checking package notes
License: MIT

%if %{with clang}
BuildRequires: clang
%else
BuildRequires: gcc
%endif
# For %check
BuildRequires: binutils
BuildRequires: jq
%if %{with ld_lld}
BuildRequires: lld
%endif

%description
Test package for checking package notes

%build
echo 'int main(int argc, char **argv) { return 0; }' | %{build_cc} ${CFLAGS} -x c -c - -o main.o
%{build_cc} -Werror ${LDFLAGS} %{?extra_ldflags} main.o -o main

# Package notes not supported with clang, so the the build succeeding is enough.
%if %{without clang}
%check
# avoid any attempt to access the network by readelf
export DEBUGINFOD_URLS=

readelf --notes ./main | sed -r -n 's/.*Packaging Metadata: (.*)/\1/p' | tee package-note.text

test "`cat package-note.text | jq -r '[.type,.name,.version,.architecture]|join(" ")'`" == "rpm %{name} %{version}-%{release} %{_arch}"
%endif

%changelog
* Sat Aug  6 2022 Jane Doe <jane@example.org> - 1-1
- Dummy
