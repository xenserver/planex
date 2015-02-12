# Run these tests with 'nosetests':
#   install the 'python-nose' package (Fedora/CentOS or Ubuntu)
#   run 'nosetests' in the root of the repository

import unittest
import os
from mock import patch
import subprocess
import tempfile
import shutil

import planex
from planex import configure
from planex import sources

DATADIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def path_to(fname):
    return os.path.join(DATADIR, fname)


class BasicTests(unittest.TestCase):
    def setUp(self):
        # 'setUp' breaks Pylint's naming rules
        # pylint: disable=C0103
        self.config = configure.parse_cmdline(['config_dir'])
        self.cohttp_url = "https://github.com/mirage/ocaml-cohttp" \
            "/archive/ocaml-cohttp-0.9.8/ocaml-cohttp-0.9.8.tar.gz"

    def test_name_from_spec(self):
        res = configure.name_from_spec("tests/data/ocaml-cohttp.spec")
        self.assertEqual(res, "ocaml-cohttp")

    def test_check_spec_name(self):
        # check_spec_name does not exit if the name is correct
        configure.check_spec_name("tests/data/ocaml-cohttp.spec")

    def test_check_spec_name_fail(self):
        # check_spec_name exits if the name is not correct
        # self.assertRaises(SystemExit, configure.check_spec_name(
        # "tests/data/bad-name.spec")) should work, but doesn't
        try:
            configure.check_spec_name("tests/data/bad-name.spec")
            self.fail()
        except SystemExit:
            pass

    def test_sources_from_spec(self):
        res = configure.sources_from_spec(path_to("ocaml-cohttp.spec"))
        self.assertEqual(res,
                         [self.cohttp_url,
                          "file:///code/ocaml-cohttp-extra#" +
                          "ocaml-cohttp-extra-0.9.8.tar.gz",
                          "ocaml-cohttp-init"])

    def test_preprocess_spec(self):
        working_dir = tempfile.mkdtemp()
        mapping = {"https://github.com/mirage/%{name}/archive/"
                   "%{name}-%{version}/%{name}-%{version}.tar.gz":
                   "foo.tar.gz"}
        source = sources.SCM("git://github.com/foo/bar.git#somebranch",
                             self.config)
        source.set_hash_and_vsn("abcde", "1.2.3")
        configure.preprocess_spec(path_to("ocaml-cohttp.spec.in"),
                                  working_dir, [source], mapping)
        spec = planex.spec.Spec(os.path.join(working_dir, "ocaml-cohttp.spec"))
        self.assertEqual(spec.version(), "1.2.3")
        self.assertEqual(spec.source_urls(), ["foo.tar.gz"])
