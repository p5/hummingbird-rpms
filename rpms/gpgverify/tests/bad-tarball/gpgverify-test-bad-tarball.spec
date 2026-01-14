Name:           gpgverify-test-bad-tarball
Version:        1
Release:        1
Summary:        gpgverify testcase, bad tarball
License:        FSFAP
Source1:        key.gpg
Source2:        dummy.tar.gz
Source3:        dummy.tar.gz.sig
BuildRequires:  gpgverify

%description
Building this package shall fail because the tarball doesn't match the
signature.

%prep
%{gpgverify} --keyring='%{SOURCE1}' --data='%{SOURCE2}' --signature='%{SOURCE3}'
echo 'Execution of prep continues.'

%changelog
* Fri Jan 10 2025 Björn Persson <Bjorn@Rombobjörn.se> - 1-1
- created
