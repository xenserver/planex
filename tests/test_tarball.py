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

    def test_getmembers(self):
        expected = ["test.spec",
                    "SOURCES/test1.source",
                    "SOURCES/test2.source"]
        actual = [mem.name for mem in self.tarball.getmembers()]
        self.assertEqual(sorted(expected), sorted(actual))

    def test_getmembers_prefix(self):
        self.tarball.prefix = "SOURCES"
        expected = ["test1.source",
                    "test2.source"]
        actual = [mem.name for mem in self.tarball.getmembers()]
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

    def test_extract_dir(self):
        self.tarball.extract_dir("SOURCES", self.tmpdir)
        expected = {"test1.source": ["test1.source contents\n"],
                    "test2.source": ["test2.source contents\n"]}
        actual_dir = os.listdir(self.tmpdir)
        self.assertEqual(sorted(expected.keys()), sorted(actual_dir))

        for filename in expected.keys():
            with open(os.path.join(self.tmpdir, filename)) as output:
                actual = output.readlines()
                self.assertEqual(actual, expected[filename])

    def test_extract_dir_prefix(self):
        self.tarball.prefix = "SOURCES"
        self.tarball.extract_dir("", self.tmpdir)
        expected = {"test1.source": ["test1.source contents\n"],
                    "test2.source": ["test2.source contents\n"]}
        actual_dir = os.listdir(self.tmpdir)
        self.assertEqual(sorted(expected.keys()), sorted(actual_dir))

        for filename in expected.keys():
            with open(os.path.join(self.tmpdir, filename)) as output:
                actual = output.readlines()
                self.assertEqual(actual, expected[filename])
