"""
planex-depend: Generate Makefile-format dependencies from spec files
"""
from __future__ import print_function

import argparse
import os
import re
import sys
import urlparse

import argcomplete
from planex.cmd.args import common_base_parser, rpm_define_parser
from planex.util import setup_sigint_handler, dedupe
from planex.cmd import manifest
from planex.spec import load, SpecNameMismatch
from planex.link import Link


def create_manifest_deps(spec):
    """
    Create depependencies for package manifest
    """
    prereqs = spec.specpath()
    spec_name = spec.name()
    lnk_path = 'SPECS/{}.lnk'.format(spec_name)

    if os.path.isfile(lnk_path):
        prereqs += ' ' + lnk_path

    print('{}: {}'.format(manifest.get_path(spec_name), prereqs))
    print('{}: {}'.format(spec.source_package_path(),
                          manifest.get_path(spec.name())))


def build_srpm_from_spec(spec, lnk=None):
    """
    Generate rules to build SRPM from spec
    """
    # All packages must depend on a spec file, and it must be the first
    # dependency listed
    srpmpath = spec.source_package_path()
    print('%s: %s' % (srpmpath, spec.specpath()))

    # The package may also depend on one or more link files
    nonspec_deps = {r.defined_by for r in spec.resources()} - {spec.specpath()}
    for dep in nonspec_deps:
        print('%s: %s' % (srpmpath, dep))

    for resource in spec.resources():
        if resource.is_remote:
            # Source was downloaded to _build/SOURCES
            print('%s: %s' % (srpmpath, resource.path))
        elif lnk and (lnk.sources is not None or lnk.has_patches):
            # Use sources from patchqueue
            pass
        else:
            # Source is local
            print('%s: %s' % (srpmpath,
                              "/".join(resource.path.split("/")[1:])))


def download_rpm_sources(spec):
    """
    Generate rules to download sources
    """
    for resource in spec.resources():
        if resource.is_remote:
            print("%s: %s" % (resource.path, resource.defined_by))


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
    print('%s: %s' % (rpm_path, srpm_path))


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
    # Package's Requires must exist for it to be installed as a
    # BuildRequire of a later package, so we make it depend on
    # Requires as well as BuildRequires to ensure they are built.
    buildreqs = (spec.buildrequires() | spec.requires()) - spec.provides()
    for buildreq in buildreqs:
        # Some buildrequires come from the system repository
        if buildreq in provides_to_rpm:
            buildreqrpm = provides_to_rpm[buildreq]
            print("%s: %s" % (rpmpath, buildreqrpm))


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description="Generate Makefile dependencies from RPM Spec files",
        parents=[common_base_parser(), rpm_define_parser()])
    parser.add_argument("specs", metavar="SPEC", nargs="+", help="spec file")
    parser.add_argument(
        "--no-package-name-check", dest="check_package_names",
        action="store_false", default=True,
        help="Don't check that package name matches spec file name")
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


def dedupe_key(path):
    """
    Return the key of path for deduplication.
    Filnames are stripped of their paths, and .pin files are equivalent
    to .lnk files.
    """
    return os.path.basename(re.sub(r"\.pin$", ".lnk", path))


def main(argv=None):
    """
    Entry point
    """
    setup_sigint_handler()
    args = parse_args_or_exit(argv)
    allspecs = dedupe(args.specs, dedupe_key)

    links = {pkgname(path): Link(path)
             for path in allspecs
             if path.endswith(".lnk") or path.endswith(".pin")}

    try:
        specs = {pkgname(path): load(path, link=links.get(pkgname(path)),
                                     defines=args.define)
                 for path in allspecs
                 if path.endswith(".spec")}
    except SpecNameMismatch as exn:
        sys.stderr.write("error: %s\n" % exn.message)
        sys.exit(1)

    provides_to_rpm = package_to_rpm_map(specs.values())

    print("# -*- makefile -*-")
    print("# vim:ft=make:")
    if args.verbose:
        print("# inputs: %s" % " ".join(allspecs))

    for spec in specs.itervalues():
        print('# %s' % (spec.name()))

        build_srpm_from_spec(spec, links.get(spec.name()))
        # Manifest dependencies must come after spec dependencies
        # otherwise manifest.json will be the SRPM's first dependency
        # and will be passed to rpmbuild in the spec position.
        create_manifest_deps(spec)
        download_rpm_sources(spec)
        build_rpm_from_srpm(spec)
        if args.buildrequires:
            buildrequires_for_rpm(spec, provides_to_rpm)
        print()

    # Generate targets to build all srpms and all rpms
    all_rpms = []
    all_srpms = []
    for spec in specs.itervalues():
        rpm_path = spec.binary_package_paths()[-1]
        all_rpms.append(rpm_path)
        all_srpms.append(spec.source_package_path())
        print("%s: %s" % (spec.name(), rpm_path))
        print("%s.srpm: %s" % (spec.name(), spec.source_package_path()))
    print()

    print("RPMS := " + " \\\n\t".join(all_rpms))
    print()
    print("SRPMS := " + " \\\n\t".join(all_srpms))
