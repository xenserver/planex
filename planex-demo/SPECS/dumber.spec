Name:           dumber
Version:        0.0.1
Release:        1%{?extrarelease}
Summary:        Dumber example for planex
License:        BSD3
Group:          Development/Other
URL:            http://github.com/jonludlam/dumber
Source0:        https://github.com/jonludlam/dumber/archive/v%{version}/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}
BuildRequires:  dumb

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
/usr/share/dumber/dumber

%changelog
* Thu Mar 27 2014 Jon Ludlam <jonathan.ludlam@citrix.com>
- Initial package

