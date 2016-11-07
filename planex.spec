Summary: RPM build tool
Name: planex
Version: 0.10.0
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
Requires: python-requests
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
%{__install} -D -m 644 planex/planex.bash %{buildroot}%{_sysconfdir}/bash_completion.d/planex.bash
%{__install} -D -m 644 planex/Makefile.rules %{buildroot}%{_datadir}/planex/Makefile.rules

%files
%doc README.md
%doc LICENSE
%doc CHANGES
%{_bindir}/planex-cache
%{_bindir}/planex-depend
%{_bindir}/planex-extract
%{_bindir}/planex-fetch
%{_bindir}/planex-init
%{_bindir}/planex-pin
%{_bindir}/planex-make-srpm
%{python_sitelib}/planex
%{python_sitelib}/planex-*.egg-info
%{_datadir}/planex/Makefile.rules
%config%{_sysconfdir}/bash_completion.d/planex.bash

%changelog
* Mon Oct 03 2016 Euan Harris <euan.harris@citrix.com> - 0.10.0-1
- Several commands can now accept multiple --define arguments to
  set or override RPM macro definitions
- planex-depend: Generate short name targets for SRPMS
- planex-depend: Remove --ignore and --ignore-from flags
- planex-extract: prepend manifest of sources (and branch variable)
- Makefile.rules: make _build/SPECS a directory, not a symlink

* Mon Oct 03 2016 Euan Harris <euan.harris@citrix.com> - 0.9.0-2
- Install Makefile.rules in /usr/share/planex for backwards compatibility

* Thu Sep 08 2016 Euan Harris <euan.harris@citrix.com> - 0.9.0-1
- Add planex-extract, which extracts and processes files from tarballs
- Planex-fetch: Add support for fetching over FTP and for tar.xz files
- planex-fetch: Teach planex-planex-fetch about links
- planex-fetch: Add support for fetching specs and sources from remote
  repositories
- planex-make-srpm: Remove patchqueue expansion, now handled by
  planex-extract
- planex-make-srpm: Don't create _build directory in temporary working
  space
- Makefile.rules: Don't link SRPMS to _build/SRPMS
- Docker: Rewrite Dockerfile to reduce image size and support Docker Hub

* Tue Jul 26 2016 Euan Harris <euan.harris@citrix.com> - 0.8.0-1
- planex-make-srpm: Add a wrapper around rpmbuild which expands patchqueue
  repositories as inline patches in the SRPM
- Add initial support for running Planex in a Docker container
- Remove unmaintained, experimental Debian package-generation scripts

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

