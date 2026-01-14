Name:           gpgverify-test-expired
Version:        1
Release:        1
Summary:        gpgverify testcase, expired key
License:        FSFAP
Source1:        key.gpg
Source2:        dummy.tar.gz
Source3:        dummy.tar.gz.sig
BuildRequires:  gpgverify

%description
This tests signature verification with an expired key. Rebuilds shall not fail
just because the clock has ticked past an arbitrary date.

%prep
%{gpgverify} --keyring='%{SOURCE1}' --data='%{SOURCE2}' --signature='%{SOURCE3}'
echo 'Execution of prep continues.'

%changelog
* Fri Jan 10 2025 Björn Persson <Bjorn@Rombobjörn.se> - 1-1
- created
