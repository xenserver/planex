from fs.opener import fsopendir
import mock


XENOPS_CLI_CONTENTS = """
Name:           xenops-cli
Version:        @VERSION@
Release:        2
Summary:        CLI for xenopsd, the xapi toolstack domain manager
License:        LGPL
Group:          Development/Other
URL:            https://github.com/xapi-project/xenops-cli/archive/xenops-cli-%{version}.tar.gz
Source0:        git://github.com/xapi-project/xenops-cli
Source1:        git://someserver.com/adir/bdir/linux-3.x.pq.git#%{version}/linux-%{version}.pq.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}
BuildRequires:  ocaml ocaml-findlib ocaml-camlp4-devel
BuildRequires:  ocaml-obuild ocaml-xcp-idl-devel cmdliner-devel ocaml-uuidm-devel
#Requires:       message-switch
#SOME_COMMENT

# XXX transitively required by message_switch
BuildRequires:  ocaml-oclock-devel

%description
Command-line interface for xenopsd, the xapi toolstack domain manager.

%prep
%setup -q -n %{name}-%{version}

%build
make

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/%{_sbindir}
install main.native %{buildroot}/%{_sbindir}/xenops-cli

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
%doc README.md LICENSE MAINTAINERS
%{_sbindir}/xenops-cli

%changelog
* Thu May 30 2013 David Scott <dave.scott@eu.citrix.com>
- Initial package
"""


def make_ramfs():
    def getsyspath(fname):
        return 'SYSPATH:' + fname

    fs = fsopendir('ram:///')
    fs.getsyspath = mock.Mock(side_effect=getsyspath)
    return fs
