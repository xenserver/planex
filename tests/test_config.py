"""Tests for Configuration class"""

import os
import os.path
import shutil
import tempfile
import unittest
from planex.config import Configuration


class ConfigTests(unittest.TestCase):
    """Basic Configuration class tests"""

    def setUp(self):
        # Create a temporary directory
        self.tmpdir = tempfile.mkdtemp()
        with open(os.path.join(self.tmpdir, '.planexrc'), 'w') as fileh:
            fileh.write("[sectionA]\n")
            fileh.write("alpha = abc\n")
            fileh.write("beta = xyz\n")
            fileh.write("[sectionB]\n")
            fileh.write("alpha = pqr\n")
            fileh.write("gamma = lmn\n")
        self.cwd = os.getcwd()
        os.chdir(self.tmpdir)

    def tearDown(self):
        # Remove the directory after the test
        os.chdir(self.cwd)
        shutil.rmtree(self.tmpdir)

    def test_exists(self):
        """Values for options present are returned"""
        self.assertEqual(Configuration.get('sectionA', 'alpha'), 'abc')
        self.assertEqual(Configuration.get('sectionB', 'alpha'), 'pqr')

    def test_defaults(self):
        """Options that are absent have default values"""
        self.assertEqual(Configuration.get('sectionA', 'gamma'), None)
        self.assertEqual(Configuration.get('sectionB', 'delta', 'jkl'), 'jkl')
