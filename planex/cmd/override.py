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


def mkdir_p(path):
    """
    Like `mkdir -p path` but does not fail when the path is already present.
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise exc


def heuristic_is_spec_repo_root(xs_path):
    """
    Heuristic check for a spec repository root folder.
    Looks for the presence of xs_path/.git, xs_path/SPECS and xs_path/mock.
    Raise and error if any of those is not present.
    """

    if not (os.path.exists("%s/.git" % xs_path) and
            os.path.exists("%s/SPECS" % xs_path) and
            os.path.exists("%s/mock" % xs_path)):
        raise Exception("Spec repository not found in %s" % xs_path)


def is_spec(repo_path, package_name):
    """
    True if repo_path/SPECS/package_name is a spec file,
    False if it is a link file,
    Exception("package not present") otherwise
    """
    partial_file_path = "%s/SPECS/%s" % (repo_path, package_name)

    if os.path.isfile("%s.spec" % partial_file_path):
        return True
    if os.path.isfile("%s.lnk" % partial_file_path):
        return False

    err_str = "Spec or link file for %s not present in %s/SPECS" % (
        package_name, repo_path)
    raise Exception(err_str)


def make_pin(xs_path, xs_branch, pinfile_dir, package_name, package_branch):
    """
    Return the pinfile path and a dict containing the content of the pinfile
    """

    xs_repos = "repos"     # make it customisable?

    pinfile = {}
    pinfile['URL'] = "%s/%s" % (xs_repos, package_name)
    pinfile['commitish'] = package_branch
    pinfile['patchqueue'] = xs_branch

    if not is_spec(xs_path, package_name):
        print "%s is a lnk: adding 'specfile' field" % package_name
        pinfile['specfile'] = "%s.spec" % package_name

    pinfile_path = "%s/%s.pin" % (pinfile_dir, package_name)
    return pinfile_path, pinfile


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """

    parser = argparse.ArgumentParser(
        description="Create an override file pointing to a repository \
                     in $CWD/repos. The override automatically \
                     points to the HEAD of the repository. You must run \
                     this tool from the root of a spec repository.")
    add_common_parser_options(parser)
    parser.add_argument("packages", metavar="PKG", nargs="+",
                        help="package name")
    parser.add_argument("--pinsdir", default="PINS",
                        help="use custom override folder (default to PINS)")
    parser.add_argument("--branch", default=None,
                        help="branch or tag name used for the override \
                              (defaults to HEAD)")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv=None):
    """
    Entry point
    """

    args = parse_args_or_exit(argv)

    xs_path = os.getcwd()
    heuristic_is_spec_repo_root(xs_path)

    xs_branch = current_branch(xs_path)

    pinfile_dir = "%s/%s/%s" % (xs_path, args.pinsdir, xs_branch)
    if not os.path.isdir(pinfile_dir):
        print "Creating overrides directory %s" % pinfile_dir
        mkdir_p(pinfile_dir)

    package_branch = args.branch if args.branch is not None else "HEAD"

    for package_name in args.packages:
        pinfile_path, pinfile = make_pin(xs_path, xs_branch, pinfile_dir,
                                         package_name, package_branch)
        with open(pinfile_path, "w") as pin:
            json.dump(pinfile, pin)

        print "Override file for %s saved in %s with the following content" % (
            package_name, pinfile_path)
        print pinfile

    print "To explicitly override the default settings " \
          "you can run make with PINSDIR=%s" % pinfile_dir
