"""
planex-pin: generate pin files pointing at local repos
in xenserver-specs/repos/ to override the spec/lnk
"""
from __future__ import print_function

import argparse
import json
import os
import sys
import errno

from planex.blobs import Archive
from planex.cmd.args import common_base_parser
from planex.link import Link
from planex.repository import Repository
from planex.util import makedirs
import planex.spec

RPM_DEFINES = [("dist", "pinned"),
               ("_topdir", "."),
               ("_sourcedir", "%_topdir/SOURCES/%name")]


def load_spec_and_lnk(repo_path, package_name):
    """
    Return the Spec object for
    repo_path/SPECS/package_name updated by the current link.
    Exception("package not present") otherwise.
    """
    partial_file_path = "%s/SPECS/%s" % (repo_path, package_name)

    specname = "%s.spec" % partial_file_path
    if not os.path.isfile(specname):
        sys.exit(
            "Spec file for {} not present in {}/SPECS".format(
                package_name, repo_path))

    linkname = "%s.lnk" % partial_file_path
    link = Link(linkname) if os.path.isfile(linkname) else None
    spec = planex.spec.load(specname, link=link, defines=RPM_DEFINES)

    return spec


def populate_pinfile(pinfile, resources):
    """
    Update [pinfile] in place with content of resources.
    """
    for name, source in resources.items():
        # Exclude secondary resources
        if name not in ("Archive0", "PatchQueue0", "Source0"):
            continue

        pinfile[name] = {}
        if source.is_repo:
            url = source.url
            commitish = source.commitish
            prefix = source.prefix
        else:
            repo = Repository(source.url)
            commitish = repo.commitish_tag_or_branch()
            url = repo.repository_url()
            prefix = None

        if commitish is None:
            pinfile[name] = {"URL": source.url}
        else:
            pinfile[name] = {
                "URL": url,
                "commitish": commitish
            }

        if prefix is not None:
            pinfile[name]["prefix"] = prefix
        if isinstance(source, Archive):
            pinfile[name]["prefix"] = source.prefix


def get_pin_content(args, spec):
    """
    Generate the pinfile content for a Spec.
    """
    resources = spec.resources_dict()

    pinfile = {"SchemaVersion": "3"}
    populate_pinfile(pinfile, resources)

    # Apply changes to the URL or commitish to the final resource
    for resource in ("PatchQueue0", "Archive0", "Source0"):
        if resource in resources:
            if args.url:
                pinfile[resource]["URL"] = args.url
            if args.commitish:
                pinfile[resource]["commitish"] = args.commitish
            break

    return pinfile


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """

    parser = argparse.ArgumentParser(
        description="Create a .pin file for PACKAGE. "
                    "Needs to run from the root of a spec repository. "
                    "Note that when URL is an ssh url to a git repository, "
                    "planex will first look for a repository with the "
                    "same name cloned in the $CWD/repos folder.",
        parents=[common_base_parser()])
    parser.add_argument("package", metavar="PACKAGE", help="package name")

    write = parser.add_mutually_exclusive_group()
    write.add_argument("-w", "--write", action="store_true",
                       help="Write pin file in PINS/PACKAGE.pin. "
                            "It overwrites the file if present.")
    write.add_argument("-o", "--output", default=None,
                       help="Path of the pinfile to write. "
                            "It overwrites the file if present.")
    write.add_argument("-s", "--show",
                       action="store_true", dest="show",
                       help="Show the current state of the PIN for"
                            "the given package.")
    write.add_argument("-u", "--unpin",
                       action="store_true", dest="unpin",
                       help="Remove the PIN for the given package.")

    parser.add_argument("--url",
                        help="Replace the URL of the final resource")
    parser.add_argument("--commitish",
                        help="Replace the commitish of the final resource")

    return parser.parse_args(argv)


def main(argv=None):
    """
    Entry point
    """

    args = parse_args_or_exit(argv)

    package_name = args.package
    xs_path = os.getcwd()
    spec = load_spec_and_lnk(xs_path, package_name)
    pin = get_pin_content(args, spec)

    if not (args.quiet or args.show or args.unpin):
        print(json.dumps(pin, indent=2, sort_keys=True,
                         separators=(',', ': ')))

    default_output = "PINS/{}.pin".format(package_name)
    output = args.output
    if args.write:
        output = default_output

    if output is not None:
        path = os.path.dirname(output)
        makedirs(path)
        with open(output, "w") as out:
            json.dump(pin, out, indent=2, sort_keys=True)

    if args.show:
        try:
            with open(default_output, 'r') as infile:
                print(infile.read())
        except IOError as err:
            if err.errno not in (errno.ENOENT,):
                raise
            print("Package '{}' is not pinned".format(package_name))

    if args.unpin:
        try:
            os.remove(default_output)
        except OSError as err:
            if err.errno not in (errno.ENOENT,):
                raise
