"""
planex-clone: Checkout sources referred to by a pin file
"""
from __future__ import print_function

from string import Template
import argparse
from os import symlink
from os.path import basename, dirname, join, relpath
import subprocess

import git
from planex.link import Link
import planex.util as util


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Clone sources')
    parser.add_argument("-P", "--pins-dir", default="PINS",
                        help="Directory containing pin overlays")
    parser.add_argument("--jenkins", action="store_true",
                        help="Print Jenkinsfile fragment")
    parser.add_argument("--skip-base", dest="clone_base",
                        default=True, action="store_false",
                        help="Do not clone the base repository")
    parser.add_argument("--credentials", metavar="CREDS", default="",
                        help="Credentials")
    parser.add_argument(
        "-r", "--repos", metavar="DIR", default="repos",
        help='Local path to the repositories')
    parser.add_argument("pins", metavar="PINS", nargs="*", help="pin file")
    return parser.parse_args(argv)


def repo_name(url):
    """Return the base repository name in url.   This is the name of
       the directory which would be created by `git clone url`"""
    return basename(url).rsplit(".git")[0]


CHECKOUT_TEMPLATE = Template("""checkout poll: true,
         scm:[$$class: 'GitSCM',
              branches: [[name: '$branch']],
              extensions: [[$$class: 'RelativeTargetDirectory',
                            relativeTargetDir: '$checkoutdir'],
                           [$$class: 'LocalBranch']],
              userRemoteConfigs: [
                [credentialsId: '$credentials',
                 url: '$url']]]
""")


def clone_jenkins(url, destination, commitish, credentials):
    """Print Jenkinsfile fragment to clone repository"""
    destination = join(destination, repo_name(url))
    print(CHECKOUT_TEMPLATE.substitute(url=url,
                                       branch=commitish,
                                       checkoutdir=destination,
                                       credentials=credentials))


def clone(url, destination, commitish):
    """Clone repository"""
    destination = join(destination, repo_name(url))
    repo = git.Repo.clone_from(url, destination)
    if commitish in repo.remotes['origin'].refs:
        branch_name = commitish
        commit = repo.remotes['origin'].refs[commitish]

    elif commitish in repo.tags:
        branch_name = "planex/%s" % commitish
        commit = repo.refs[commitish]

    else:
        branch_name = "planex/%s" % commitish[:8]
        commit = repo.rev_parse(commitish)

    local_branch = repo.create_head(branch_name, commit)
    local_branch.checkout()
    return repo


def apply_patchqueue(base_repo, pq_repo, pq_dir):
    """
    Apply a patchqueue to a base repository
    """
    # Symlink the patchqueue repository into .git/patches
    link_path = relpath(pq_repo.working_dir, base_repo.git_dir)
    symlink(link_path, join(base_repo.git_dir, "patches"))

    # Symlink the patchqueue directory to match the base_repo
    # branch name as guilt expects
    patchqueue_path = join(base_repo.git_dir, "patches",
                           base_repo.active_branch.name)
    branch_path = dirname(base_repo.active_branch.name)
    util.makedirs(dirname(patchqueue_path))
    symlink(relpath(pq_dir, branch_path), patchqueue_path)

    # Create empty guilt status for the branch
    status = join(patchqueue_path, 'status')
    open(status, 'w').close()

    # Push patchqueue
    # `guilt push --all` fails with a non-zero error code if the patchqueue
    # is empty; this cannot be distinguished from a patch failing to apply,
    # so skip trying to push if the patchqueue is empty.
    patches = subprocess.check_output(['guilt', 'unapplied'],
                                      cwd=base_repo.working_dir)
    if patches:
        subprocess.check_call(['guilt', 'push', '--all'],
                              cwd=base_repo.working_dir)


def main(argv=None):
    """
    Entry point
    """
    args = parse_args_or_exit(argv)

    for pinpath in args.pins:
        pin = Link(pinpath)

        if args.jenkins:
            print('echo "Cloning %s"' % pin.url)
            clone_jenkins(pin.url, args.repos, pin.commitish, args.credentials)

        else:
            try:
                print("Cloning %s" % pin.url)
                util.makedirs(args.repos)
                pq_repo = clone(pin.url, args.repos, pin.commitish)

                if args.clone_base and pin.base:
                    print("Cloning %s" % pin.base)
                    base_repo = clone(pin.base, args.repos, pin.base_commitish)
                    apply_patchqueue(base_repo, pq_repo, pin.patchqueue)

            except git.GitCommandError as gce:
                print(gce.stderr)
