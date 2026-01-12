Name:           gpgverify-test-keybox
Version:        1
Release:        1
Summary:        gpgverify testcase, key in a keybox file
License:        FSFAP
Source1:        key.kbx
Source2:        dummy.tar.gz
Source3:        dummy.tar.gz.sig
BuildRequires:  gpgverify

%description
This tests signature verification with a key in the keybox format.

%prep
%{gpgverify} --keyring='%{SOURCE1}' --data='%{SOURCE2}' --signature='%{SOURCE3}'
echo 'Execution of prep continues.'

%changelog
* Sun Jan 12 2025 Björn Persson <Bjorn@Rombobjörn.se> - 1-1
- created
