"""Tests for dependency generation"""

import glob
import os
import sys
import unittest

import planex.spec
import planex.cmd.depend


class BasicTests(unittest.TestCase):
    """Basic dependency generation tests"""
    def setUp(self):
        rpm_defines = [("dist", ".el6"),
                       ("_topdir", "_build"),
                       ("_sourcedir", "%_topdir/SOURCES/%name")]
        self.spec = planex.spec.Spec("tests/data/ocaml-cohttp.spec",
                                     defines=rpm_defines)

    def test_build_srpm_from_spec(self):
        """Dependency rules to pack sources into source RPMs"""
        # This should be a library method which doesn't write to stdout
        planex.cmd.depend.build_srpm_from_spec(self.spec)

        # Nose adds sys.stdout.getvalue() dynamically.
        # pylint: disable=E1101
        self.assertEqual(
            sys.stdout.getvalue(),
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm: "
            "tests/data/ocaml-cohttp.spec\n"
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm: "
            "./MANIFESTS/ocaml-cohttp.json\n"
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm: "
            "_build/SOURCES/ocaml-cohttp/ocaml-cohttp-0.9.8.tar.gz\n"
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm: "
            "SOURCES/ocaml-cohttp/ocaml-cohttp-init\n"
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm: "
            "SOURCES/ocaml-cohttp/ocaml-cohttp-service\n"
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm: "
            "SOURCES/ocaml-cohttp/cohttp0.patch\n"
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm: "
            "SOURCES/ocaml-cohttp/cohttp1.patch\n")

    def test_download_rpm_sources(self):
        """Dependency rules to download non-local sources"""
        # This should be a library method which doesn't write to stdout
        planex.cmd.depend.download_rpm_sources(self.spec)

        # pylint: disable=E1101
        self.assertEqual(
            sys.stdout.getvalue(),
            "_build/SOURCES/ocaml-cohttp/ocaml-cohttp-0.9.8.tar.gz: "
            "tests/data/ocaml-cohttp.spec\n")

    def test_build_rpm_from_srpm(self):
        """Dependency rules to build binary RPMs from source RPMs"""
        # This should be a library method which doesn't write to stdout
        planex.cmd.depend.build_rpm_from_srpm(self.spec)

        # pylint: disable=E1101
        self.assertEqual(
            sys.stdout.getvalue(),
            "_build/RPMS/x86_64/ocaml-cohttp-devel-0.9.8-1.el6.x86_64.rpm: "
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm\n")

    def test_buildrequires_for_rpm(self):
        """Dependency rules for build-time dependencies between binary RPMs"""
        # N.B. buildrequires_for_rpm only generates rules for other packages
        # defined by local spec files.   Even though ocaml-cohttp depends on
        # other packages, the test data directory contains only ocaml-uri and
        # ocaml-cstruct.
        spec_paths = glob.glob(os.path.join("tests/data", "ocaml-*.spec"))
        specs = [planex.spec.Spec(spec_path, defines=[('dist', '.el6')])
                 for spec_path in spec_paths]

        # This should be a library method which doesn't write to stdout
        planex.cmd.depend.buildrequires_for_rpm(
            self.spec, planex.cmd.depend.package_to_rpm_map(specs))

        # pylint: disable=E1101
        self.assertEqual(
            sys.stdout.getvalue(),
            "_build/RPMS/x86_64/ocaml-cohttp-devel-0.9.8-1.el6.x86_64.rpm: "
            "_build/RPMS/x86_64/ocaml-uri-devel-1.6.0-1.el6.x86_64.rpm\n"
            "_build/RPMS/x86_64/ocaml-cohttp-devel-0.9.8-1.el6.x86_64.rpm: "
            "_build/RPMS/x86_64/ocaml-cstruct-devel-1.4.0-1.el6.x86_64.rpm\n")
