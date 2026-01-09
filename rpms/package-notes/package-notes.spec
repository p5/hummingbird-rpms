Name:           package-notes
Version:        0.5
Release:        %autorelease
Summary:        Generate LDFLAGS to insert .note.package section
License:        0BSD
URL:            https://github.com/systemd/package-notes

Source0:        redhat-package-notes.in
Source1:        macros.package-notes-srpm

BuildArch:      noarch

%description
This package provides a generator of linker scripts that insert a section with
an ELF note with a JSON payload that describes the package the binary was built
for.

%package srpm-macros
Summary:        %{summary}
Obsoletes:      package-notes < 0.5
# Those are minimum versions that implement --package-metadata
Conflicts:      binutils < 2.37-34
Conflicts:      binutils-gold < 2.37-34
Conflicts:      mold < 1.3.0
Conflicts:      lld < 14.0.5-4

%description srpm-macros
RPM macros to insert a section with an ELF note with a JSON payload that
describes the package the binary was built for via a compiler spec file.

%prep
# nothing to do

%build
sed "s|@OSCPE@|$(cat /usr/lib/system-release-cpe)|" %{SOURCE0} >redhat-package-notes

%install
install -Dt %{buildroot}%{_rpmconfigdir}/redhat/ redhat-package-notes
install -m0644 -Dt %{buildroot}%{_rpmmacrodir}/ %{SOURCE1}

%files srpm-macros
%{_rpmconfigdir}/redhat/redhat-package-notes
%{_rpmmacrodir}/macros.package-notes-srpm

%changelog
%autochangelog
