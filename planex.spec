%define name planex
%define version 0.6.0
%define release 1

Summary: RPM/deb build tool
Name: %{name}
Version: %{version}
Release: %{release}%{?dist}
URL: http://github.com/xenserver/planex
Source0: http://github.com/xenserver/planex/archive/v%{version}/%{name}-%{version}.tar.gz
License: LGPLv2.1
BuildArch: noarch
BuildRequires: python-setuptools
Requires: mock
Requires: rpm-build
Requires: createrepo
Requires: python-argparse
Requires: python-argcomplete
Requires: python-setuptools

%description
Planex is a tool for building RPMs and deb files. It manages interdependencies
and caching.

%prep
%setup -q

%build
%{__python} setup.py build

%install
%{__python} setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%files
%doc README.md
%doc LICENSE
%doc CHANGES
%{_bindir}/planex-cache
%{_bindir}/planex-clone
%{_bindir}/planex-configure
%{_bindir}/planex-fetch
%{_bindir}/planex-makedeb
%{_bindir}/planex-depend
%{python_sitelib}/planex-*.egg-info
%{python_sitelib}/planex

%changelog
* Wed Mar 25 2015 Euan Harris <euan.harris@citrix.com> - 0.7.0-1
- Build products are now written to the _build subdirectory by default
- Add planex-pin, which overrides a package's sources with a local repo
- Add planex-init, which sets up the planex environment
- Add planex-fetch, replacing planex-downloader
- Remove planex-configure, which is superseded by planex-pin
- Rename Makefile.common to Makefile.rules

* Wed Jan 21 2015 Euan Harris <euan.harris@citrix.com> - 0.6.0-1
- planex-specdep is now known as planex-depend
- planex-depend: By default, produce packages for the host system
- planex-depend: Add a --topdir parameter to set rpmbuild working directory
- planex-depend, planex-configure: Package name checking is now optional
- planex-configure: SRPM building is now optional
- planex-clone, planex-configure: Default configuration directory is now '.'
- planex-cache: Support multiple cache locations
- planex-depend: Add support for git:// and hg:// source URLs
- Add Makefile.common, containing useful generic make rules

* Fri Oct 31 2014 Jon Ludlam <jonathan.ludlam@citrix.com> - 0.5.0-1
- Initial package

