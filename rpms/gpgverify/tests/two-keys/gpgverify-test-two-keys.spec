Name:           gpgverify-test-two-keys
Version:        1
Release:        1
Summary:        gpgverify testcase, two separate keyrings
License:        FSFAP
Source1:        key-1.gpg
Source2:        key-2.gpg
Source3:        dummy.tar.gz
Source4:        dummy.tar.gz.sig
BuildRequires:  gpgverify

%description
This tests passing --keyring to gpgverify more than once.

%prep
%{gpgverify} --keyring='%{SOURCE1}' --keyring='%{SOURCE2}' --data='%{SOURCE3}' --signature='%{SOURCE4}'
echo 'Execution of prep continues.'

%changelog
* Sat Jan 11 2025 Björn Persson <Bjorn@Rombobjörn.se> - 1-1
- created
