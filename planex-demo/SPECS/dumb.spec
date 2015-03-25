Name:           dumb
Version:        0.1
Release:        1%{?extrarelease}
Summary:        Dumb example for planex
License:        BSD3
Group:          Development/Other
URL:            http://github.com/jonludlam/dumb
Source0:        https://github.com/jonludlam/dumb/archive/%{version}/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}

%description
Dumb package for demonstrating planex

%prep
%setup -q

%build
make

%install
export DESTDIR=%{buildroot}/
make install

%clean
rm -rf %{buildroot}

%files
/usr/share/dummy

%changelog
* Thu Mar 27 2014 Jon Ludlam <jonathan.ludlam@citrix.com>
- Initial package

