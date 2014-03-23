import unittest
import textwrap
from fs.opener import fsopendir

from planex import rpm_adapter


XENOPS_CLI_CONTENTS = textwrap.dedent("""
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
""")


class TestSimpleRPM(unittest.TestCase):
    def test_get_sources(self):
        ramfs = fsopendir('ram:///')
        ramfs.setcontents('somefile', 'Source: somesource')

        rpm = rpm_adapter.SimpleRPM()
        sources = rpm.get_sources('somefile', ramfs)
        self.assertEquals(['somesource'], sources)


class TestRPMLibrary(unittest.TestCase):
    def test_get_sources(self):
        ramfs = fsopendir('ram:///')
        ramfs.setcontents('xenops-cli.spec.in', XENOPS_CLI_CONTENTS)

        rpm = rpm_adapter.RPMLibraryAdapter()
        sources = rpm.get_sources('xenops-cli.spec.in', ramfs)
        self.assertEquals(
            [
                'git://github.com/xapi-project/xenops-cli',
                'git://someserver.com/adir/bdir/linux-3.x.pq.git#UNRELEASED/linux-UNRELEASED.pq.tar.gz',
            ],
            sources
        )
