"""Test tarball handling"""

import os
import os.path
import shutil
import tempfile
import unittest

import planex.tarball


class BasicTests(unittest.TestCase):
    """Basic tarball tests"""

    def setUp(self):
        # Create a temporary directory
        self.tmpdir = tempfile.mkdtemp()
        self.tarball = planex.tarball.Tarball("tests/data/patchqueue.tar")

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.tmpdir)
        self.tarball.close()

    def test_archive_root(self):
        """Tarball root prefix is detected correctly"""
        self.assertEqual(self.tarball.archive_root, "patchqueue")

    def test_getnames(self):
        """Tarball listing without prefix includes all members"""
        expected = ["test.spec",
                    "SOURCES/test1.source",
                    "SOURCES/test2.source"]
        actual = self.tarball.getnames()
        self.assertItemsEqual(expected, actual)

    def test_getnames_prefix(self):
        """Tarball listing with prefix only includes members under prefix"""
        self.tarball.prefix = "SOURCES"
        expected = ["test1.source",
                    "test2.source"]
        actual = self.tarball.getnames()
        self.assertItemsEqual(expected, actual)

    def test_extractfile(self):
        """Members can be extracted to a file-like object"""
        extracted = self.tarball.extractfile("SOURCES/test1.source")
        expected = ["test1.source contents\n"]
        actual = extracted.readlines()
        self.assertItemsEqual(expected, actual)

    def test_extractfile_prefix(self):
        """Members under prefix can be extracted to a file-like object"""
        self.tarball.prefix = "SOURCES"
        extracted = self.tarball.extractfile("test1.source")
        expected = ["test1.source contents\n"]
        actual = extracted.readlines()
        self.assertItemsEqual(expected, actual)

    def test_extract(self):
        """Members can be extracted to the filesystem"""
        self.tarball.extract(("SOURCES/test1.source",), self.tmpdir)
        with open(os.path.join(self.tmpdir, "test1.source")) as output:
            expected = ["test1.source contents\n"]
            actual = output.readlines()
        self.assertItemsEqual(expected, actual)

    def test_extract_prefix(self):
        """Members under prefix can be extracted to the filesystem"""
        self.tarball.prefix = "SOURCES"
        self.tarball.extract(("test1.source",), self.tmpdir)
        with open(os.path.join(self.tmpdir, "test1.source")) as output:
            expected = ["test1.source contents\n"]
            actual = output.readlines()
        self.assertItemsEqual(expected, actual)

    def test_extract_multiple(self):
        """Members under prefix can be extracted to the filesystem"""
        self.tarball.prefix = "SOURCES"
        sources = ("test1.source", "test2.source")
        self.tarball.extract(sources, self.tmpdir)
        for source in sources:
            self.assertEqual(
                os.path.isfile(os.path.join(self.tmpdir, source)),
                True,
                msg="{} not found in {}".format(source, self.tmpdir)
            )
