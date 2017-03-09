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

import planex.patchqueue
from planex.spec import Spec


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

        applied = list(planex.patchqueue.parse_patchseries(series))

        self.assertIn("patch_no_guard_or_comment", applied)
        self.assertIn("patch_with_a_comment", applied)
        self.assertNotIn("patch_with_a_positive_guard", applied)
        self.assertIn("patch_with_a_negative_guard", applied)

    def test_rewrite_spec(self):
        spec = Spec("tests/data/manifest/branding-xenserver.spec",
                    check_package_name=False)
        patches = ["first.patch", "second.patch", "third.patch"]
        rewritten = planex.patchqueue.expand_patchqueue(spec, patches)
        self.assertIn("Patch0: first.patch\n", rewritten)
        self.assertIn("Patch1: second.patch\n", rewritten)
        self.assertIn("Patch2: third.patch\n", rewritten)

    def test_autosetup_present(self):
        spec = Spec("tests/data/manifest/branding-xenserver.spec",
                    check_package_name=False)
        patches = ["first.patch"]
        planex.patchqueue.expand_patchqueue(spec, patches)

    def test_autosetup_missing(self):
        spec = Spec("tests/data/ocaml-uri.spec", check_package_name=False)
        patches = ["first.patch"]
        with self.assertRaises(planex.patchqueue.SpecMissingAutosetup):
            planex.patchqueue.expand_patchqueue(spec, patches)
