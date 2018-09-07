"""Tests for Spec class"""

import unittest
import platform
import planex.spec
from planex.spec import Blob, Archive, Patchqueue


def get_rpm_machine():
    """Return the RPM architecture name for the local machine"""
    if platform.machine() == 'x86_64':
        return 'x86_64'
    return 'i386'


RPM_DEFINES = [("dist", ".el6"),
               ("_topdir", "."),
               ("_sourcedir", "%_topdir/SOURCES/%name")]


class RpmTests(unittest.TestCase):
    """Basic Spec class tests"""

    def setUp(self):
        self.spec = planex.spec.Spec("tests/data/ocaml-cohttp.spec",
                                     defines=RPM_DEFINES)

    def test_bad_filename(self):
        """Exception is raised if filenname does not match package name"""
        self.assertRaises(planex.spec.SpecNameMismatch, planex.spec.Spec,
                          "tests/data/bad-name.spec")

    def test_name(self):
        """Package name is correct"""
        self.assertEqual(self.spec.name(), "ocaml-cohttp")

    def test_specpath(self):
        """Path to spec file on disk is correct"""
        self.assertEqual(self.spec.specpath(), "tests/data/ocaml-cohttp.spec")

    def test_version(self):
        """Package version is correct"""
        self.assertEqual(self.spec.version(), "0.9.8")

    def test_provides(self):
        """Package provides are correct"""
        self.assertItemsEqual(
            self.spec.provides(),
            ["ocaml-cohttp", "ocaml-cohttp-devel"])

    def test_sources(self):
        """Package source paths and URLs are correct"""
        self.assertItemsEqual(
            self.spec.sources(),
            [("./SOURCES/ocaml-cohttp/ocaml-cohttp-0.9.8.tar.gz",
              "https://github.com/mirage/ocaml-cohttp/archive/"
              "ocaml-cohttp-0.9.8/ocaml-cohttp-0.9.8.tar.gz"),
             ("./SOURCES/ocaml-cohttp/ocaml-cohttp-init",
              "SOURCES/ocaml-cohttp-init"),
             ("./SOURCES/ocaml-cohttp/ocaml-cohttp-service",
              "SOURCES/ocaml-cohttp-service"),
             ("./SOURCES/ocaml-cohttp/cohttp0.patch",
              "SOURCES/cohttp0.patch"),
             ("./SOURCES/ocaml-cohttp/cohttp1.patch",
              "SOURCES/cohttp1.patch")])

    def test_requires(self):
        """Package runtime requirements are correct"""
        self.assertEqual(
            self.spec.requires(),
            set(["ocaml", "ocaml-findlib"]))

    def test_buildrequires(self):
        """Package build-time requirements are correct"""
        self.assertEqual(
            self.spec.buildrequires(),
            set(["ocaml", "ocaml-findlib", "ocaml-re-devel",
                 "ocaml-uri-devel", "ocaml-cstruct-devel",
                 "ocaml-lwt-devel", "ocaml-ounit-devel",
                 "ocaml-ocamldoc", "ocaml-camlp4-devel",
                 "openssl", "openssl-devel"]))

    def test_source_package_path(self):
        """Path to resulting source RPM is correct"""
        self.assertEqual(
            self.spec.source_package_path(),
            "./SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm")

    def test_binary_package_paths(self):
        """Paths to resulting binary RPMs are correct"""
        machine = get_rpm_machine()

        self.assertItemsEqual(
            self.spec.binary_package_paths(),
            [path.format(machine=machine) for path in
             ["./RPMS/{machine}/ocaml-cohttp-0.9.8-1.el6.{machine}.rpm",
              "./RPMS/{machine}/" +
              "ocaml-cohttp-devel-0.9.8-1.el6.{machine}.rpm"]]
        )

    def test_resources(self):
        """Package source paths and URLs are correct"""
        self.assertEqual(
            self.spec.resources(),
            [Blob(self.spec,
                  "https://github.com/mirage/ocaml-cohttp/archive/"
                  "ocaml-cohttp-0.9.8/ocaml-cohttp-0.9.8.tar.gz",
                  "tests/data/ocaml-cohttp.spec"),
             Blob(self.spec, "SOURCES/ocaml-cohttp-init",
                  "tests/data/ocaml-cohttp.spec"),
             Blob(self.spec, "SOURCES/ocaml-cohttp-service",
                  "tests/data/ocaml-cohttp.spec"),
             Blob(self.spec, "SOURCES/cohttp0.patch",
                  "tests/data/ocaml-cohttp.spec"),
             Blob(self.spec, "SOURCES/cohttp1.patch",
                  "tests/data/ocaml-cohttp.spec")])

    def test_resources_override(self):
        """Package source paths and URLs are correct"""
        self.spec.add_source(0, Blob(self.spec, "http://elsewhere", "link1"))
        self.spec.add_source(3, Blob(self.spec, "http://additional", "link2"))
        self.spec.add_patch(1, Blob(self.spec, "http://a.n.other", "link3"))
        self.spec.add_patch(3, Blob(self.spec, "http://extra", "link4"))
        self.assertEqual(
            self.spec.resources(),
            [Blob(self.spec, "http://elsewhere", "link1"),
             Blob(self.spec, "SOURCES/ocaml-cohttp-init",
                  "tests/data/ocaml-cohttp.spec"),
             Blob(self.spec, "SOURCES/ocaml-cohttp-service",
                  "tests/data/ocaml-cohttp.spec"),
             Blob(self.spec, "http://additional", "link2"),
             Blob(self.spec, "SOURCES/cohttp0.patch",
                  "tests/data/ocaml-cohttp.spec"),
             Blob(self.spec, "http://a.n.other", "link3"),
             Blob(self.spec, "http://extra", "link4")])

    def test_resources_extras(self):
        """Package source paths and URLs are correct"""
        self.spec.add_archive(0, Archive(self.spec, "http://foo/patches.tar",
                                         "link1", "SOURCES/"))
        self.spec.add_patchqueue(0, Patchqueue(self.spec,
                                               "http://foo/patchqueue.tar",
                                               "link1", "PATCHES/"))
        self.assertEqual(
            self.spec.resources(),
            [Blob(self.spec,
                  "https://github.com/mirage/ocaml-cohttp/archive/"
                  "ocaml-cohttp-0.9.8/ocaml-cohttp-0.9.8.tar.gz",
                  "tests/data/ocaml-cohttp.spec"),
             Blob(self.spec, "SOURCES/ocaml-cohttp-init",
                  "tests/data/ocaml-cohttp.spec"),
             Blob(self.spec, "SOURCES/ocaml-cohttp-service",
                  "tests/data/ocaml-cohttp.spec"),
             Blob(self.spec, "SOURCES/cohttp0.patch",
                  "tests/data/ocaml-cohttp.spec"),
             Blob(self.spec, "SOURCES/cohttp1.patch",
                  "tests/data/ocaml-cohttp.spec"),
             Archive(self.spec, "http://foo/patches.tar", "link1",
                     "SOURCES/"),
             Patchqueue(self.spec, "http://foo/patchqueue.tar",
                        "link1", "PATCHES/")])

    def test_resource(self):
        """URLs for individual resources are correct"""
        self.assertEqual(
            self.spec.resource("path/to/ocaml-cohttp-0.9.8.tar.gz"),
            Blob(self.spec,
                 "https://github.com/mirage/ocaml-cohttp/archive/"
                 "ocaml-cohttp-0.9.8/ocaml-cohttp-0.9.8.tar.gz",
                 "tests/data/ocaml-cohttp.spec"))
        self.assertEqual(
            self.spec.resource("ocaml-cohttp-init"),
            Blob(self.spec, "SOURCES/ocaml-cohttp-init",
                 "tests/data/ocaml-cohttp.spec"))
        self.assertEqual(
            self.spec.resource("somewhere/cohttp0.patch"),
            Blob(self.spec, "SOURCES/cohttp0.patch",
                 "tests/data/ocaml-cohttp.spec"))
        self.spec.add_archive(0, Archive(self.spec, "http://foo/patches.tar",
                                         "link1", "SOURCES/"))
        self.assertEqual(
            self.spec.resource("somewhere/patches.tar"),
            Archive(self.spec, "http://foo/patches.tar", "link1",
                    "SOURCES/"))

    def test_resource_nonexistent(self):
        """Nonexistent sources are handled correctly"""
        with self.assertRaises(KeyError):
            self.spec.resource("nonexistent")


class RpmSourceNameParsingTest(unittest.TestCase):
    """Further Spec class tests"""

    def test_source_replaces_source0(self):
        """A link with a Source entry is parsed into Source0"""
        link = planex.link.Link("tests/data/ocaml-cstruct.lnk")
        spec = planex.spec.load("tests/data/ocaml-cstruct.spec", link=link,
                                defines=RPM_DEFINES)

        self.assertEqual(
            spec.resources(),
            [Blob(spec, "tests/data/test-git.tar.gz",
                  "tests/data/ocaml-cstruct.lnk")]
        )

    def test_spec_not_rewritten(self):
        """Spec files with no patches or sources should not be rewritten"""
        spec = planex.spec.load("tests/data/empty.spec", link=None,
                                defines=RPM_DEFINES)
        self.assertEqual(
            spec.spectext,
            spec.rewrite_spec()
        )
