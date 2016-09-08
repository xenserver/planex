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

import planex.extract


class BasicTests(unittest.TestCase):
    # unittest.TestCase has more methods than Pylint permits
    # pylint: disable=R0904

    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)

    def test_patch_guards(self):
        series = ("patch_no_guard_or_comment\n",
                  "patch_with_a_comment # this is a comment\n",
                  "patch_with_a_positive_guard #+aguard\n",
                  "patch_with_a_negative_guard #-aguard\n",
                  )

        applied = list(planex.extract.parse_patchseries(series))

        self.assertIn("patch_no_guard_or_comment", applied)
        self.assertIn("patch_with_a_comment", applied)
        self.assertNotIn("patch_with_a_positive_guard", applied)
        self.assertIn("patch_with_a_negative_guard", applied)

    def test_rewrite_spec(self):
        patches = ("first.patch", "second.patch", "third.patch")
        outfile = os.path.join(self.test_dir, "out.spec")
        planex.extract.rewrite_spec("tests/data/ocaml-uri.spec", outfile,
                                    patches, -1, None)
        with open(outfile) as fh:
            spec = fh.read(4096).split('\n')

        self.assertIn("Patch0: %{name}-first.patch", spec)
        self.assertIn("Patch1: %{name}-second.patch", spec)
        self.assertIn("Patch2: %{name}-third.patch", spec)
