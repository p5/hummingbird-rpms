Name:           gpgverify-test-invalid-parameter
Version:        1
Release:        1
Summary:        gpgverify testcase, invalid parameter
License:        FSFAP
Source1:        key.gpg
Source2:        dummy.tar.gz
Source3:        dummy.tar.gz.sig
BuildRequires:  gpgverify

%description
Building this package shall fail because "0" is invalid as a parameter to
gpgverify. This checks that gpgverify does not have the vulnerability that an
attacker tried to inject in this merge request:
https://src.fedoraproject.org/rpms/redhat-rpm-config/pull-request/84

%prep
%{gpgverify} --keyring='%{SOURCE1}' --data='%{SOURCE2}' --signature='%{SOURCE3}' 0
echo 'Execution of prep continues.'

%changelog
* Thu Jan 23 2025 Björn Persson <Bjorn@Rombobjörn.se> - 1-1
- created
