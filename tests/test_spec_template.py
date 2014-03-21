import unittest
import textwrap
from fs.opener import fsopendir

from planex import spec_template
from planex import rpm_adapter
from planex import exceptions


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


class TestSpecTemplate(unittest.TestCase):
    def test_name(self):
        fs = fsopendir('ram:///')

        fs.setcontents('xenops-cli.spec.in', XENOPS_CLI_CONTENTS)
        template = spec_template.SpecTemplate(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        self.assertEquals('xenops-cli', template.name)

    def test_main_source(self):
        fs = fsopendir('ram:///')

        fs.setcontents('xenops-cli.spec.in', XENOPS_CLI_CONTENTS)
        template = spec_template.SpecTemplate(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        self.assertEquals(
            'git://github.com/xapi-project/xenops-cli',
            template.main_source)


class TestFromFile(unittest.TestCase):
    def test_file_does_not_exist(self):
        fs = fsopendir('ram:///')

        self.assertRaises(
            exceptions.NoSuchFile,
            lambda: spec_template.template_from_file(
                'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM()))

    def test_file_exist(self):
        fs = fsopendir('ram:///')
        fs.setcontents('xenops-cli.spec.in', XENOPS_CLI_CONTENTS)

        template = spec_template.template_from_file(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        self.assertFalse(template is None)


class TestTemplatesFromDir(unittest.TestCase):
    def test_empty_dir(self):
        fs = fsopendir('ram:///')

        templates = spec_template.templates_from_dir(
            fs, rpm_adapter.SimpleRPM())
        self.assertEquals([], templates)

    def test_one_entry(self):
        fs = fsopendir('ram:///')
        fs.setcontents('xenops-cli.spec.in', XENOPS_CLI_CONTENTS)
        template = spec_template.SpecTemplate(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        templates = spec_template.templates_from_dir(
            fs, rpm_adapter.SimpleRPM())
        self.assertEquals(1, len(templates))

    def test_non_spec_ins_are_excluded(self):
        fs = fsopendir('ram:///')
        fs.createfile('somefile')

        templates = spec_template.templates_from_dir(
            fs, rpm_adapter.SimpleRPM())
        self.assertEquals([], templates)

    def test_non_recursive(self):
        fs = fsopendir('ram:///')
        fs.makedir('somedir')
        fs.createfile('somedir/somefile.spec.in')

        templates = spec_template.templates_from_dir(
            fs, rpm_adapter.SimpleRPM())
        self.assertEquals([], templates)


class TestSources(unittest.TestCase):
    def test_length(self):
        fs = fsopendir('ram:///')
        fs.setcontents('xenops-cli.spec.in', XENOPS_CLI_CONTENTS)

        template = spec_template.template_from_file(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        self.assertEquals(2, len(template.sources))

    def test_sources(self):
        fs = fsopendir('ram:///')
        fs.setcontents('xenops-cli.spec.in', XENOPS_CLI_CONTENTS)

        template = spec_template.template_from_file(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        self.assertEquals([
            'git://github.com/xapi-project/xenops-cli',
            'git://someserver.com/adir/bdir/linux-3.x.pq.git#%{version}/linux-%{version}.pq.tar.gz'
        ], template.sources)

    def test_source_ordering(self):
        fs = fsopendir('ram:///')
        contents = 'Source04: somesource\n' + XENOPS_CLI_CONTENTS
        fs.setcontents('xenops-cli.spec.in', contents)

        template = spec_template.template_from_file(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        self.assertEquals([
            'git://github.com/xapi-project/xenops-cli',
            'git://someserver.com/adir/bdir/linux-3.x.pq.git#%{version}/linux-%{version}.pq.tar.gz',
            'somesource'
        ], template.sources)
