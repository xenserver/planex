#!/usr/bin/python

"""
planex-depend: Generate Makefile-format dependencies from spec files
"""

import argparse
import os
import planex.spec as pkg
import platform
import sys
import urlparse
import glob
from planex import mappkgname


def build_type():
    """
    Discover appropriate build type for local host
    """
    debian_like = ["ubuntu", "debian", "linaro"]
    rhel_like = ["fedora", "redhat", "centos"]

    dist = platform.linux_distribution(full_distribution_name=False)[0].lower()
    assert dist in debian_like + rhel_like

    if dist in debian_like:
        return "deb"
    elif dist in rhel_like:
        return "rpm"


def build_srpm_from_spec(spec):
    """
    Generate rules to build SRPM from spec
    """
    srpmpath = spec.source_package_path()
    print '%s: %s %s' % (srpmpath, spec.specpath(),
                         " ".join(spec.source_paths()))


def download_rpm_sources(spec):
    """
    Generate rules to download sources
    """
    for (url, path) in zip(spec.source_urls(), spec.source_paths()):
        source = urlparse.urlparse(url)
        if source.scheme in ["http", "https", "file"]:
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

    rpm_path = spec.binary_package_paths()[0]
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
            provides_to_rpm[provided] = spec.binary_package_paths()[0]
    return provides_to_rpm


def buildrequires_for_rpm(spec, provides_to_rpm):
    """
    Generate build dependency rules between binary RPMs
    """
    rpmpath = spec.binary_package_paths()[0]
    for buildreq in spec.buildrequires():
        # Some buildrequires come from the system repository
        if buildreq in provides_to_rpm:
            buildreqrpm = provides_to_rpm[buildreq]
            print "%s: %s" % (rpmpath, buildreqrpm)


def parse_cmdline():
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description="Generate Makefile dependencies from RPM Spec files")
    parser.add_argument("specs", metavar="SPEC", nargs="+", help="spec file")
    parser.add_argument(
        "-i", "--ignore", metavar="PKG", action="append", default=[],
        help="package name to ignore")
    parser.add_argument(
        "-I", "--ignore-from", metavar="FILE", action="append", default=[],
        help="file of package names to be ignored")
    parser.add_argument(
        "-P", "--pins-dir", help="Directory containing pin overlays")
    parser.add_argument(
        "-d", "--dist", metavar="DIST", default="",
        help="distribution tag (used in RPM filenames)")
    parser.add_argument(
        "-r", "--repos_path", metavar="DIR", default="repos",
        help='Local path to the repositories')
    parser.add_argument(
        "-p", "--packaging", metavar="PACKAGING",
        choices=["rpm", "deb"], default=build_type(),
        help='Packaging to use (rpm or deb): default %s' % build_type())
    parser.add_argument(
        "--no-package-name-check", dest="check_package_names",
        action="store_false", default=True,
        help="Don't check that package name matches spec file name")
    parser.add_argument(
        "-t", "--topdir", metavar="DIR", default=None,
        help='Set rpmbuild toplevel directory')
    return parser.parse_args()


def main():
    """
    Entry point
    """
    args = parse_cmdline()
    specs = {}

    pkgs_to_ignore = args.ignore
    for ignore_from in args.ignore_from:
        try:
            with open(ignore_from) as ignore_file:
                for name in ignore_file.readlines():
                    pkgs_to_ignore.append(name.strip())
        except IOError:
            pass
    for i in pkgs_to_ignore:
        print "# Will ignore: %s" % i

    pins = {}
    if args.pins_dir:
        pins_glob = os.path.join(args.pins_dir, "*.spec")
        pin_paths = glob.glob(pins_glob)
        if pin_paths and args.packaging == "deb":
            sys.stderr.write("error: Pinning not supported for debian target")
            sys.exit(1)
        for pin_path in pin_paths:
            spec = pkg.Spec(pin_path, target="rpm", dist=args.dist,
                            check_package_name=args.check_package_names,
                            topdir=args.topdir)
            pins[os.path.basename(pin_path)] = spec

    os_type = platform.linux_distribution(
        full_distribution_name=False)[1].lower()
    for spec_path in args.specs:
        try:
            if args.packaging == "deb":

                def map_name_fn(name):
                    return mappkgname.map_package(name, os_type)

                spec = pkg.Spec(spec_path, target="deb", map_name=map_name_fn,
                                check_package_name=args.check_package_names,
                                topdir=args.topdir)

            else:
                spec = pkg.Spec(spec_path, target="rpm", dist=args.dist,
                                check_package_name=args.check_package_names,
                                topdir=args.topdir)
            pkg_name = spec.name()
            if pkg_name in pkgs_to_ignore:
                continue

            spec_name = os.path.basename(spec_path)
            if spec_name in pins:
                print "# Pinning '%s' to '%s'" % (pkg_name,
                                                  pins[spec_name].specpath())
                specs[spec_name] = pins[spec_name]
            else:
                specs[spec_name] = spec

        except pkg.SpecNameMismatch as exn:
            sys.stderr.write("error: %s\n" % exn.message)
            sys.exit(1)

    provides_to_rpm = package_to_rpm_map(specs.values())

    for spec in specs.itervalues():
        build_srpm_from_spec(spec)
        download_rpm_sources(spec)
        build_rpm_from_srpm(spec)
        buildrequires_for_rpm(spec, provides_to_rpm)
        print ""

    # Generate targets to build all srpms and all rpms
    all_rpms = []
    all_srpms = []
    for spec in specs.itervalues():
        rpm_path = spec.binary_package_paths()[0]
        all_rpms.append(rpm_path)
        all_srpms.append(spec.source_package_path())
        print "%s: %s" % (spec.name(), rpm_path)
    print ""

    print "rpms: " + " \\\n\t".join(all_rpms)
    print ""
    print "srpms: " + " \\\n\t".join(all_srpms)
    print ""
    print "install: all"
    print "\t. scripts/%s/install.sh" % build_type()


if __name__ == "__main__":
    main()
