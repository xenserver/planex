Name:           dumbest
Version:        0.1
Release:        1%{?extrarelease}
Summary:        Dumbest example for planex
License:        BSD3
Group:          Development/Other
URL:            http://github.com/simonjbeaumont/dumbest
Source0:        https://github.com/simonjbeaumont/%{name}/archive/v%{version}/%{name}-%{version}.tar.gz
Source1:        https://github.com/simonjbeaumont/%{name}-extra/archive/v%{version}/%{name}-extra-%{version}.tar.gz

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}

%description
Dumbest package for demonstrating planex with multiple sources

%prep
%setup 
%setup -a 1

%build

%install

%clean

%files

%changelog
* Thu Mar 27 2014 Jon Ludlam <jonathan.ludlam@citrix.com>
- Initial package

