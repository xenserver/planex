"""
planex-clone: Checkout sources referred to by a pin file
"""
from __future__ import print_function

import errno
from string import Template
import argparse
from os import symlink
from os.path import basename, dirname, join, relpath
import subprocess
import sys

import git
from planex.link import Link
import planex.util as util


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Clone sources')
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
    try:
        symlink(relpath(pq_dir, branch_path), patchqueue_path)
    except OSError as err:
        if err.errno == errno.EEXIST:
            pass
        else:
            raise

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

# pylint: disable=too-many-locals
def main(argv=None):
    """
    Entry point
    """
    args = parse_args_or_exit(argv)

    for pinpath in args.pins:
        pin = Link(pinpath)

        if args.jenkins:
            # The following assumes that the pin file does not use any
            # rpm macro in its fields. We can enable them by using
            # planex.spec.load and the right RPM_DEFINES but it is more
            # error prone and should probably be done only if we see
            # that it is an essential feature.
            gathered = ([source for _, source in pin.sources.items()
                         if source.get('commitish', False)] +
                        [archive for _, archive in pin.archives.items()
                         if archive.get('commitish', False)] +
                        [pq for _, pq in pin.patchqueue_sources.items()
                         if pq.get('commitish', False)])

            # Prevent double-cloning of a repository
            gathered = set((gath['URL'], gath['commitish'])
                           for gath in gathered)

            if gathered:
                print('echo "Clones for %s"' % pinpath)

            # this is suboptimal but the sets are very small
            if any(commitish1 != commitish2
                   for (url1, commitish1) in gathered
                   for (url2, commitish2) in gathered
                   if url1 == url2):
                sys.exit("error: cloning two git repositories with the same "
                         "name but different commitish is not supported")

            for url, commitish in gathered:
                print('echo "Cloning %s"' % url)
                clone_jenkins(url, args.repos,
                              commitish, args.credentials)

        else:
            sources = [(src['URL'], src['commitish'])
                       for _, src in pin.sources.items()
                       if src.get('commitish', False)]
            patchqueues = [(pq['URL'], pq['commitish'], dirname(pq['prefix']))
                           for _, pq in pin.patchqueue_sources.items()
                           if pq.get('commitish', False)]

            if not sources:
                sys.exit("error: planex-clone requires Source0 to point to "
                         "a git repository.")
            if pin.patchqueue_sources and not patchqueues:
                sys.exit("error: planex-clone requires PatchQueue0 to point "
                         "to a git repository.")

            if len(sources) != 1 and len(patchqueues) > 1:
                sys.exit(
                    "error: planex-clone does not support the cloning and "
                    "assembly of multiple sources and patchqueues, currently "
                    "this case needs to be handled by hands.")
            try:
                src_url, src_commitish = sources.pop()
                print("Cloning %s" % src_url)
                util.makedirs(args.repos)
                src_repo = clone(src_url, args.repos, src_commitish)

                if patchqueues:
                    pq_url, pq_commitish, pq_prefix = patchqueues.pop()
                    print("Cloning %s" % pq_url)
                    pq_repo = clone(pq_url, args.repos,
                                    pq_commitish)
                    apply_patchqueue(src_repo, pq_repo, pq_prefix)

            except git.GitCommandError as gce:
                print(gce.stderr)
