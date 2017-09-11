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

    @mock.patch('planex.link.open', mock.mock_open(read_data=v2_link))
    def test_schema_v2(self):
        """ Test that the schema version of a v2 lnk is 2 """
        link = planex.link.Link('test_v2.lnk')

        self.assertEquals(2, link.schema_version)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v1_link))
    def test_schema_v1(self):
        """ Test that the schema version of a v1 lnk is coerced to 1 """
        link = planex.link.Link('test_v1.lnk')

        self.assertEquals(1, link.schema_version)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v1_link))
    def test_patch_sources_v1(self):
        """ Test that we get an error if asking for patch_sources on v1"""

        link = planex.link.Link('test_v1.lnk')
        sources = None
        with self.assertRaises(planex.link.UnsupportedProperty):
            sources = link.patch_sources
        self.assertIsNone(sources)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v1_link))
    def test_patchqueue_sources_v1(self):
        """ Test that we get an error if asking for patchqueue_sources on v1"""

        link = planex.link.Link('test_v1.lnk')
        sources = None
        with self.assertRaises(planex.link.UnsupportedProperty):
            sources = link.patchqueue_sources
        self.assertIsNone(sources)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v2_link))
    def test_patch_sources_v2(self):
        """ Test that we get sources if asking for patch_sources on v2"""

        link = planex.link.Link('test_v2.lnk')
        sources = link.patch_sources
        self.assertIn('Patch0', sources)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v2_link))
    def test_patchqueue_sources_v2(self):
        """ Test that we get sources if asking for patchqueue_sources on v2"""

        link = planex.link.Link('test_v2.lnk')
        sources = link.patchqueue_sources
        self.assertIn('PatchQueue0', sources)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v1_link))
    def test_patchqueue_v1(self):
        """ Test that we get data for patchqueue on v1"""

        link = planex.link.Link('test_v1.lnk')
        patchqueue = link.patchqueue
        self.assertEqual('master', patchqueue)

    @mock.patch('planex.link.open', mock.mock_open(read_data=v2_link))
    def test_patchqueue_v2(self):
        """ Test that we get an error for patchqueue on v2"""

        link = planex.link.Link('test_v2.lnk')
        patchqueue = None
        with self.assertRaises(planex.link.UnsupportedProperty):
            patchqueue = link.patchqueue
        self.assertIsNone(patchqueue)
