"""
Wrappers and utility functions for dealing with git repositories
"""

import os
import re
import subprocess

from planex.util import run


def dotgitdir_of_path(repo):
    """
    Return the path to the dotgitdir of the repository.

    Possible paths: <repo>/.git, <repo> or <repo>.git

    """

    # We often have bare repos checked out, e.g. /path/to/xen-api.git,
    # which doesn't contain a '.git' dir inside. We want to support
    # specifying this by only by providing the path to the repo, or by
    # just specifying 'xen-api' and having this function check for
    # 'xen-api.git'
    possibilities = [os.path.join(repo, ".git"),
                     repo,
                     repo + ".git"]
    matches = [x for x in possibilities if
               os.path.exists(os.path.join(x, "HEAD"))]
    if matches:
        return matches[0]
    else:
        raise Exception("Not a git repository: '%s'" % repo)


def archive(repo, commit_hash, output, prefix=None):
    """
    Archive a git repo at a given commit with a specified version prefix.
    Returns the path to an archive to be used as a source for building an RPM.
    """
    dotgitdir = dotgitdir_of_path(repo)

    cmd = ["git", "--git-dir=%s" % dotgitdir, "archive", commit_hash]

    if prefix is not None:
        cmd += ["--prefix=%s-%s/" % (os.path.basename(repo), prefix)]
    subprocess.check_call(cmd, stdout=output)


def tags(repo):
    """
    Return a list of all tags defined on repo.
    """
    dotgitdir = dotgitdir_of_path(repo)
    return run(["git", "--git-dir=%s" % dotgitdir, "tag"])['stdout'].split()


def format_patch(repo, startref, endref, target_dir):
    """
    Write patches from ref to HEAD out to target_dir.
    Returns a list of patch filenames which can be used to create a
    series file.
    """
    dotgitdir = dotgitdir_of_path(repo)

    commit_range = "%s..%s" % (startref, endref)
    res = run(["git", "--git-dir=%s" % dotgitdir, "format-patch",
               "--no-renames", commit_range, "--output-directory", target_dir])
    return res['stdout'].split()


def origin_url(repo):
    """
    Return the remote url for origin
    """
    dotgitdir = dotgitdir_of_path(repo)

    res = run(['git', '--git-dir=%s' % dotgitdir, 'remote', '-v'])
    remotes = res['stdout'].strip()
    match = re.search(r'origin\s*(\S*)\s*\(fetch\)', remotes)

    return match.group(1).strip()


def ls_remote(url, ref=None, *options):
    """
    Run 'git ls-remote' command.
    """
    cmd = ['git', 'ls-remote'] + list(options) + [url]

    if ref is not None:
        cmd.append(ref)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, stderr = proc.communicate()

    if stderr:
        raise RuntimeError(stderr)

    return stdout
