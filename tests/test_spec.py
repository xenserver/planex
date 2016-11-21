# Run these tests with 'nosetests':
#   install the 'python-nose' package (Fedora/CentOS or Ubuntu)
#   run 'nosetests' in the root of the repository

import unittest
import platform
import planex.spec


def get_rpm_machine():
    if platform.machine() == 'x86_64':
        return 'x86_64'
    return 'i386'


class RpmTests(unittest.TestCase):
    # unittest.TestCase has more methods than Pylint permits
    # pylint: disable=R0904

    def setUp(self):
        rpm_defines = [("dist", ".el6"),
                       ("_topdir", "."),
                       ("_sourcedir", "%_topdir/SOURCES/%name")]
        self.spec = planex.spec.Spec("tests/data/ocaml-cohttp.spec",
                                     defines=rpm_defines)

    def test_bad_filename(self):
        self.assertRaises(planex.spec.SpecNameMismatch, planex.spec.Spec,
                          "tests/data/bad-name.spec")

    def test_name(self):
        self.assertEqual(self.spec.name(), "ocaml-cohttp")

    def test_specpath(self):
        self.assertEqual(self.spec.specpath(), "tests/data/ocaml-cohttp.spec")

    def test_version(self):
        self.assertEqual(self.spec.version(), "0.9.8")

    def test_provides(self):
        self.assertEqual(
            self.spec.provides(),
            set(["ocaml-cohttp", "ocaml-cohttp-devel"]))

    def test_source_urls(self):
        self.assertEqual(
            set(self.spec.source_urls()),
            set(["https://github.com/mirage/ocaml-cohttp/archive/"
                 "ocaml-cohttp-0.9.8/ocaml-cohttp-0.9.8.tar.gz",
                 "ocaml-cohttp-init",
                 "ocaml-cohttp-service",
                 "cohttp0.patch",
                 "cohttp1.patch"]))

    def test_source_paths(self):
        self.assertEqual(
            set(self.spec.source_paths()),
            set(["./SOURCES/ocaml-cohttp/ocaml-cohttp-0.9.8.tar.gz",
                 "./SOURCES/ocaml-cohttp/ocaml-cohttp-init",
                 "./SOURCES/ocaml-cohttp/ocaml-cohttp-service",
                 "./SOURCES/ocaml-cohttp/cohttp0.patch",
                 "./SOURCES/ocaml-cohttp/cohttp1.patch"]))

    def test_buildrequires(self):
        self.assertEqual(
            self.spec.buildrequires(),
            set(["ocaml", "ocaml-findlib", "ocaml-re-devel",
                 "ocaml-uri-devel", "ocaml-cstruct-devel",
                 "ocaml-lwt-devel", "ocaml-ounit-devel",
                 "ocaml-ocamldoc", "ocaml-camlp4-devel",
                 "openssl", "openssl-devel"]))

    def test_source_package_path(self):
        self.assertEqual(
            self.spec.source_package_path(),
            "./SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm")

    def test_binary_package_paths(self):
        machine = get_rpm_machine()

        self.assertEqual(
            sorted(self.spec.binary_package_paths()),
            [
                path.format(machine=machine) for path in
                sorted([
                    "./RPMS/{machine}/ocaml-cohttp-0.9.8-1.el6.{machine}.rpm",
                    "./RPMS/{machine}/" +
                    "ocaml-cohttp-devel-0.9.8-1.el6.{machine}.rpm"])
            ]
        )
