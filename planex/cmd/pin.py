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


def get_pin_content(args, pq_name, spec, link):
    """
    Generate the pinfile content for a Spec.
    """
    base_repo = repository_of(spec)
    pq_repo = repository_of(link)

    if args.repo is not None:
        repository = args.repo
        if '#' not in repository:
            url = repository
            commitish = "master"
        else:
            url, commitish = args.repo.split("#", 1)
    else:
        if link is not None:
            url = pq_repo.repository_url()
            # A link specifies a tag, version or commitish
            commitish = pq_repo.commitish_tag_or_branch()
        else:
            url = base_repo.repository_url()
            commitish = "master"

    pinfile = {
        'URL': url,
        'commitish': commitish,
        'patchqueue': pq_name
    }

    if link is not None:
        if args.base is not None:
            base_url, base_commitish = args.base.split("#", 1)
            # this is to allow setting the base_commitish (but not base)
            # for repatched components
            base = base_url if base_url else None
            base_commitish = base_commitish if base_commitish else None
        else:
            base = base_repo.repository_url()
            base_commitish = base_repo.commitish_tag_or_branch()

        # base_commitish can be none for repatched components
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
        print("Argument --base is allowed only for lnk packages")
        sys.exit(1)

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
    parser.add_argument("--repo", metavar="URL#COMMITISH", default=None,
                        help="Source repository URL and commitish."
                             "It can be local e.g. repos/package#master. "
                             "The commitish defaults to master.")
    parser.add_argument("--base", metavar="BASE#COMMITISH", default=None,
                        help="Base repository URL and commitish. "
                             "It can be local e.g. repos/package#master. "
                             "This is used only for lnk packages.")
    parser.add_argument("--patchqueue", default="master",
                        help="Value for the patchqueue field of the pin file. "
                             "Defaults to master. ")
    return parser.parse_args(argv)


def main(argv=None):
    """
    Entry point
    """

    args = parse_args_or_exit(argv)

    if args.base is not None and len(args.base.split("#", 1)) != 2:
        print("Error: --base argument must be of the form BASE#COMMITISH, "
              "got '{}' instead".format(args.base))
        sys.exit(1)

    package_name = args.package
    xs_path = os.getcwd()
    pin = make_pin(args, xs_path, package_name)

    print(json.dumps(pin, indent=2))
