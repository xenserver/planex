"""
planex-whatchanged: Find packages that have to be rebuilt
"""

import argparse
import os
import sys
import logging

import subprocess
import itertools
import rpm
import argcomplete
from planex.util import setup_logging
from planex.util import add_common_parser_options
from planex.util import setup_sigint_handler
import planex.spec as pkg


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description="Find packages that have to be rebuilt")
    add_common_parser_options(parser)
    parser.add_argument("specs", metavar="SPEC", nargs="+", help="spec file")
    parser.add_argument("--strict", action="store_true",
                        help="Do not allow downgrades")
    parser.add_argument(
        "-D", "--define", default=[], action="append",
        help="--define='MACRO EXPR' define MACRO with value EXPR")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def get_repo_versions(packages):
    """Return the versions of specified packages from the repository"""
    cmd = ["repoquery", "--disablerepo=base,epel,updates,extras",
           "-q", "--qf=%{NAME} %{EPOCH} %{VERSION} %{RELEASE}"] + packages
    logging.debug("Running %s", cmd)
    return {
        name: (e, v, r)
        for (name, e, v, r) in
        [line.split(' ')
         for line in subprocess.check_output(cmd).splitlines()]
    }


def find_changed(local_rpms, remote_rpms, strict):
    """Return list of changed RPMs"""
    updated = []
    downgraded = []
    for (package, local_evr) in local_rpms.iteritems():
        logging.debug("Looking up %s in remote package list", package)
        if package in remote_rpms:
            remote_evr = remote_rpms[package]
            logging.debug("Comparing %s and %s", local_evr, remote_evr)
            ret = rpm.labelCompare(local_evr, remote_evr)
            if ret > 0:
                result = ">"
                updated += [package]
            elif ret < 0:
                result = "<"
                downgraded += [package]
            else:
                result = "="
            logging.debug("Package '%s' local version %s %s %s", package,
                          local_evr, result, remote_evr)
    logging.debug("Got %d updated packages", len(updated))
    if downgraded:
        logging.warning("Downgraded packages: %s", downgraded)
        if strict:
            raise Exception("Downgrades are not allowed in strict mode")
    return updated + downgraded


def digests_of_rpm(srpm):
    """Return the file digests of an RPM"""
    with open(srpm, "r") as srpmfile:
        hdr = rpm.ts().hdrFromFdno(srpmfile.fileno())
        return hdr['FILEDIGESTS']


def groupbykey(lst, key):
    """Sort and group by the given list using the key function"""
    return itertools.groupby(sorted(lst, key=key), key)


def compute_changes(specs, strict):
    """Return set of changed source package names"""
    logging.debug("Gathering binary packages")
    rpms = {}
    rpm2spec = {}
    for spec in specs.values():
        outputs = spec.binary_packages()
        rpms.update(outputs)
        for package in outputs:
            rpm2spec[package] = spec.name()
    logging.debug("Got %d binary packages", len(rpms))

    logging.debug("Querying repositories")
    repo_versions = get_repo_versions(rpms.keys())
    logging.debug("Got %d remote binary packages", len(repo_versions))

    delta = find_changed(rpms, repo_versions, strict)
    logging.debug("Got %d changed packages", len(delta))

    # Map them back to spec names, see comment on generating dependencies only
    # on first binary package in planex depend

    return set([rpm2spec[package] for package in delta])


def compute_srpm_changes(fulldiffpkgs, specs, changed_specs):
    """Finds source packages that have changed source/patches"""
    srpm2spec = {os.path.basename(spec.source_package_path()): spec.name()
                 for spec in specs.values()}

    for (base, paths) in groupbykey(fulldiffpkgs, os.path.basename):
        paths = [p for p in paths]
        logging.debug("Checking %s in %s", base, paths)
        pathdigests = {path: frozenset(digests_of_rpm(path)) for path in paths}
        different = set(pathdigests.values())
        logging.debug("Unique digests: %d", len(different))
        if len(different) > 1:
            logging.debug(pathdigests)
            logging.warn("File digests for %s are different", base)
            changed_specs.update([srpm2spec[base]])


def load_specs(args):
    """Load all the specs specified on the command line"""
    macros = [tuple(macro.split(' ', 1)) for macro in args.define]

    if any(len(macro) != 2 for macro in macros):
        _err = [macro for macro in macros if len(macro) != 2]
        print "error: malformed macro passed to --define: %r" % _err
        sys.exit(1)

    logging.debug("Loading specs")
    return {
        spec.name(): spec for spec in
        [pkg.Spec(spec_path, defines=macros)
         for spec_path in args.specs if spec_path.endswith(".spec")]
    }


def update_reverse_dependencies(specs, changed_specs, strict):
    """Find packages that had their build requirements rebuilt"""
    provides = set()
    for name in changed_specs:
        provides.update(specs[name].provides())

    reverse_rebuild = [name for name in specs
                       if name not in changed_specs and not
                       specs[name].buildrequires().isdisjoint(provides)]
    if reverse_rebuild:
        logging.warning("These packages would require a rebuild: %s",
                        reverse_rebuild)
        if strict:
            raise Exception("Strict mode doesn't allow unspecified rebuilds")
        changed_specs.update(reverse_rebuild)
        update_reverse_dependencies(specs, changed_specs, strict)


def main(argv=None):
    """
    Entry point
    """

    setup_sigint_handler()
    args = parse_args_or_exit(argv)
    setup_logging(args)

    logging.debug("Strict mode: %s", args.strict)
    specs = load_specs(args)
    logging.debug("Got %d specs", len(specs))

    changed_specs = compute_changes(specs, args.strict)

    fulldiffpkgs = [srpm for srpm in args.specs if srpm.endswith(".src.rpm")]
    compute_srpm_changes(fulldiffpkgs, specs, changed_specs)

    update_reverse_dependencies(specs, changed_specs, args.strict)

    logging.debug("Got %d changed sources: %s",
                  len(changed_specs), changed_specs)
    for spec in changed_specs:
        print spec
