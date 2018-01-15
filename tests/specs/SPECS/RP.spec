# -*- rpm-spec -*-
%define repo_name  nsource

Summary: nsource for RP type
Name: RP
Version: 1.0
Release: 1
License: BSD
Group: Xen
URL: http://www.citrix.com
Vendor:  citrix
Source0: https://github.com/xenserver/%{repo_name}/archive/v%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Requires: python-setuptools
BuildRequires: python-setuptools
Patch0: testpatch0

Patch2001: testpatch1
Patch2002: testpatch2

%description
A simple package for testing planex building RP type

%prep
%autosetup -p1 -N -n %{repo_name}-%{version}
%patch0 -p1 -b .patch0

%patch2001 -p1
%patch2002 -p1

%build
python setup.py build

%install
python setup.py install --root %{buildroot}

%files 
%defattr(-,root,root,-)
/usr/lib/python2.7/site-packages/nsource*
/usr/bin/nsource

%changelog
* Mon Jan 15 2018  <kun.ma@citrix.com>
- Init version
