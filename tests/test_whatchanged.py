# Run these tests with 'nosetests':
#   install the 'python-nose' package (Fedora/CentOS or Ubuntu)
#   run 'nosetests' in the root of the repository

import glob
import os
import unittest

import sys
import mock

import planex.spec as pkg
from planex.cmd.whatchanged import find_changed, compute_changes, groupbykey,\
    compute_srpm_changes, update_reverse_dependencies


SRPM_TESTS = {
    'a/ocaml-uri-1.6.0-1.el6.src.rpm': ['A', 'B'],
    'b/ocaml-uri-1.6.0-1.el6.src.rpm': ['A', 'B'],
    'a/ocaml-cohttp-0.9.8-1.el6.src.rpm': ['A', 'B'],
    'b/ocaml-cohttp-0.9.8-1.el6.src.rpm': ['A', 'C'],
    'a/ocaml-cstruct-1.4.0-1.el6.src.rpm': ['A', 'B'],
    'b/ocaml-cstruct-1.4.0-1.el6.src.rpm': ['A', 'B', 'C'],
}


def digests_mock(rpm):
    return SRPM_TESTS[rpm]


class BasicTests(unittest.TestCase):
    # unittest.TestCase has more methods than Pylint permits
    # pylint: disable=R0904
    def setUp(self):
        rpm_defines = [("dist", ".el6"),
                       ("_topdir", "_build"),
                       ("_sourcedir", "%_topdir/SOURCES/%name")]
        spec_paths = glob.glob(os.path.join("tests/data", "ocaml-*.spec"))
        self.specs = {spec.name(): spec for spec in
                      [pkg.Spec(spec_path, defines=rpm_defines)
                       for spec_path in spec_paths
                       if spec_path.endswith(".spec")]}
        self.pkgs = {
            'ocaml-cohttp-devel': (None, '0.9.8', '1.el6'),
            'ocaml-cohttp': (None, '0.9.8', '1.el6'),
            'ocaml-cstruct-devel': (None, '1.4.0', '1.el6'),
            'ocaml-cstruct': (None, '1.4.0', '1.el6'),
            'ocaml-uri-devel': (None, '1.6.0', '1.el6'),
            'ocaml-uri': (None, '1.6.0', '1.el6')
        }
        self.new_pkgs = self.pkgs.copy()
        self.new_pkgs.update({
            'ocaml-uri': (None, '1.6.1', '1.el6'),
            'ocaml-cstruct': (None, '1.4.0', '2.el6')
        })

    def test_find_no_changes(self):
        self.assertEqual(
            find_changed(self.pkgs, self.pkgs, True),
            [])

    def test_find_changes(self):
        self.assertEqual(
            find_changed(self.new_pkgs, self.pkgs, True),
            ['ocaml-uri', 'ocaml-cstruct'])

    def test_no_downgrades(self):
        with self.assertRaises(Exception):
            find_changed(self.pkgs, self.new_pkgs, True)

    def test_downgrades(self):
        self.assertEqual(
            find_changed(self.pkgs, self.new_pkgs, False),
            ['ocaml-uri', 'ocaml-cstruct'])

    @mock.patch('planex.cmd.whatchanged.get_repo_versions')
    def test_all(self, get_repo_versions):
        get_repo_versions.return_value = {
            'ocaml-uri': (None, '1.5.9', '1.el6')
        }
        self.assertEqual(compute_changes(self.specs, True),
                         set(['ocaml-uri']))

    def test_groupby(self):
        pkgs = ['a/pkg1-0.1', 'b/pkg0-0.2', 'c/pkg1-0.1',
                'd/pkg2-0.3', 'd/pkg2-0.4']
        result = {
            base: list(lst)
            for (base, lst) in groupbykey(pkgs, os.path.basename)
        }
        self.assertEqual(result,
                         {'pkg1-0.1': ['a/pkg1-0.1', 'c/pkg1-0.1'],
                          'pkg0-0.2': ['b/pkg0-0.2'],
                          'pkg2-0.3': ['d/pkg2-0.3'],
                          'pkg2-0.4': ['d/pkg2-0.4']})

    @mock.patch('planex.cmd.whatchanged.digests_of_rpm', new=digests_mock)
    def test_srpm_changes(self):
        changed_specs = set()
        compute_srpm_changes(SRPM_TESTS.keys(), self.specs, changed_specs)
        self.assertEqual(changed_specs,
                         set(['ocaml-cohttp', 'ocaml-cstruct']))

    def test_revdeps_noop(self):
        changed_specs = set(self.specs.keys())
        orig_changed_specs = changed_specs
        update_reverse_dependencies(self.specs, changed_specs, True)
        self.assertEqual(changed_specs, orig_changed_specs)

    def test_revdeps_strict(self):
        changed_specs = set(['ocaml-cstruct'])
        with self.assertRaises(Exception):
            update_reverse_dependencies(self.specs, changed_specs, True)

    def test_revdeps_update(self):
        changed_specs = set(['ocaml-cstruct'])
        orig_changed_specs = changed_specs
        update_reverse_dependencies(self.specs, changed_specs, False)
        self.assertEqual(changed_specs, set(['ocaml-cohttp', 'ocaml-cstruct']))
