"""
planex-override: generate override files pointing at local repos
in xenserver-specs/repos/
"""

import errno
import json
import os

import argparse
import argcomplete

from planex.git import current_branch
from planex.util import add_common_parser_options


def infer_current_xenserver_path(repo_name):
    """
    Very hacky for now, cut the path to xenserver-specs
    and check the branch name.
    """

    cwd = os.getcwd()
    if repo_name in cwd:
        path = cwd.split(repo_name)[0]
        return os.path.normpath("/".join([path, repo_name]))

    raise ValueError("%s not found in %s" % (repo_name, cwd))


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """

    parser = argparse.ArgumentParser(
        description="Create an override file pointing to a repository \
                     in xenserver-specs/repos")
    add_common_parser_options(parser)
    parser.add_argument("reponame", metavar="REPO", help="repository nanme")
    parser.add_argument("branch", metavar="BRANCH", nargs="?",
                        help="branch or tag name (defaults to HEAD)")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv=None):
    """
    Entry point
    """

    args = parse_args_or_exit(argv)

    # TODO: make it customisable
    xs_path = infer_current_xenserver_path("xenserver-specs")
    xs_branch = current_branch(xs_path)

    pinfile = {}
    pinfile['URL'] = "repos/%s" % args.reponame
    pinfile['commitish'] = args.branch if args.branch is not None else "HEAD"
    pinfile['patchqueue'] = xs_branch

    pinfile_dir = "%s/PINS/%s" % (xs_path, xs_branch)
    pinfile_path = "%s/%s.pin" % (pinfile_dir, args.reponame)

    print(pinfile, pinfile_dir, pinfile_path)

    if not os.path.isdir(pinfile_dir):
        print "Creating overrides directory %s" % pinfile_dir
        os.mkdir(pinfile_dir)

    print "Override file for %s saved in %s" % (args.reponame, pinfile_path)
    with open(pinfile_path, "w") as pin:
        json.dump(pinfile, pin)
