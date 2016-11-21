# Run these tests with 'nosetests':
#   install the 'python-nose' package (Fedora/CentOS or Ubuntu)
#   run 'nosetests' in the root of the repository

import glob
import os
import os.path
import shutil
import sys
import tempfile
import unittest

import planex.tarball


class BasicTests(unittest.TestCase):
    # unittest.TestCase has more methods than Pylint permits
    # pylint: disable=R0904

    def setUp(self):
        # Create a temporary directory
        self.tmpdir = tempfile.mkdtemp()
        self.tarball = planex.tarball.Tarball("tests/data/patchqueue.tar")

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.tmpdir)
        self.tarball.close()

    def test_archive_root(self):
        assert self.tarball.archive_root == "patchqueue"

    def test_getnames(self):
        expected = ["test.spec",
                    "SOURCES/test1.source",
                    "SOURCES/test2.source"]
        actual = self.tarball.getnames()
        self.assertEqual(sorted(expected), sorted(actual))

    def test_getnames_prefix(self):
        self.tarball.prefix = "SOURCES"
        expected = ["test1.source",
                    "test2.source"]
        actual = self.tarball.getnames()
        self.assertEqual(sorted(expected), sorted(actual))

    def test_extractfile(self):
        file = self.tarball.extractfile("SOURCES/test1.source")
        expected = ["test1.source contents\n"]
        actual = file.readlines()
        self.assertEqual(sorted(expected), sorted(actual))

    def test_extractfile_prefix(self):
        self.tarball.prefix = "SOURCES"
        file = self.tarball.extractfile("test1.source")
        expected = ["test1.source contents\n"]
        actual = file.readlines()
        self.assertEqual(sorted(expected), sorted(actual))

    def test_extract(self):
        self.tarball.extract("SOURCES/test1.source", self.tmpdir)
        with open(os.path.join(self.tmpdir, "test1.source")) as output:
            expected = ["test1.source contents\n"]
            actual = output.readlines()
        self.assertEqual(sorted(expected), sorted(actual))

    def test_extract_prefix(self):
        self.tarball.prefix = "SOURCES"
        self.tarball.extract("test1.source", self.tmpdir)
        with open(os.path.join(self.tmpdir, "test1.source")) as output:
            expected = ["test1.source contents\n"]
            actual = output.readlines()
        self.assertEqual(sorted(expected), sorted(actual))
