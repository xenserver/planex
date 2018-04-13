Summary: RPM build tool
Name: planex
Version: 4.0.0
Release: beta2%{?dist}
URL: http://github.com/xenserver/planex
Source0: http://github.com/xenserver/planex/archive/v%{version}/%{name}-%{version}.tar.gz
License: LGPLv2.1
BuildArch: noarch
BuildRequires: python-setuptools
Requires: createrepo
Requires: git
Requires: GitPython
Requires: make
Requires: mock
Requires: python-argcomplete
Requires: python-argparse
Requires: python-requests
Requires: python-setuptools
Requires: rpm-build
Requires: yum-plugin-priorities

%description
Planex is a tool for building collections of RPMs.

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
%{_bindir}/planex-build-mock
%{_bindir}/planex-clone
%{_bindir}/planex-create-mock-config
%{_bindir}/planex-depend
%{_bindir}/planex-fetch
%{_bindir}/planex-init
%{_bindir}/planex-make-srpm
%{_bindir}/planex-manifest
%{_bindir}/planex-patchqueue
%{_bindir}/planex-pin
%{python_sitelib}/planex
%{python_sitelib}/planex-*.egg-info
%{_datadir}/planex/Makefile.rules
%config%{_sysconfdir}/bash_completion.d/planex.bash

%changelog
* Tue Apr 10 2018 Marcello Seri <marcello.seri@citrix.com> - 4.0.0-beta1
- add support for the boolean IgnoreAutosetup in links
- do not extract the same resource multiple times
- add bulk extraction for tarball-type sources
- update links to schemaVersion 3
- drop support for schemaVersion=1
- fetch: do not use an intermediate temporary fetch file
- fetch: mitigate race condition when fetching to a temp file
- port code from pycurl to requests
- README: Add a section on design principles
- README: High level overview of links and pins
- README: Add a section on spec files and spec repository structure
- improve look of rewritten spec files
- spec.py: Expand macros in links when loading
- do a proper specfile rewrite when creating srpms
- make links replace source/patch/patchqueue fields in the spec file
- follow specfile sourcename semantics when parsing links
- fetch: Take spec file and an optional link as arguments
- spec: Rename File and GitArchive to Blob and GitBlob
- fetch: Add support for generating archives from local Git repositories
- spec: Expand patchqueues
- spec: Add extract_source() methods to spec and resource classes
- spec: Add a separate list of resources, with methods to add to it
- spec: Add decorator to expand RPM macros in strings
- overall code cleanups and refactorings

* Tue Mar 20 2018 Euan Harris <euan.harris@citrix.com> - 3.1.0-1
- planex-makesrpm: Search for source files in patch archives

* Mon Mar 12 2018 Euan Harris <euan.harris@citrix.com> - 3.0.0-1
- Makefile.rules: Do not make links to _build/RPMS and _build/MANIFESTS
- planex-fetch: Remove --mirror argument
- planex-fetch: Do not create path to downloaded file - Makefile.rules
  now does this
- planex-mock: Do not pass _topdir through to mock
- planex-mock: Use RPM library to find the correct repository path for
  createrepo, instead of a hard-coded path
- planex-make-srpm: Fix crash when reading a .gitarchive-info file
  containing unexpanded Git format strings
- planex-patchqueue: Apply patchqueues to specs with %autopatch directives
  as well as %autosetup directives

* Mon Jan 8 2018 Euan Harris <euan.harris@citrix.com> - 2.2.0-1
- planex-makesrpm: Support multiple patchqueues
- planex-patchqueue: Insert new patches after existing patches
- planex-manifest: Only generate manifest if link URL is present
- planex-create-mock-config: add 'disablerepo' option
- planex-depend: Ensure that a package's runtime dependencies
  are available before it is built, so that the resulting package
  can be installed immediately
- Docker: Use latest CentOS base image

* Mon Dec 11 2017 Euan Harris <euan.harris@citrix.com> - 2.1.2-1
- Makefile.rules: Work around a race in the ln command

* Thu Nov 30 2017 Euan Harris <euan.harris@citrix.com> - 2.1.1-1
- planex-mock: Properly create the RPMS top-level symlink
- planex-make-srpm: Don't cause RPM to choke on a malformed gitsha
- planex-create-mock-config: honour exclude and includepkgs
- planex-pin: Add an option to specify the location of the pin file

* Mon Sep 4 2017 Euan Harris <euan.harris@citrix.com> - 2.1.0-1
- planex-pin: Reintroduce utility to override a package's sources with
  a local repo
- Makefile.rules: Split up centralized _build/ directory creation
- planex-clone: Remove unused --pins-dir argument
- planex-clone: Add --skip-base argument
- planex-create-mock-config: add --environment argument

* Wed Aug 23 2017 Euan Harris <euan.harris@citrix.com> - 2.0.1-1
- depend: Handle pinned packages without patchqueues correctly

* Wed Aug 16 2017 Euan Harris <euan.harris@citrix.com> - 2.0.0-1
- patchqueue: Patch queues no longer contain spec files
- depend: Specs and links listed earlier on the command line override
  those listed later
- depend: Remove --pins-dir option
- extract: Remove obsolete utility
- link: Store the path from which the link was loaded

* Mon Aug 14 2017 Euan Harris <euan.harris@citrix.com> - 1.0.0-1
* git: Remove unused describe() and current_branch() methods

* Fri Jul 21 2017 Euan Harris <euan.harris@citrix.com> - 0.23.1-1
- depend: Do not make an SRPM depend on a link if a pin is also present
- Makefile.rules: add RPMBUILD_EXTRA_FLAGS variable
- depend: Remove unused --repos_path argument

* Mon May 8 2017 Euan Harris <euan.harris@citrix.com> - 0.23.0-1
- planex-makesrpm: Do not rewrite 'autosetup' rules in spec files

* Mon May 8 2017 Euan Harris <euan.harris@citrix.com> - 0.22.1-1
- planex-patchqueue: Handle static tarballs in patchqueue repositories
  correctly

* Wed May 3 2017 Euan Harris <euan.harris@citrix.com> - 0.22.0-1
- mock: Restore loglevel to normal and allocate a pty so that it
  continues to print standard error logging when running in a container.

* Thu Apr 20 2017 Euan Harris <euan.harris@citrix.com> - 0.21.0-1
- Add planex-create-mock-config, which constructs a mock configuration
  file from the system yum configuration.
- planex-make-srpm: Add Provides: tags containing the Git hashes of the
  sources used to build binary RPMs, if this information is available.
- Makfile.rules, planex-patchqueue: Always rebuild pinned patchqueue tarballs,
  but short-circuit the rebuilding of dependent source and binary RPMs if the
  contents of the patchqueue have not changed
- planex-clone: Continue if cloning one of a series of pinned repos fails
- Makefile.rules: add a dependency on the mock config

* Mon Mar 27 2017 Euan Harris <euan.harris@citrix.com> - 0.20.0-1
- planex-build-mock: Add '--loopback-config-extra' option to pass extra
  lines to the loopback repository configuration
- planex-depend: Add option to disable generation of buildrequires
  dependencies
- planex-fetch: Fix a TOCTOU race when creating directories
- planex-container: Pass SSH agent socket through to container

* Fri Mar 10 2017 Euan Harris <euan.harris@citrix.com> - 0.19.0-1
- planex-build-mock: Pass --verbose to mock if --quiet is not supplied
  so that logs are produced inside docker with concurrent builds which
  use make's output --output-sync=target option
- planex-patchqueue: Check that pinned spec file contains the 
  'autosetup -p1' macro which is needed to apply patch queue
- planex-clone: Improve handling of pins to branches, tags and commit
  hashes

* Thu Feb 23 2017 Euan Harris <euan.harris@citrix.com> - 0.18.0-1
- planex-clone-sources has been removed and replaced by planex-clone
- planex-extract: Remove support for heavyweight branches
- Makefile.rules: It is now possible to override the Mock configuration
  used to build packages by defining the MOCK_CONFIGDIR and MOCK_ROOT
  variables

* Mon Feb 20 2017 Euan Harris <euan.harris@citrix.com> - 0.17.0-1
- planex-clone: Add ability to clone repositories with patchqueues

* Tue Feb 7 2017 Euan Harris <euan.harris@citrix.com> - 0.16.2-1
- planex-clone: Fix typo in Jenkinsfile fragment template

* Mon Feb 6 2017 Euan Harris <euan.harris@citrix.com> - 0.16.1-1
- planex-clone: Allow list of pin files to be empty

* Mon Feb 6 2017 Euan Harris <euan.harris@citrix.com> - 0.16.0-1
- planex-build-mock: Add --init option to pre-warm root cache

* Wed Feb 1 2017 Euan Harris <euan.harris@citrix.com> - 0.15.1-1
- git library: Add current_branch function

* Thu Jan 12 2017 Euan Harris <euan.harris@citrix.com> - 0.15.0-1
- planex-patchqueue: If a pin specifies a remote URL, look for a local
  clone of the repository
- planex-clone: Add utility to clone repositories listed in pin files

* Thu Jan 12 2017 Euan Harris <euan.harris@citrix.com> - 0.14.0-1
- planex-mock: enable concurrent package builds

* Wed Jan 4 2017 Euan Harris <euan.harris@citrix.com> - 0.13.0-1
- planex-mock: automatically generate loopback repository configuration
- planex-cache has been removed

* Tue Jan 3 2017 Euan Harris <euan.harris@citrix.com> - 0.12.0-1
- Docker: allow passwordless sudo for the build user
- planex-patchqueue: Add a new utility to create a patchqueue based on
  a spec file and a locally checked-out Git repository
- planex-pin has been removed and replaced by planex-patchqueue
- planex-makesrpm: Do not extract all files in source directories
- spec: Report local sources and patches separately
- makesrpm: Extract patches and sources separately
- Add utility classes for dealing with links, tarballs and patchqueues
- planex-makesrpm: Require 'patches' to be declared explicitly in
  link files
- Tools which accepted the --topdir and --dist arguments now accept
  rpmbuild-style --define arguments
- planex-extract: Do not unpack patches or rewrite spec files 
- planex-makesrpm: Consume the patch queue tarball directly, rather
  than requiring it to be unpacked
- Makefile.rules: Don't symlink SOURCES into _build, and keep local
  and downloaded sources separate

* Thu Nov 10 2016 Euan Harris <euan.harris@citrix.com> - 0.11.0-1
- planex-clone-sources: Add a tool to check out source repositories
- planex-manifest: Add a tool to record repository hashes
- planex-build-mock: Add a wrapper around mock
- planex-container: Add a wrapper to run planex in a Docker container
- planex-extract: Don't prepend package name to patch filename
- Add utility classes for links, patch queues, repositories and tarballs
- Makefile.rules: Fail if _build/deps can't be rebuilt

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

