import unittest
import mock
import textwrap

from tests import common

from planex import rpm_adapter


class TestSimpleRPM(unittest.TestCase):
    def test_get_sources(self):
        ramfs = common.make_ramfs()
        ramfs.setcontents('somefile', 'Source: somesource')

        rpm = rpm_adapter.SimpleRPM()
        sources = rpm.get_sources('somefile', ramfs)
        self.assertEquals(['somesource'], sources)


class TestRPMLibrary(unittest.TestCase):
    def test_get_sources(self):
        ramfs = common.make_ramfs()
        ramfs.setcontents('xenops-cli.spec.in', common.XENOPS_CLI_CONTENTS)

        rpm = rpm_adapter.RPMLibraryAdapter()
        sources = rpm.get_sources('xenops-cli.spec.in', ramfs)
        self.assertEquals(
            [
                'git://github.com/xapi-project/xenops-cli',
                'git://someserver.com/adir/bdir/linux-3.x.pq.git#UNRELEASED/linux-UNRELEASED.pq.tar.gz',
            ],
            sources
        )

    def test_get_sources_with_buildrequires_pre(self):
        ramfs = common.make_ramfs()
        contents = common.XENOPS_CLI_CONTENTS.replace(
            '#SOME_COMMENT','BuildRequires(pre): gcc')
        ramfs.setcontents('xenops-cli.spec.in', contents)

        rpm = rpm_adapter.RPMLibraryAdapter()
        sources = rpm.get_sources('xenops-cli.spec.in', ramfs)
        self.assertEquals(
            [
                'git://github.com/xapi-project/xenops-cli',
                'git://someserver.com/adir/bdir/linux-3.x.pq.git#UNRELEASED/linux-UNRELEASED.pq.tar.gz',
            ],
            sources
        )
