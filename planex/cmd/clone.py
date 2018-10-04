"""
planex-clone: Checkout sources referred to by a pin file
"""
from __future__ import print_function

import errno
import argparse
from os import symlink, getcwd
from os.path import basename, dirname, join, relpath, splitext
import subprocess
import sys
import tarfile
from textwrap import fill
import json
import git

from planex.cmd.fetch import fetch_source_dispatch
from planex.link import Link
import planex.util as util
import planex.spec


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Clone sources')
    parser.add_argument("--jenkins", action="store_true",
                        help="Print Jenkinsfile fragment")
    parser.add_argument("--clone", action="store_true",
                        help="Only clone repositories, do not apply patches")
    parser.add_argument("--output", "-o",
                        default=join(getcwd(), "clone_sources.json"),
                        help="Choose output name for clone sources JSON file")
    parser.add_argument(
        "-r", "--repos", metavar="DIR", default="repos",
        help='Local path to the repositories')
    parser.add_argument("pins", metavar="PINS", nargs="*", help="pin file")

    return parser.parse_args(argv)


def repo_name(url):
    """Return the base repository name in url.   This is the name of
       the directory which would be created by `git clone url`"""
    return basename(url).rsplit(".git")[0]


def clone_jenkins(filename, gathered):
    """Print json file containing repositories to clone"""
    json_dict = {}
    for url, commitish in gathered:
        json_dict[repo_name(url)] = {'URL': url, 'commitish': commitish}
    with open(filename, "w") as clone_sources:
        clone_sources.write(json.dumps(json_dict))


def clone(url, destination, commitish, nodetached=True):
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

    # if we are assemblying a patchqueue or a
    # repatched component we care not being in
    # detached state, so we commit to a
    # planex/commitish branch as done previously
    if nodetached:
        local_branch = repo.create_head(branch_name, commit)
        local_branch.checkout()
    else:
        repo.git.checkout(commitish)

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


def clone_all(args, pin, nodetached=False):
    """
    If [args.jenkins] prints the clone string for jenkins else
    it clones all the clonable sources into [args.repos].
    """
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
        print('echo "Clones for %s"' % basename(pin.linkpath))

    # this is suboptimal but the sets are very small
    if any(commitish1 != commitish2
           for (url1, commitish1) in gathered
           for (url2, commitish2) in gathered
           if url1 == url2):
        sys.exit("error: cloning two git repositories with the same "
                 "name but different commitish is not supported.")

    if args.jenkins:
        clone_jenkins(args.output, gathered)
    else:
        for url, commitish in gathered:
            print('echo "Cloning %s#%s"' % (url, commitish))
            # clone is assumed for all other flags
            util.makedirs(args.repos)
            try:
                clone(url, args.repos, commitish, nodetached)
            except git.GitCommandError as gce:
                print(gce.stderr)


def assemble_patchqueue(args, pin):
    """
    Assemble patchqueues using Source0 and PatchQueue0 using
    the active branches in the cloned sources.
    """
    sources = {
        key: src['URL']
        for key, src in pin.sources.items()
        if src.get('commitish', False)
    }
    patchqueues = {
        key: (pq['URL'], dirname(pq['prefix']))
        for key, pq in pin.patchqueue_sources.items()
        if pq.get('commitish', False)
    }

    if 'Source0' not in sources:
        sys.exit("error: planex-clone requires Source0 to point to "
                 "a git repository.")
    if 'PatchQueue0' not in patchqueues:
        sys.exit("error: planex-clone requires PatchQueue0 to point "
                 "to a git repository.")

    if len(patchqueues.keys()) > 1:
        sys.exit(
            "error: planex-clone does not support the cloning and "
            "assembly of multiple sources and patchqueues, currently "
            "this case needs to be handled manually.")
    try:
        src_url = sources['Source0']
        pq_url, pq_prefix = patchqueues['PatchQueue0']
        src_repo = git.Repo(join(args.repos, repo_name(src_url)))
        pq_repo = git.Repo(join(args.repos, repo_name(pq_url)))
        apply_patchqueue(src_repo, pq_repo, pq_prefix)
        print(fill(
            "By default the PIN file will instruct `planex` to "
            "`git archive` the source repository and the patchqueue "
            "repository at the commitish specified in the pin file, "
            "then assemble the patchqueue when building the RPM.\n"
            "If you want to build using the HEAD of the source repository, "
            "where you have all your ongoing modifications applied, you "
            "can edit the pin file as follows: \n"
            "\t- delete the `PatchQueue0` section, and\n"
            "\t- set the correct commitish for `Source0` (usually the name "
            "of the active branch)."
        ))
    except git.GitCommandError as gce:
        print(gce.stderr)


def assemble_repatched(args, specpath, defines, pin):
    """
    Assemble an upstream centos package and apply the upstream patchqueue,
    then apply the local patchqueue.
    """
    sources = {
        key: (src['URL'], bool(src.get("commitish", False)))
        for key, src in pin.sources.items()
    }
    archives = {
        key: (arc['URL'], dirname(arc['prefix']),
              bool(arc.get("commitish", False)))
        for key, arc in pin.archives.items()
    }
    patchqueues = {
        key: (pq['URL'], dirname(pq['prefix']))
        for key, pq in pin.patchqueue_sources.items()
        if pq.get('commitish', False)
    }

    if 'Source0' not in sources:
        sys.exit("error: planex-clone requires Source0 to be specified.")
    if 'Archive0' not in archives:
        sys.exit("error: planex-clone requires Archive0 to be specified.")
    if 'PatchQueue0' not in patchqueues:
        sys.exit("error: planex-clone requires PatchQueue0 to point "
                 "to a git repository.")

    spec = planex.spec.load(specpath, link=pin,
                            check_package_name=True,
                            defines=defines)

    for source in (sources['Source0'], archives['Archive0']):
        if not source[1]:
            try:
                resource = spec.resource(source[0])
            except KeyError as exn:
                sys.exit("error: No source corresponding to %s" % exn)
            fetch_source_dispatch(resource, retries=1)

    # If the source is a tarball, we need to unpack it and
    # init it as a git repository
    if not sources['Source0'][1]:
        resource = spec.resource(sources['Source0'][0])
        reponame, _ = splitext(basename(specpath))
        repopath = join(args.repos, reponame)
        if not tarfile.is_tarfile(resource.path):
            sys.exit("error: invalid source at {}".format(resource.path))
        with tarfile.open(resource.path) as tar:
            tar.extractall(path=repopath)
        src_repo = git.Repo.init(repopath)
        src_repo.index.add([['*']])
        src_repo.index.commit("base")
    else:
        repopath = join(args.repos, repo_name(sources['Source0'][0]))
        src_repo = git.Repo(repopath)

    patches = sorted(
        ((kind, resource)
         for kind, resource in spec.resources_dict().items()
         if kind.startswith("Patch") and "Queue" not in kind),
        key=lambda kv: int(kv[0][5:])
    )
    patches = [basename(resource.path) for _, resource in patches]

    for patch in patches:
        print("Applying archive patch..{}".format(patch))
        patchpath = join("..",
                         repo_name(archives['Archive0'][0]),
                         archives['Archive0'][1],
                         patch)
        src_repo.git.apply('-p1', '--index', patchpath)
        src_repo.index.commit(basename(patch))
        print("Patch applied.")

    pq_name, pq_prefix = patchqueues['PatchQueue0']
    pq_repo = git.Repo(join(args.repos, repo_name(pq_name)))
    apply_patchqueue(src_repo, pq_repo, pq_prefix)


def main(argv=None):
    """
    Entry point
    """
    args = parse_args_or_exit(argv)

    for pinpath in args.pins:
        pin = Link(pinpath)

        if args.clone or args.jenkins:
            clone_all(args, pin)
        else:
            if "PatchQueue0" in pin.patchqueue_sources:
                if "Archive0" in pin.archives:
                    specname, _ = splitext(basename(pinpath))
                    specpath = "SPECS/{}.spec".format(specname)
                    defines = [
                        ("_topdir", "_build"),
                        ("_sourcedir", "%_topdir/SOURCES/%name")
                    ]
                    clone_all(args, pin, nodetached=True)
                    assemble_repatched(args, specpath, defines, pin)
                else:
                    clone_all(args, pin, nodetached=True)
                    assemble_patchqueue(args, pin)
            else:
                clone_all(args, pin)
