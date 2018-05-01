Name: branding-xenserver
Version: 7.0.91
Release: 1
Summary: Build-time branding for XenServer
License: Proprietary
Source0: https://code.citrite.net/rest/archive/latest/projects/XS/repos/branding/archive?format=tar.gz#/%{name}.tar.gz
BuildArch: noarch
BuildRequires: python

Requires: python

%description
Files containing platform and product versioning, EULA etc.

%prep
%autosetup -p1

%install
%{__make} -f Citrix/XenServer/Makefile install DESTDIR=%{buildroot}


%files
%{_sysconfdir}/rpm/macros.*
%{_usrsrc}/branding
