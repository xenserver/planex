# -*- rpm-spec -*-
%define repo_name  nsource

Summary: nsource for PQ type
Name: PQ
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

%description
A simple package for testing planex building PQ type

%prep
%autosetup -p1 -n %{repo_name}-%{version}

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
