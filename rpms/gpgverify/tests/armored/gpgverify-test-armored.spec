Name:           gpgverify-test-armored
Version:        1
Release:        1
Summary:        gpgverify testcase, ASCII-armored files
License:        FSFAP
Source1:        key.asc
Source2:        dummy.tar.gz
Source3:        dummy.tar.gz.asc
BuildRequires:  gpgverify

%description
This tests signature verification where the key and the signature are ASCII-
armored.

%prep
%{gpgverify} --keyring='%{SOURCE1}' --data='%{SOURCE2}' --signature='%{SOURCE3}'
echo 'Execution of prep continues.'

%changelog
* Fri Jan 10 2025 Björn Persson <Bjorn@Rombobjörn.se> - 1-1
- created
