Summary: RPM build tool
Name: planex
Version: 0.7.3
Release: 1%{?dist}
URL: http://github.com/xenserver/planex
Source0: http://github.com/xenserver/planex/archive/v%{version}/%{name}-%{version}.tar.gz
License: LGPLv2.1
BuildArch: noarch
BuildRequires: python-setuptools
Requires: createrepo
Requires: git
Requires: make
Requires: mock
Requires: python-argcomplete
Requires: python-argparse
Requires: python-setuptools
Requires: rpm-build
Requires: yum-plugin-priorities

%description
Planex is a tool for building RPMs. It manages interdependencies and caching.

%prep
%setup -q

%build
sed -i "s/\(version='\)[^'\"]\+/\1%{version}-%{release}/g" setup.py
%{__python} setup.py build

%install
%{__python} setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%files
%doc README.md
%doc LICENSE
%doc CHANGES
%{_bindir}/planex-cache
%{_bindir}/planex-depend
%{_bindir}/planex-fetch
%{_bindir}/planex-init
%{_bindir}/planex-pin
%{_bindir}/planex-make-srpm
%{_datarootdir}/%{name}/Makefile.rules
%{python_sitelib}/planex
%{python_sitelib}/planex-*.egg-info
%config%{_sysconfdir}/bash_completion.d/planex.bash

%changelog
* Mon Mar 14 2016 Euan Harris <euan.harris@citrix.com> 0.7.3-1
- planex-fetch: Handle Source URLs with fragments correctly

* Tue Nov 10 2015 Euan Harris <euan.harris@citrix.com> - 0.7.2-1
- planex-pin: It is now possible to pin to a bare Git repository
- planex-cache: Use yum configuration but not mock configuration when
  calculating hash
- planex-cache: When writing back to the cache, do not exit if the binary
  package already exists
- Locally-built packages now override newer packages of the same name in
  distribution repositories

* Tue May 26 2015 Euan Harris <euan.harris@citrix.com> - 0.7.1-1
- planex-cache: Update cached files' timestamps on cache hits
- planex-cache: Print mock's logs if it fails
- planex-pin: Improve formatting of the pins file

* Thu Apr 23 2015 Euan Harris <euan.harris@citrix.com> - 0.7.0-1
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

