%define name planex
%define version 0.5.0
%define release 1

Summary: RPM/deb build tool
Name: %{name}
Version: %{version}
Release: %{release}
URL: http://github.com/xenserver/planex
Source0: http://github.com/xenserver/planex/archive/v%{version}/%{name}-%{version}.tar.gz
License: GPLv2
BuildArch: noarch
BuildRequires: python-setuptools
Requires: mock
Requires: rpm-build
Requires: createrepo
Requires: python-argparse

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
%{_bindir}/planex-build
%{_bindir}/planex-cache
%{_bindir}/planex-clone
%{_bindir}/planex-configure
%{_bindir}/planex-downloader
%{_bindir}/planex-makedeb
%{_bindir}/planex-specdep
%{python_sitelib}/planex-*.egg-info
%{python_sitelib}/planex

%changelog
* Fri Oct 31 2014 Jon Ludlam <jonathan.ludlam@citrix.com> - 0.5.0-1
- Initial package

