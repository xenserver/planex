"""
Tests for the class representing a link (lnk) or pin file
"""
import unittest
import mock

import planex.link


class TestLink(unittest.TestCase):
    """ Unit tests for the Link class """

    v1_link = """
{
    "URL": "https://code.citrite.net/rest/archive/latest/projects/XS/repos/sm.pg/archive?at=1.14&format=tar#/sm.patches.tar",
    "patchqueue": "master"
}
"""  # nopep8

    v1_link_sv = """
{
    "SchemaVersion": "1",
    "URL": "https://code.citrite.net/rest/archive/latest/projects/XS/repos/sm.pg/archive?at=1.14&format=tar#/sm.patches.tar",
    "patchqueue": "master"
}
"""  # nopep8

    v2_link = """
{
    "SchemaVersion": "2",
    "Source0":
    {
        "URL": "https://code.citrite.net/rest/archive/latest/projects/XSU/repos/sbd/archive?at=v1.3.0&format=tar"
    },
    "Source1":
    {
        "URL": "Blah"
    },
    "Patch0":
    {
        "URL": "https://code.citrite.net/rest/archive/latest/projects/~MARKSY/repos/sbd-centos/archive?at=f46b0e608f5&format=tar",
        "patches": "SOURCES"
    },
    "PatchQueue0":
    {
        "URL": "https://code.citrite.net/rest/archive/latest/projects/~MARKSY/repos/sbd.pg/archive?at=f4d3fb5&format=tar",
        "patchqueue": "master"
    }
}
"""  # nopep8

    v3_link = """
{
    "SchemaVersion": "3",
    "Source0":
    {
        "URL": "https://code.citrite.net/rest/archive/latest/projects/XSU/repos/sbd/archive?at=v1.3.0&format=tar"
    },
    "Source1":
    {
        "URL": "Blah"
    },
    "Archive0":
    {
        "URL": "https://code.citrite.net/rest/archive/latest/projects/~MARKSY/repos/sbd-centos/archive?at=f46b0e608f5&format=tar",
        "prefix": "SOURCES"
    },
    "PatchQueue0":
    {
        "URL": "https://code.citrite.net/rest/archive/latest/projects/~MARKSY/repos/sbd.pg/archive?at=f4d3fb5&format=tar",
        "prefix": "master"
    }
}
"""  # nopep8

    @mock.patch('planex.link.open', mock.mock_open(read_data=v1_link))
    def test_schema_missing(self):
        """ Test that the schema version is required """
        with self.assertRaises(planex.link.UnsupportedProperty):
            planex.link.Link('test_v1.lnk')

    @mock.patch('planex.link.open', mock.mock_open(read_data=v1_link_sv))
    def test_schema_v1(self):
        """ Test that the schema version of a v1 lnk is not supported """
        with self.assertRaises(planex.link.UnsupportedProperty):
            planex.link.Link('test_v1.lnk')

    @mock.patch('planex.link.open', mock.mock_open(read_data=v2_link))
    def test_schema_v2(self):
        """ Test that the schema version of a v2 lnk is 2 """
        link = planex.link.Link('test_v2.lnk')

        self.assertEquals(2, link.schema_version)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v3_link))
    def test_schema_v3(self):
        """ Test that the schema version of a v3 lnk is 3 """
        link = planex.link.Link('test_v3.lnk')

        self.assertEquals(3, link.schema_version)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v2_link))
    def test_patch_sources_v2(self):
        """ Test that we get sources if asking for patch_sources on v2"""

        link = planex.link.Link('test_v2.lnk')
        sources = link.patch_sources
        self.assertIn('Patch0', sources)
        self.assertNotIn('PatchQueue0', sources)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v3_link))
    def test_patch_sources_v3(self):
        """ Test that we get a failure if asking for patch_sources on v3"""

        link = planex.link.Link('test_v3.lnk')
        with self.assertRaises(planex.link.UnsupportedProperty):
            _ = link.patch_sources

    @mock.patch('planex.link.open', mock.mock_open(read_data=v2_link))
    def test_archives_v2(self):
        """ Test that we get a failure if asking for archives on v2"""

        link = planex.link.Link('test_v2.lnk')
        with self.assertRaises(planex.link.UnsupportedProperty):
            _ = link.archives

    @mock.patch('planex.link.open', mock.mock_open(read_data=v3_link))
    def test_archives_v3(self):
        """ Test that we get sources if asking for archives on v3"""

        link = planex.link.Link('test_v3.lnk')
        sources = link.archives
        self.assertIn('Archive0', sources)
        self.assertNotIn('PatchQueue0', sources)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v2_link))
    def test_patchqueue_sources_v2(self):
        """ Test that we get sources if asking for patchqueue_sources on v2"""

        link = planex.link.Link('test_v2.lnk')
        sources = link.patchqueue_sources
        self.assertIn('PatchQueue0', sources)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v3_link))
    def test_patchqueue_sources_v3(self):
        """ Test that we get sources if asking for patchqueue_sources on v2"""

        link = planex.link.Link('test_v3.lnk')
        sources = link.patchqueue_sources
        self.assertIn('PatchQueue0', sources)
