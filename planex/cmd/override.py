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


def infer_current_xenserver_path(repo_name):
    """
    Very hacky for now, cut the path to xenserver-specs
    and check the branch name.
    """

    cwd = os.getcwd()
    if repo_name in cwd:
        path = cwd.split(repo_name)[0]
        return os.path.normpath("/".join([path, repo_name]))

    raise ValueError("Base repository %s not found in the current path %s"
                     % (repo_name, cwd))


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


def make_pin(xs_path, xs_repos, xs_branch, pinfile_dir, package_name, package_branch):
    """
    Return the pinfile path and a dict containing the content of the pinfile
    """
    pinfile = {}
    pinfile['URL'] = "%s/%s" % (xs_repos, package_name)
    pinfile['commitish'] = package_branch
    pinfile['patchqueue'] = xs_branch

    if not is_spec(xs_path, package_name):
        print "%s is a lnk: adding 'specfile' field to the override file" % package_name
        pinfile['specfile'] = "%s.spec" % package_name

    pinfile_path = "%s/%s.pin" % (pinfile_dir, package_name)
    return pinfile_path, pinfile


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """

    parser = argparse.ArgumentParser(
        description="Create an override file pointing to a repository \
                     in xenserver-specs/repos. The override automatically \
                     points to the HEAD of the repository.")
    add_common_parser_options(parser)
    parser.add_argument("packages", metavar="PKG", nargs="+",
                        help="package name")
    parser.add_argument("--pinsdir", default="PINS",
                        help="use custom override folder (default to PINS)")
    parser.add_argument("--baserepo", default="xenserver-specs",
                        help="use custom base repository, \
                              its name must be present in the path \
                              (dafault to xenserver-specs)")
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

    xs_path = infer_current_xenserver_path(args.baserepo)
    xs_branch = current_branch(xs_path)
    # make it customisable?
    xs_repos = "repos"

    pinfile_dir = "%s/%s/%s" % (xs_path, args.pinsdir, xs_branch)
    if not os.path.isdir(pinfile_dir):
        print "Creating overrides directory %s" % pinfile_dir
        mkdir_p(pinfile_dir)

    package_branch = args.branch if args.branch is not None else "HEAD"

    for package_name in args.packages:
        pinfile_path, pinfile = make_pin(xs_path, xs_repos, xs_branch, pinfile_dir,
                                         package_name, package_branch)
        with open(pinfile_path, "w") as pin:
            json.dump(pinfile, pin)

        print "Override file for %s saved in %s with the following content" % (package_name, pinfile_path)
        print pinfile

    print "To explicitly override the default transformer settings you can run make with PINSDIR=%s" % pinfile_dir
