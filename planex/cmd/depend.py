"""
planex-depend: Generate Makefile-format dependencies from spec files
"""

import argparse
import glob
import os
import sys
import urlparse

import argcomplete
from planex.cmd.args import add_common_parser_options, rpm_macro
from planex.util import setup_sigint_handler
from planex.cmd import manifest
import planex.spec as pkg


def create_manifest_deps(spec):
    """
    Create depependencies for package manifest
    """
    prereqs = spec.specpath()
    spec_name = spec.name()
    lnk_path = 'SPECS/{}.lnk'.format(spec_name)

    if os.path.isfile(lnk_path):
        prereqs += ' ' + lnk_path

    print '{}: {}'.format(manifest.get_path(spec_name), prereqs)
    print '{}: {}'.format(spec.source_package_path(),
                          manifest.get_path(spec.name()))


def build_srpm_from_spec(spec, lnk=False):
    """
    Generate rules to build SRPM from spec
    """
    srpmpath = spec.source_package_path()
    print '%s: %s' % (srpmpath, spec.specpath())
    for (url, path) in zip(spec.source_urls(), spec.source_paths()):
        source = urlparse.urlparse(url)
        if source.scheme in ["http", "https", "file", "ftp"]:
            # Source was downloaded to _build/SOURCES
            print '%s: %s' % (srpmpath, path)
        elif not lnk:
            # Source is local
            print '%s: %s' % (srpmpath, "/".join(path.split("/")[1:]))


def download_rpm_sources(spec):
    """
    Generate rules to download sources
    """
    for (url, path) in zip(spec.source_urls(), spec.source_paths()):
        source = urlparse.urlparse(url)
        if source.scheme in ["http", "https", "file", "ftp"]:
            # Source can be fetched by fetch
            print '%s: %s' % (path, spec.specpath())


def build_rpm_from_srpm(spec):
    """
    Generate rules to build RPMS from SRPMS.
    Extracts binary package names from the spec file.
    """
    # We only generate a rule for the first binary RPM produced by the
    # specfile.  If we generate multiple rules (one for the base package,
    # one for -devel and so on), make will interpret these as completely
    # separate targets which must be built separately.   At best, this means
    # that the same package will be built more than once; at worst, in a
    # concurrent build, there is a risk that the targets might not be rebuilt
    # correctly.
    #
    # Make does understand the concept of multiple targets being built by
    # a single rule invocation, but only for pattern rules (e.g. %.h %.c: %.y).
    # It is tricky to generate correct pattern rules for RPM builds.

    rpm_path = spec.binary_package_paths()[-1]
    srpm_path = spec.source_package_path()
    print '%s: %s' % (rpm_path, srpm_path)


def package_to_rpm_map(specs):
    """
    Generate a mapping from RPM package names to the RPM files
    which provide them.
    """
    provides_to_rpm = {}
    for spec in specs:
        for provided in spec.provides():
            provides_to_rpm[provided] = spec.binary_package_paths()[-1]
    return provides_to_rpm


def buildrequires_for_rpm(spec, provides_to_rpm):
    """
    Generate build dependency rules between binary RPMs
    """
    rpmpath = spec.binary_package_paths()[-1]
    for buildreq in spec.buildrequires():
        # Some buildrequires come from the system repository
        if buildreq in provides_to_rpm:
            buildreqrpm = provides_to_rpm[buildreq]
            print "%s: %s" % (rpmpath, buildreqrpm)


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description="Generate Makefile dependencies from RPM Spec files")
    add_common_parser_options(parser)
    parser.add_argument("specs", metavar="SPEC", nargs="+", help="spec file")
    parser.add_argument(
        "--no-package-name-check", dest="check_package_names",
        action="store_false", default=True,
        help="Don't check that package name matches spec file name")
    parser.add_argument(
        "-D", "--define", default=[], action="append", type=rpm_macro,
        help="--define='MACRO EXPR' define MACRO with value EXPR")
    parser.add_argument(
        "-P", "--pins-dir", default="PINS",
        help="Directory containing pin overlays")
    parser.add_argument(
        "--no-buildrequires", dest="buildrequires",
        action="store_false", default=True,
        help="Don't generate dependency rules for BuildRequires")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def pkgname(path):
    """
    Return the name of the package at path
    """
    return os.path.splitext(os.path.basename(path))[0]


def main(argv=None):
    """
    Entry point
    """
    # pylint: disable=R0914

    setup_sigint_handler()
    args = parse_args_or_exit(argv)
    specs = {}

    print "# -*- makefile -*-"
    print "# vim:ft=make:"

    pins = []
    if args.pins_dir:
        pins_glob = os.path.join(args.pins_dir, "*.pin")
        pins = [pkgname(pin) for pin in glob.glob(pins_glob)]

    links = {pkgname(lnk): lnk for lnk in args.specs if lnk.endswith(".lnk")}

    for spec_path in [spec for spec in args.specs if spec.endswith(".spec")]:
        try:
            spec = pkg.Spec(spec_path,
                            check_package_name=args.check_package_names,
                            defines=args.define)
            spec_name = os.path.basename(spec_path)
            specs[spec_name] = spec

        except pkg.SpecNameMismatch as exn:
            sys.stderr.write("error: %s\n" % exn.message)
            sys.exit(1)

    provides_to_rpm = package_to_rpm_map(specs.values())

    for spec in specs.itervalues():
        build_srpm_from_spec(spec, (spec.name() in links))
        # Manifest dependencies must come after spec dependencies
        # otherwise manifest.json will be the SRPM's first dependency
        # and will be passed to rpmbuild in the spec position.
        create_manifest_deps(spec)
        if spec.name() in links or spec.name() in pins:
            srpmpath = spec.source_package_path()
            patchpath = spec.expand_macro("%_sourcedir/patches.tar")
            print '%s: %s' % (srpmpath, patchpath)
        if spec.name() in pins:
            pinpath = "%s/%s.pin" % (args.pins_dir, spec.name())
            print '%s: %s' % (srpmpath, pinpath)
        if spec.name() in links:
            linkpath = "SPECS/%s.lnk" % spec.name()
            print '%s: %s' % (srpmpath, linkpath)
        download_rpm_sources(spec)
        build_rpm_from_srpm(spec)
        if args.buildrequires:
            buildrequires_for_rpm(spec, provides_to_rpm)
        print ""

    # Generate targets to build all srpms and all rpms
    all_rpms = []
    all_srpms = []
    for spec in specs.itervalues():
        rpm_path = spec.binary_package_paths()[-1]
        all_rpms.append(rpm_path)
        all_srpms.append(spec.source_package_path())
        print "%s: %s" % (spec.name(), rpm_path)
        print "%s.srpm: %s" % (spec.name(), spec.source_package_path())
    print ""

    print "RPMS := " + " \\\n\t".join(all_rpms)
    print ""
    print "SRPMS := " + " \\\n\t".join(all_srpms)
