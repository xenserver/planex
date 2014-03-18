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

DATADIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def path_to(fname):
    return os.path.join(DATADIR, fname)


class BasicTests(unittest.TestCase):
    def setUp(self):
        # 'setUp' breaks Pylint's naming rules
        # pylint: disable=C0103
        self.cohttp_url = "https://github.com/mirage/ocaml-cohttp" \
            "/archive/ocaml-cohttp-0.9.8/ocaml-cohttp-0.9.8.tar.gz"


    def test_rewrite_to_distfiles(self):
        url = "http://github.com/xenserver/planex"
        res = configure.rewrite_to_distfiles(url)
        self.assertEqual(res,  "file:///distfiles/ocaml2/planex")


    # Decorators are applied bottom up
    @patch('os.path.exists')
    @patch('planex.configure.call') # configure adds subprocess.call to its namespace
    def test_fetch_url(self, mock_subprocess_call, mock_os_path_exists):
        mock_os_path_exists.return_value = False
        mock_subprocess_call.return_value = 0
        configure.fetch_url(self.cohttp_url)
        assert mock_os_path_exists.called
        mock_subprocess_call.assert_called_with(["curl", "-k", "-L", "-o",
            "planex-build-root/SOURCES/ocaml-cohttp-0.9.8.tar.gz",
            self.cohttp_url])


    @patch('os.path.exists')
    @patch('planex.configure.call')
    def test_fetch_url_existing_file(self, mock_subprocess_call,
                                     mock_os_path_exists):
        mock_os_path_exists.return_value = True
        mock_subprocess_call.return_value = 0
        configure.fetch_url(self.cohttp_url)
        mock_os_path_exists.assert_called_with(
            "planex-build-root/SOURCES/ocaml-cohttp-0.9.8.tar.gz")
        assert not mock_subprocess_call.called


    @patch('os.path.exists')
    @patch('planex.configure.call')
    def test_fetch_url_with_rewrite(self, mock_subprocess_call,
                                    mock_os_path_exists):
        def rewrite(_url):
            return "http://rewritten.com/file.tar.gz"

        mock_os_path_exists.return_value = False
        mock_subprocess_call.return_value = 0
        configure.fetch_url(self.cohttp_url, rewrite=rewrite)
        mock_os_path_exists.assert_called_with(
            "planex-build-root/SOURCES/file.tar.gz")
        mock_subprocess_call.assert_called_with(["curl", "-k", "-L", "-o",
            "planex-build-root/SOURCES/file.tar.gz",
            "http://rewritten.com/file.tar.gz"])


    def test_make_extended_git_url(self):
        base_url = "https://github.com/xenserver/planex"
        extended_url = "https://github.com/xenserver/planex#1.0.0/" \
                       "planex-1.0.0.tar.gz"
        res = configure.make_extended_git_url(base_url, "1.0.0")
        self.assertEqual(res, extended_url)


    # We don't handle 'v1.0.0'

    def test_parse_extended_git_url(self):
        url = "git://github.com/xenserver/planex#1.0.0/" \
              "%{name}-%{version}.tar.gz"
        res = configure.parse_extended_git_url(url)
        expected = ("git", "github.com", "/xenserver/planex", "1.0.0",
                    "%{name}-%{version}.tar.gz")
        self.assertEqual(res, expected)


    def test_roundtrip_extended_git_url(self):
        base_url = "git://github.com/xenserver/planex"
        url = configure.make_extended_git_url(base_url, "1.0.0")
        res = configure.parse_extended_git_url(url)
        expected = ("git", "github.com", "/xenserver/planex", "1.0.0",
                    "planex-1.0.0.tar.gz")
        self.assertEqual(res, expected)


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
             "file:///code/ocaml-cohttp-extra#ocaml-cohttp-extra-0.9.8.tar.gz",
             "ocaml-cohttp-init"])


    @patch('planex.configure.fetch_url')
    @patch('planex.configure.sources_from_spec')
    def test_prepare_srpm_http(self, mock_sources, mock_fetch):
        """Test downloading a single 'normal' source URL"""
        urls = ["http://test.com/foo#1.0.0/foo-1.0.0.tar.gz"]

        mock_sources.return_value = urls
        mock_fetch.return_value = 1

        res = configure.prepare_srpm(path_to("ocaml-cohttp.spec"), 
                                     use_distfiles=False)

        mock_sources.assert_called_with(path_to("ocaml-cohttp.spec"))
        mock_fetch.assert_called_with(urls[0], None)
    
        self.assertEqual(res, (1, 0))
        

    @patch('planex.configure.fetch_git_source')
    @patch('planex.configure.fetch_url')
    @patch('planex.configure.sources_from_spec')
    def test_prepare_srpm_git(self, mock_sources, mock_fetch, mock_fetch_git):
        """Test downloading a single GitHub-like git source URL"""
        urls = ["git://test.com/foo#1.0.0/foo-1.0.0.tar.gz"]

        mock_sources.return_value = urls
        mock_fetch.return_value = 1

        res = configure.prepare_srpm(path_to("ocaml-cohttp.spec"), 
                                     use_distfiles=False)

        mock_sources.assert_called_with(path_to("ocaml-cohttp.spec"))
        self.assertFalse(mock_fetch.called)
        mock_fetch_git.assert_called_with(urls[0])
    
        self.assertEqual(res, (1, 0))


    def test_preprocess_spec(self):
        working_dir = tempfile.mkdtemp()
        mapping = {"https://github.com/mirage/%{name}/archive/"
                   "%{name}-%{version}/%{name}-%{version}.tar.gz": "foo.tar.gz"}
        configure.preprocess_spec(path_to("ocaml-cohttp.spec.in"),
                                  working_dir, ["1.2.3"], mapping)
        spec = planex.spec.Spec(os.path.join(working_dir, "ocaml-cohttp.spec"))
        self.assertEqual(spec.version(), "1.2.3")
        self.assertEqual(spec.source_urls(), ["foo.tar.gz"])


class GitTests(unittest.TestCase):
    def setUp(self):
        # 'setUp' breaks Pylint's naming rules
        # pylint: disable=C0103
        self.working_dir = tempfile.mkdtemp()
        self.sources_dir = os.path.join(self.working_dir, "SOURCES")
        os.mkdir(self.sources_dir)
        subprocess.call(["tar", "zxf", "tests/data/test-git.tar.gz", 
                         "-C", self.working_dir])


    def tearDown(self):
        # 'tearDown' breaks Pylint's naming rules
        # pylint: disable=C0103
        shutil.rmtree(self.working_dir)
	

    def test_locate_repo(self):
        res = configure.locate_repo("test.git", myrepos=self.working_dir)
        self.assertEqual(res, os.path.join(self.working_dir, "test.git"))


    def test_latest_git_tag(self):
        res = configure.latest_git_tag("git://host.com/test.git", 
                                       myrepos=self.working_dir)
        self.assertEqual(res, "1.1.0")


    def test_fetch_git_source(self):
        configure.fetch_git_source("git://host.com/test.git#"
                                       "1.1.0/test-1.1.0.tar.gz", 
                                   myrepos=self.working_dir,
                                   sources_dir=self.sources_dir)
        expected_tarball = os.path.join(self.sources_dir, "test-1.1.0.tar.gz")
        self.assertTrue(os.path.exists(expected_tarball))
