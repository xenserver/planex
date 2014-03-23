import unittest
from tests import common

from planex import spec_template
from planex import rpm_adapter
from planex import exceptions


class TestFromFile(unittest.TestCase):
    def test_file_does_not_exist(self):
        fs = common.make_ramfs()

        self.assertRaises(
            exceptions.NoSuchFile,
            lambda: spec_template.template_from_file(
                'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM()))

    def test_file_exist(self):
        fs = common.make_ramfs()
        fs.setcontents('xenops-cli.spec.in', common.XENOPS_CLI_CONTENTS)

        template = spec_template.template_from_file(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        self.assertFalse(template is None)


class TestTemplatesFromDir(unittest.TestCase):
    def test_empty_dir(self):
        fs = common.make_ramfs()

        templates = spec_template.templates_from_dir(
            fs, rpm_adapter.SimpleRPM(), '*')
        self.assertEquals([], templates)

    def test_one_entry(self):
        fs = common.make_ramfs()
        fs.setcontents('xenops-cli.spec.in', common.XENOPS_CLI_CONTENTS)
        template = spec_template.SpecTemplate(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        templates = spec_template.templates_from_dir(
            fs, rpm_adapter.SimpleRPM(), '*.spec.in')
        self.assertEquals(1, len(templates))

    def test_non_recursive(self):
        fs = common.make_ramfs()
        fs.makedir('somedir')
        fs.createfile('somedir/somefile.spec.in')

        templates = spec_template.templates_from_dir(
            fs, rpm_adapter.SimpleRPM(), '*')
        self.assertEquals([], templates)


class TestSources(unittest.TestCase):
    def test_length(self):
        fs = common.make_ramfs()
        fs.setcontents('xenops-cli.spec.in', common.XENOPS_CLI_CONTENTS)

        template = spec_template.template_from_file(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        self.assertEquals(2, len(template.sources))

    def test_sources(self):
        fs = common.make_ramfs()
        fs.setcontents('xenops-cli.spec.in', common.XENOPS_CLI_CONTENTS)

        template = spec_template.template_from_file(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        self.assertEquals([
            'git://github.com/xapi-project/xenops-cli',
            'git://someserver.com/adir/bdir/linux-3.x.pq.git#%{version}/linux-%{version}.pq.tar.gz'
        ], template.sources)

    def test_source_ordering(self):
        fs = common.make_ramfs()
        contents = 'Source04: somesource\n' + common.XENOPS_CLI_CONTENTS
        fs.setcontents('xenops-cli.spec.in', contents)

        template = spec_template.template_from_file(
            'xenops-cli.spec.in', fs, rpm_adapter.SimpleRPM())

        self.assertEquals([
            'git://github.com/xapi-project/xenops-cli',
            'git://someserver.com/adir/bdir/linux-3.x.pq.git#%{version}/linux-%{version}.pq.tar.gz',
            'somesource'
        ], template.sources)
