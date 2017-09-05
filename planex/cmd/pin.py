"""
planex-pin: generate pin files pointing at local repos
in xenserver-specs/repos/ to override the spec/lnk
"""
from __future__ import print_function

import argparse
import json
import os
import sys

from planex.cmd.args import add_common_parser_options
from planex.link import Link
from planex.repository import Repository
from planex.spec import Spec


def spec_and_lnk(repo_path, package_name):
    """
    Return the Spec and Link object for
    repo_path/SPECS/package_name.
    Link can be None if not present.
    Exception("package not present") otherwise
    """
    partial_file_path = "%s/SPECS/%s" % (repo_path, package_name)

    specname = "%s.spec" % partial_file_path
    if not os.path.isfile(specname):
        print("Spec file for %s not present in %s/SPECS"
              % (package_name, repo_path))
        sys.exit(1)

    spec = Spec(specname)

    linkname = "%s.lnk" % partial_file_path
    link = Link(linkname) if os.path.isfile(linkname) else None

    return spec, link


def repository_of(spec_or_link):
    """Return the Repository of the provided Spec source url or Link url.
       None if spec_or_link is None"""
    if isinstance(spec_or_link, Spec):
        return Repository(spec_or_link.source_urls()[0])
    if isinstance(spec_or_link, Link):
        return Repository(spec_or_link.url)
    if spec_or_link is None:
        return None
    else:
        print("repository_of: got unexpected object {}")
        sys.exit(1)


# pylint: disable=too-many-branches
def get_pin_content(args, pq_name, spec, link):
    """
    Generate the pinfile content for a Spec.
    """
    base_repo = repository_of(spec)
    pq_repo = repository_of(link)

    url = args.url
    if url is None:
        if link is not None:
            url = pq_repo.repository_url()
        else:
            url = base_repo.repository_url()

    commitish = args.commitish
    if commitish is None:
        if link is not None:
            commitish = pq_repo.commitish_tag_or_branch()
        else:
            commitish = base_repo.commitish_tag_or_branch()

    pinfile = {
        'URL': url,
        'commitish': commitish,
        'patchqueue': pq_name
    }

    if link is not None:
        if args.base_commitish is not None:
            base = args.base  # This can be None
            base_commitish = args.base_commitish
        else:
            base = base_repo.repository_url()
            base_commitish = base_repo.commitish_tag_or_branch()

        # base_commitish can be None, it happens for repatched components
        if base_commitish is not None:
            if base is not None:
                pinfile['base'] = base
            pinfile['base_commitish'] = base_commitish

        if link.sources is not None:
            pinfile["sources"] = link.sources

        if link.patches is not None:
            pinfile["patches"] = link.patches

    return pinfile


def make_pin(args, xs_path, package_name):
    """
    Return the pinfile path and a dict containing the content of the pinfile
    """

    spec, link = spec_and_lnk(xs_path, package_name)

    if link is None and args.base is not None:
        sys.exit("Argument --base is allowed only for lnk packages")

    return get_pin_content(args, args.patchqueue, spec, link)


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """

    parser = argparse.ArgumentParser(
        description="Create a .pin file pointing to a repository "
                    "in $CWD/repos. You must run "
                    "this tool from the root of a spec repository.")
    add_common_parser_options(parser)
    parser.add_argument("package", help="package name")
    parser.add_argument("--url", metavar="URL", default=None,
                        help="Source repository URL."
                             "It can be local e.g. repos/package.")
    parser.add_argument("--commitish", default=None,
                        help="Source repository commitish, tag or branch)."
                             "Defaults to the one inferred from the SPEC "
                             "or link file.")
    parser.add_argument("--base", metavar="URL", default=None,
                        help="Base repository URL. "
                             "It can be local e.g. repos/package. "
                             "This is used only for lnk packages.")
    parser.add_argument("--base_commitish", metavar="COMMITISH",
                        default=None,
                        help="Base repository commitish, tag or branch. "
                             "This is required when using --base. "
                             "This is used only for lnk packages.")
    parser.add_argument("--patchqueue", default="master",
                        help="Value for the patchqueue field of the pin file. "
                             "Defaults to master. ")
    parser.add_argument("-o", "--output", default=None,
                        help="Path of the pinfile to write. "
                             "When used, it overwrites the file "
                             "if present.")
    return parser.parse_args(argv)


def main(argv=None):
    """
    Entry point
    """

    args = parse_args_or_exit(argv)

    if args.base is not None and args.base_commitish is None:
        sys.exit("Error: --base_commitish is required if --base is used.")

    package_name = args.package
    xs_path = os.getcwd()
    pin = make_pin(args, xs_path, package_name)

    print(json.dumps(pin, indent=2))

    if args.output:
        path = os.path.dirname(args.output)
        if os.path.exists(path):
            with open(args.output, "w") as out:
                json.dump(pin, out, indent=2)
        else:
            sys.exit("Error: path {} does not exist.".format(path))
