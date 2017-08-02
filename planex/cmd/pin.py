"""
planex-pin: generate pin files pointing at local repos
in xenserver-specs/repos/ to override the spec/lnk
"""
from __future__ import print_function

import argparse
import json
import os
import sys
from urlparse import urlunparse

from planex.cmd.args import add_common_parser_options
from planex.link import Link
from planex.repository import Repository
from planex.spec import Spec
from planex.util import makedirs


def heuristic_is_spec_repo_root(xs_path):
    """
    Heuristic check for a spec repository root folder.
    Looks for the presence of xs_path/.git, xs_path/SPECS and xs_path/mock.
    Raise and error if any of those is not present.
    """

    if not (os.path.exists("%s/.git" % xs_path) and
                os.path.exists("%s/SPECS" % xs_path) and
                os.path.exists("%s/mock" % xs_path)):
        print("Spec repo not found in %s" % xs_path)
        sys.exit(1)


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


def repository_url(repo):
    """
    Return the first non-null value among repo.clone_url and
    repo.url. If they are all None, it returns None.
    """
    if repo.clone_url is not None:
        return repo.clone_url
    if repo.url is not None:
        return urlunparse(repo.url)


def commitish_tag_or_branch(repo):
    """
    Return the first non-null value among the repository commitish,
    tag or branch. If they are all None, it returns None.
    """
    if repo.commitish is not None:
        return repo.commitish
    if repo.tag is not None:
        return repo.tag
    if repo.branch is not None:
        return repo.branch


def get_pin_content(args, pq_name, spec, link):
    """
    Generate the pinfile content for a Spec.
    """
    base_repo = repository_of(spec)
    pq_repo = repository_of(link)

    if args.url is not None:
        url = args.url
    else:
        if link is not None:
            url = repository_url(pq_repo)
        else:
            url = repository_url(base_repo)

    if args.branch is not None:
        commitish = args.branch
    else:
        if link is not None:
            # A link specifies a tag, version or commitish
            commitish = commitish_tag_or_branch(pq_repo)
        else:
            commitish = "master"

    pinfile = {
        'URL': url,
        'commitish': commitish,
        'patchqueue': pq_name
    }

    if link is not None:
        if args.base is not None:
            base_url, base_commitish = args.base.split("#", 1)
            base = base_url
            base_commitish = base_commitish
        else:
            base = repository_url(base_repo)
            # TODO: what whould we do if base is a url to a non-git tarball and the following is None?
            base_commitish = commitish_tag_or_branch(base_repo)

        # TODO: Should we take into account here if a spec is already in PINS?
        pinfile.update({
            'base': base,
            'base_commitish': base_commitish
        })

        if link.sources is not None:
            pinfile["sources"] = link.sources

        if link.patches is not None:
            pinfile["patches"] = link.patches

    return pinfile


def make_pin(args, xs_path, package_name):
    """
    Return the pinfile path and a dict containing the content of the pinfile
    """

    # TODO: make the 'patchqueue' field customisable?
    pin_pq_name = "master"
    spec, link = spec_and_lnk(xs_path, package_name)

    if link is None and args.base is not None:
        print("Argument --base is allowed only for lnk packages")
        sys.exit(1)

    return get_pin_content(args, pin_pq_name, spec, link)


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
    parser.add_argument("--pinsdir", default="PINS",
                        help="use custom pin folder (default to PINS)")
    parser.add_argument("--url", metavar="URL", default=None,
                        help="Source repository URL. It can be local "
                             "e.g. repos/package)")
    parser.add_argument("--branch", default=None,
                        help="branch, hash or tag name to specify "
                             "the source tree to compile (defaults to "
                             "master or the tag in the lnk file)")
    parser.add_argument("--base", metavar="BASE#COMMITISH", default=None,
                        help="Base repository URL and commitish. "
                             "It can be local e.g. repos/package#master. "
                             "This is used only for lnk packages.")
    parser.add_argument("--dry-run", dest="dry", action="store_true",
                        help="perform a dry-run only showing the "
                             "performed steps")
    parser.add_argument("--no-checks", dest="nochecks", action="store_true",
                        help="prevent check for the presence of a spec "
                             "repository")
    return parser.parse_args(argv)


def main(argv=None):
    """
    Entry point
    """

    args = parse_args_or_exit(argv)

    if args.dry:
        print("======= running in dry-run mode =======")

    xs_path = os.getcwd()
    if not args.nochecks:
        heuristic_is_spec_repo_root(xs_path)

    if args.base is not None and len(args.base.split("#", 1)) != 2:
        print("Error: --base argument must be of the form BASE#COMMITISH, "
              "got '{}' instead".format(args.base))
        sys.exit(1)

    pinsdir = "%s/%s" % (xs_path, args.pinsdir)
    if not args.dry and not os.path.exists(pinsdir):
        print("Creating pins directory {}".format(pinsdir))
        makedirs(pinsdir)

    package_name = args.package
    pin = make_pin(args, xs_path, package_name)
    pinfile = "{}/{}.pin".format(pinsdir, package_name)

    if not args.dry:
        with open(pinfile, "w") as pf:
            json.dump(pin, pf, indent=2)

    print("Pin file for {} saved in {} with the following content".format(
        package_name, pinfile))
    print(json.dumps(pin, indent=2))
