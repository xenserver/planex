"""
planex-pin: generate pin files pointing at local repos
in xenserver-specs/repos/ to override the spec/lnk
"""
from __future__ import print_function

import argparse
import copy
import json
import os
import sys

# pylint: disable=relative-import
from six.moves.urllib.parse import parse_qs, urlparse

from planex.blobs import Archive
from planex.cmd.args import common_base_parser
from planex.link import Link
from planex.repository import Repository
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


def repo_or_path(arg):
    """
    Heuristic. Parse URL#commitish into (URL, commitish) and anything else into
    (URL, None)
    """
    if arg.startswith("ssh://"):
        split = arg.split("#")
        if len(split) > 2 or not split:
            raise ValueError(
                "Expected URL or ssh://URL#commitish but got {}".format(arg))
        if len(split) == 1:
            return (arg, None)
        return tuple(split)

    return (arg, None)


# pylint: disable=too-many-branches
def populate_pinfile(pinfile, args, resources):
    """
    Update [pinfile] in place with content of resources.
    """
    for name, source in resources.items():

        # If we are overriding Source0, we still need to keep other
        # eventual sources
        if args.source is not None \
                and (name == "Source0" or "Source" not in name):
            continue
        # When we override PatchQueue0, we get rid of all the other
        # patchqueues
        if args.patchqueue is not None and "PatchQueue" in name:
            continue
        # Patches are defined in the spec and could be overridden with
        # Archives, but we do not put them in the link and pin files
        if "Patch" in name and "PatchQueue" not in name:
            continue

        pinfile[name] = {}
        if source.is_repo:
            url = source.url
            commitish = source.commitish
            prefix = source.prefix
        else:
            # heuristically try to get a repo
            repo = Repository(source.url)
            commitish = repo.commitish_tag_or_branch()
            url = repo.repository_url()
            # for some archives the commitish_tag_or_branch does not work properly
            parsed_url = urlparse(source.url)
            at_val = parse_qs(parsed_url.query).get('at', [None]).pop()
            if at_val is not None and at_val != commitish:
                commitish = at_val
            if name == "Source0":
                prefix = parse_qs(
                    urlparse(source.url).query
                ).get("prefix", None)
                if prefix and isinstance(prefix, list):
                    prefix = prefix.pop()
            else:
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
    if args.source is not None:
        url, commitish = repo_or_path(args.source)
        pinfile["Source0"] = {"URL": url}
        if commitish is not None:
            pinfile["Source0"]["commitish"] = commitish

    populate_pinfile(pinfile, args, resources)

    if args.patchqueue is not None:
        url, commitish = repo_or_path(args.patchqueue)
        pinfile["PatchQueue0"] = {"URL": url}
        if commitish is not None:
            pinfile["PatchQueue0"]["commitish"] = commitish
            pinfile["PatchQueue0"]["prefix"] = resources["PatchQueue0"].prefix

        # When both a PQ0 and an Archive0 are present, and point to the same
        # repository, we assume that they are pointint to the same tarball.
        # This, by default, planex-pin will overwrite the Archive0 with
        # the same content as PatchQueue0. This could fail when multiple
        # archives are present and the one matching the PQ is not the first
        # one, but for now I value the simplicity of the code over covering
        # any possible corner case.
        if "Archive0" not in resources:
            return pinfile

        pq_url = urlparse(url)
        archive = resources["Archive0"]
        archive_url = urlparse(archive.url)
        if pq_url.netloc == archive_url.netloc \
                and pq_url.path == archive_url.path:
            pinfile["Archive0"] = copy.deepcopy(pinfile["PatchQueue0"])
            pinfile["Archive0"]["prefix"] = archive.prefix

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

    parser.add_argument("--override-source", dest="source", default=None,
                        help="Path to a tarball or url of a git "
                             "repository in the form ssh://GitURL#commitish. "
                             "When used the pin will get rid of any "
                             "pre-existing source, archive or patchqueue "
                             "and use the provided path as Source0.")
    parser.add_argument("--override-patchqueue", dest="patchqueue",
                        default=None,
                        help="Path to a tarball or url of a git "
                             "repository in the form ssh://GitURL#commitish. "
                             "When used the pin will get rid of any "
                             "pre-existing patchqueue and use the provided "
                             "path as PatchQueue0.")

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

    print(json.dumps(pin, indent=2, sort_keys=True))

    output = args.output
    if args.write:
        output = "PINS/{}.pin".format(package_name)

    if output is not None:
        path = os.path.dirname(output)
        if os.path.exists(path):
            with open(output, "w") as out:
                json.dump(pin, out, indent=2, sort_keys=True)
        else:
            sys.exit("Error: path {} does not exist.".format(path))
