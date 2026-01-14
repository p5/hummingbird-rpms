Name:           gpgverify-test-stdin
Version:        1
Release:        1
Summary:        gpgverify testcase, standard input
License:        FSFAP
Source1:        key.gpg
Source2:        dummy.tar.gz
Source3:        dummy.tar.gz.sig
BuildRequires:  gpgverify

%description
This tests gpgverify in a pipeline where the signed data come through the
standard input stream.

%prep
cat '%{SOURCE2}' | %{gpgverify} --keyring='%{SOURCE1}' --data=- --signature='%{SOURCE3}'
echo 'Execution of prep continues.'

%changelog
* Fri Jan 10 2025 Björn Persson <Bjorn@Rombobjörn.se> - 1-1
- created
