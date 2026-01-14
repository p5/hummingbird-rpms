Name:           gpgverify-test-unarmored
Version:        1
Release:        1
Summary:        gpgverify testcase, no ASCII armor
License:        FSFAP
Source1:        key.gpg
Source2:        dummy.tar.gz
Source3:        dummy.tar.gz.sig
BuildRequires:  gpgverify

%description
This tests the most basic signature verification. There is no ASCII armor or
other complications.

%prep
%{gpgverify} --keyring='%{SOURCE1}' --data='%{SOURCE2}' --signature='%{SOURCE3}'
echo 'Execution of prep continues.'

%changelog
* Fri Jan 10 2025 Björn Persson <Bjorn@Rombobjörn.se> - 1-1
- created
