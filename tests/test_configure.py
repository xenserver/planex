# Run these tests with 'nosetests':
#   install the 'python-nose' package (Fedora/CentOS or Ubuntu)
#   run 'nosetests' in the root of the repository

from cStringIO import StringIO
import glob
import os
import sys
import unittest

import configure

class BasicTests(unittest.TestCase):
    def test_rewrite_to_distfiles(self):
        res = configure.rewrite_to_distfiles("http://github.com/xenserver/planex") 
	assert res == "file:///distfiles/ocaml2/planex"

    def test_make_extended_git_url(self):
	base_url = "https://github.com/xenserver/planex"
        res = configure.make_extended_git_url(base_url, "1.0.0")
	assert res == "https://github.com/xenserver/planex#1.0.0/%{name}-%{version}.tar.gz"

    # We don't handle 'v1.0.0'

    def test_parse_extended_git_url(self):
	url = "git://github.com/xenserver/planex#1.0.0/%{name}-%{version}.tar.gz"
        res = configure.parse_extended_git_url(url)
	assert res == ("git", "github.com", "/xenserver/planex", "1.0.0", 
                       "%{name}-%{version}.tar.gz")
    
    def test_make_and_parse_extended_git_url(self):
	base_url = "git://github.com/xenserver/planex"
        url = configure.make_extended_git_url(base_url, "1.0.0")
        res = configure.parse_extended_git_url(url)
	assert res == ("git", "github.com", "/xenserver/planex", "1.0.0", 
                       "%{name}-%{version}.tar.gz")
    
    def test_name_from_spec(self):
        res = configure.name_from_spec("tests/data/ocaml-cohttp.spec")
        assert res == "ocaml-cohttp"

    def test_check_spec_name(self):
	# check_spec_name does not exit if the name is correct
        configure.check_spec_name("tests/data/ocaml-cohttp.spec")

    def test_check_spec_name_fail(self):
	# check_spec_name exits if the name is not correct
        # self.assertRaises(SystemExit, configure.check_spec_name("tests/data/bad-name.spec"))
        try:
           configure.check_spec_name("tests/data/bad-name.spec")
           self.fail()
        except SystemExit:
           pass

    def test_sources_from_spec(self):
	res = configure.sources_from_spec("tests/data/ocaml-cohttp.spec")
        assert sorted(res) == sorted(["https://github.com/mirage/ocaml-cohttp/archive/ocaml-cohttp-0.9.8/ocaml-cohttp-0.9.8.tar.gz"])

