Name:           gpgverify-test-bad-usage
Version:        1
Release:        1
Summary:        gpgverify testcase, insecure clearsigned usage
License:        FSFAP
Source1:        key.gpg
Source2:        dummy.txt.asc
BuildRequires:  gpgverify

%description
Building this package shall fail because it tries to verify a clearsigned text
file in an insecure way. The --output parameter is missing.

%prep
%{gpgverify} --keyring='%{SOURCE1}' --data='%{SOURCE2}'
echo 'Execution of prep continues.'
# A naive packager would now pass dummy.txt.asc directly to some other program,
# thinking it has been verified, unaware that it contains unsigned parts.

%changelog
* Sat Jan 11 2025 Björn Persson <Bjorn@Rombobjörn.se> - 1-1
- created
