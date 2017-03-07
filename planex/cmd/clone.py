"""
planex-clone: Checkout sources referred to by a pin file
"""

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
    parser.add_argument("--credentials", metavar="CREDS", default="",
                        help="Credentials")
    parser.add_argument(
        "-r", "--repos", metavar="DIR", default="repos",
        help='Local path to the repositories')
    parser.add_argument("pins", metavar="PINS", nargs="*", help="pin file")
    return parser.parse_args(argv)


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
    print CHECKOUT_TEMPLATE.substitute(url=url,
                                       branch=commitish,
                                       checkoutdir=destination,
                                       credentials=credentials)


def clone(url, destination, commitish):
    """Clone repository"""
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


def main(argv=None):
    """
    Entry point
    """
    args = parse_args_or_exit(argv)

    for pinpath in args.pins:
        pin = Link(pinpath)
        reponame = basename(pin.url).rsplit(".git")[0]
        checkoutdir = join(args.repos, reponame)

        if args.jenkins:
            print 'echo "Cloning %s"' % pin.url
            clone_jenkins(pin.url, checkoutdir, pin.commitish, args.credentials)

        else:
            print "Cloning %s" % pin.url
            util.makedirs(dirname(checkoutdir))
            clone(pin.url, checkoutdir, pin.commitish)

            if pin.base is not None:
                base_reponame = basename(pin.base).rsplit(".git")[0]
                base_checkoutdir = join(args.repos, base_reponame)
                print "Cloning %s" % pin.base
                util.makedirs(dirname(base_checkoutdir))
                base_repo = clone(pin.base, base_checkoutdir,
                                  pin.base_commitish)

                # Symlink the patchqueue repository into .git/patches
                patch_path = join(base_checkoutdir, ".git/patches")
                link_path = relpath(checkoutdir, dirname(patch_path))
                symlink(link_path, patch_path)

                # Symlink the patchqueue directory to match the base_repo
                # branch name as guilt expects
                patchqueue_path = join(base_checkoutdir, ".git/patches",
                                       base_repo.active_branch.name)
                branch_path = dirname(base_repo.active_branch.name)
                util.makedirs(dirname(patchqueue_path))
                symlink(relpath(pin.patchqueue, branch_path), patchqueue_path)

                # Create empty guilt status for the branch
                status = join(patchqueue_path, 'status')
                open(status, 'w').close()

                # Push patchqueue
                subprocess.check_call(['guilt', 'push', '--all'],
                                      cwd=base_checkoutdir)


if __name__ == "__main__":
    main()
