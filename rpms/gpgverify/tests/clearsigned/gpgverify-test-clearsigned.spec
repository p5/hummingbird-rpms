Name:           gpgverify-test-clearsigned
Version:        1
Release:        1
Summary:        gpgverify testcase, clearsigned text file
License:        FSFAP
Source1:        key.gpg
Source2:        dummy.txt.asc
BuildRequires:  gpgverify

%description
This tests verifying a clearsigned text file. The clearsigned file includes
unsigned parts, which must be excluded from the verified text.

%prep
%{gpgverify} --keyring='%{SOURCE1}' --data='%{SOURCE2}' --output=verified.txt
echo 'Execution of prep continues.'
# The verified text would now be processed by some other program, such as
# sha512sum. Here it's instead output for inspection by test-rpmbuild.
cat verified.txt

%changelog
* Sat Jan 11 2025 Björn Persson <Bjorn@Rombobjörn.se> - 1-1
- created
