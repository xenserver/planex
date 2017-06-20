"""Test patchqueue handling"""

import shutil
import tempfile
import unittest

from hypothesis import given
from nose.plugins.attrib import attr

import tests.strategies as tst

import planex.patchqueue
from planex.spec import Spec


class BasicTests(unittest.TestCase):
    """Basic tests of patchqueue handling"""

    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)

    def test_patch_guards(self):
        """Patch guards are applied correctly"""
        series = ("patch_no_guard_or_comment\n",
                  "patch_with_a_comment # this is a comment\n",
                  "patch_with_a_positive_guard #+aguard\n",
                  "patch_with_a_negative_guard #-aguard\n")

        applied = list(planex.patchqueue.parse_patchseries(series))

        self.assertIn("patch_no_guard_or_comment", applied)
        self.assertIn("patch_with_a_comment", applied)
        self.assertNotIn("patch_with_a_positive_guard", applied)
        self.assertIn("patch_with_a_negative_guard", applied)

    def test_rewrite_spec(self):
        """Patches are inserted into rewritten spec file"""
        spec = Spec("tests/data/manifest/branding-xenserver.spec",
                    check_package_name=False)
        patches = ["first.patch", "second.patch", "third.patch"]
        rewritten = planex.patchqueue.expand_patchqueue(spec, patches)
        self.assertIn("Patch0: first.patch\n", rewritten)
        self.assertIn("Patch1: second.patch\n", rewritten)
        self.assertIn("Patch2: third.patch\n", rewritten)

    def test_autosetup_present(self):
        """Patchqueue application succeeds if %autosetup is present"""
        spec = Spec("tests/data/manifest/branding-xenserver.spec",
                    check_package_name=False)
        patches = ["first.patch"]
        rewritten = planex.patchqueue.expand_patchqueue(spec, patches)
        self.assertIn("Patch0: first.patch\n", rewritten)

    def test_autosetup_missing(self):
        """Patchqueue application fails if %autosetup is not present"""
        spec = Spec("tests/data/ocaml-uri.spec", check_package_name=False)
        patches = ["first.patch"]
        with self.assertRaises(planex.patchqueue.SpecMissingAutosetup):
            planex.patchqueue.expand_patchqueue(spec, patches)


# Mercurial's guard logic is documented in:
#
#   O'Sullivan, B. "Mercurial: The Definitive Guide", Chapter 13 "Advanced
#   uses of Mercurial queues", in the section titled "MQ's rules for
#   applying patches"
#
#   http://hgbook.red-bean.com/read/advanced-uses-of-mercurial-queues.html


# The PatchQueue class currently only handles a single guard on each
# patch.   If support for multiple guards is added, the tests should
# check behaviour when a patch has positive and negative guards with
# the same label.   'hg qguard' won't create such a guard, but it can
# be added to the series file by hand and without extra constraints
# hypothesis will generate one.  Testing with hg shows that the positive
# guard overrides the negative one in this case: 'patch #+foo,-foo' is
# equivalent to 'patch #+foo".


class PatchqueueGuardTests(unittest.TestCase):
    """Test patchqueue series processing with guards"""

    @attr("pq")
    @given(tst.patchqueues(), tst.guard_names())
    def test_application_order(self, patchqueue, guard):
        """Patches are applied in patchqueue order"""
        series = patchqueue.series().splitlines(True)
        applied = list(planex.patchqueue.parse_patchseries(series, guard))
        # Filter unapplied patches out of the patchqueue, yielding a list
        # of applied patches in patchqueue order
        expected_inorder = [p.patch.name for p in patchqueue.patches
                            if p.patch.name in applied]
        self.assertEqual(applied, expected_inorder)

    @attr("pq")
    @given(tst.patchqueues(), tst.guard_names())
    def test_unguarded(self, patchqueue, guard):
        """Unguarded patches are always applied"""
        series = patchqueue.series().splitlines(True)
        applied = list(planex.patchqueue.parse_patchseries(series, guard))
        expected = [p.patch.name for p in patchqueue.patches if not p.guards]
        self.assertTrue(all([p in applied for p in expected]))

    @attr("pq")
    @given(tst.patchqueues(), tst.guard_names())
    def test_neg_guarded_apply(self, patchqueue, guard):
        """Negatively-guarded patches are applied if guard is not selected"""
        series = patchqueue.series().splitlines(True)
        applied = list(planex.patchqueue.parse_patchseries(series, guard))
        expected = [p.patch.name for p in patchqueue.patches
                    if p.has_negative_guards() and
                    tst.Guard('-', guard) not in p.guards]
        self.assertTrue(all([p in applied for p in expected]))

    @attr("pq")
    @given(tst.patchqueues(), tst.guard_names())
    def test_neg_guarded_skip(self, patchqueue, guard):
        """Negatively-guarded patches are skipped if guard is selected"""
        series = patchqueue.series().splitlines(True)
        applied = list(planex.patchqueue.parse_patchseries(series, guard))
        not_expected = [p.patch.name for p in patchqueue.patches
                        if tst.Guard('-', guard) in p.guards and
                        tst.Guard('+', guard) not in p.guards]
        self.assertTrue(all([p not in applied for p in not_expected]))

    @attr("pq")
    @given(tst.patchqueues(), tst.guard_names())
    def test_pos_guarded_apply(self, patchqueue, guard):
        """Positively guarded patches are applied if guard is selected"""
        series = patchqueue.series().splitlines(True)
        applied = list(planex.patchqueue.parse_patchseries(series, guard))
        expected = [p.patch.name for p in patchqueue.patches
                    if tst.Guard("+", guard) in p.guards]
        self.assertTrue(all([p in applied for p in expected]))

    @attr("pq")
    @given(tst.patchqueues(), tst.guard_names())
    def test_pos_guarded_skip(self, patchqueue, guard):
        """Positively-guarded patches are skipped if guard is not selected"""
        series = patchqueue.series().splitlines(True)
        applied = list(planex.patchqueue.parse_patchseries(series, guard))
        not_expected = [p.patch.name for p in patchqueue.patches
                        if p.has_positive_guards() and
                        tst.Guard('+', guard) not in p.guards]
        self.assertTrue(all([p not in applied for p in not_expected]))
