# Run these tests with 'nosetests':
#   install the 'python-nose' package (Fedora/CentOS or Ubuntu)
#   run 'nosetests' in the root of the repository

import glob
import os
import sys
import unittest

import planex.makesrpm


class BasicTests(unittest.TestCase):
    # unittest.TestCase has more methods than Pylint permits
    # pylint: disable=R0904

    def test_patch_guards(self):
        series = ("patch_no_guard_or_comment\n",
                  "patch_with_a_comment # this is a comment\n",
                  "patch_with_a_positive_guard #+aguard\n",
                  "patch_with_a_negative_guard #-aguard\n",
                  )

        applied = list(planex.makesrpm.parse_patchseries(series))

        self.assertIn("patch_no_guard_or_comment", applied)
        self.assertIn("patch_with_a_comment", applied)
        self.assertNotIn("patch_with_a_positive_guard", applied)
        self.assertIn("patch_with_a_negative_guard", applied)
