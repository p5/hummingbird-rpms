Name:                 python-pello
Version:              1.0.4
Release:              0%{?dist}
Summary:              Example Python library

License:              MIT-0
URL:                  https://github.com/fedora-python/Pello
Source:               %{url}/archive/v%{version}/Pello-%{version}.tar.gz

BuildArch:            noarch

# we use this specfile for various different tests, the bconds controls it
# a build --with options tests custom BuildOptions(generate_buildrequires)
%bcond options 0
# a build --with override_install has a custom %%install section
%bcond override_install 0

# unfortunately, the following is not even parsable on RPM < 4.20
%if v"0%{?rpmversion}" >= v"4.19.90"
BuildSystem:          pyproject
%if %{without override_install}
BuildOption(install): -l pello
%endif
%if %{with options}
BuildOption(generate_buildrequires): -t
%endif
%endif

%description
We use this specfile to test the declarative buildsystem.
On older RPM version the build succeeds but builds nothing.

Note that due to the "automagic" it's a bit challenging to actually assert
anything here. Manually inspecting the logs and results when doing changes
to the declarative buildsystem is still advised.


%package -n python3-pello
Summary:              %{summary}

%description -n python3-pello
...


%if %{with options} && v"0%{?rpmversion}" >= v"4.19.90"
%check -a
%tox
%endif


%if %{with override_install} && v"0%{?rpmversion}" >= v"4.19.90"
# to test a fix for https://github.com/rpm-software-management/rpm/issues/3890
%install
%pyproject_install
%pyproject_save_files -l pello
%endif


%if v"0%{?rpmversion}" >= v"4.19.90"
%files -n python3-pello -f %{pyproject_files}
%doc README.md
%{_bindir}/pello_greeting
%endif
