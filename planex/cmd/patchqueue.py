"""
planex-patchqueue: Create a patchqueue containing the difference between
the tag pointed to by a spec file and a Git repository.
"""

import argparse
import os
import shutil
import sys
import tempfile
from urlparse import urlparse

import argcomplete

from planex.fileupdate import FileUpdate
from planex.link import Link
from planex.spec import Spec
import planex.git as git
import planex.tarball as tarball
import planex.util as util
from planex.cmd.args import add_common_parser_options


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description='Create a patchqueue from a linked Git repository')
    add_common_parser_options(parser)
    parser.add_argument("link", metavar="LINK", help="link file")
    parser.add_argument("tarball", metavar="TARBALL", help="tarball")
    parser.add_argument("--repos", default="repos",
                        help="Local repository directory")
    parser.add_argument("--keeptmp", action="store_true",
                        help="Do not clean up working directory")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def copy_to_tmpdir(tmpdir, source, dest):
    """
    Copy source to dest in tmpdir
    """
    dest_path = os.path.join(tmpdir, dest)
    util.makedirs(os.path.dirname(dest_path))
    shutil.copyfile(source, dest_path)


def assemble_patchqueue(tmpdir, link, repo, start_tag, end_tag):
    """
    Assemble the contents of the patch queue in a temporary directory
    """
    patchqueue = os.path.join(tmpdir, link.patchqueue)
    os.makedirs(patchqueue)
    patches = git.format_patch(repo, start_tag, end_tag, patchqueue)
    with open(os.path.join(patchqueue, "series"), "w") as series:
        for patch in patches:
            series.write(os.path.basename(patch) + "\n")


def assemble_extra_sources(tmpdir, repo, spec, link):
    """
    Assemble the non-patchqueue sources in the working directory.
    """
    if link.sources is not None:
        for source in spec.local_sources():
            source_path = os.path.join(repo, link.sources, source)
            dest_path = os.path.join(link.sources, source)
            copy_to_tmpdir(tmpdir, source_path, dest_path)

    if link.patches is not None:
        for patch in spec.local_patches():
            source_path = os.path.join(repo, link.patches, patch)
            dest_path = os.path.join(tmpdir, link.patches, patch)
            copy_to_tmpdir(tmpdir, source_path, dest_path)


def main(argv=None):
    """
    Entry point
    """
    args = parse_args_or_exit(argv)
    util.setup_logging(args)
    link = Link(args.link)

    # Repo and ending tag are specified in the link file
    repo = link.url
    end_tag = link.commitish
    if end_tag is None:
        end_tag = "HEAD"

    # If the repository URL in the link is remote, look for a
    # local clone in repos (without a .git suffix)
    url = urlparse(repo)
    if url.scheme:
        reponame = os.path.basename(url.path).rsplit(".git")[0]
        repo = os.path.join(args.repos, reponame)

    util.makedirs(os.path.dirname(args.tarball))
    with open('{0}.origin'.format(args.tarball), 'w') as origin_file:
        origin_file.write('{0}\n'.format(git.origin_url(repo)))

    if repo.endswith(".pg"):
        with FileUpdate(args.tarball) as outfile:
            git.archive(repo, end_tag, outfile)
        sys.exit(0)

    # Start tag is based on the version specified in the spec file,
    # but the tag name may be slightly different (v1.2.3 rather than 1.2.3)
    # If the link file does not list a spec file, assume that there is one in
    # the usual place
    basename = os.path.splitext(os.path.basename(args.link))[0]
    spec_path = os.path.join("SPECS", "%s.spec" % basename)
    spec = Spec(spec_path)

    start_tag = link.base_commitish
    if start_tag is None:
        start_tag = spec.version()
        if start_tag not in git.tags(repo):
            start_tag = "v%s" % start_tag

    try:
        tmpdir = tempfile.mkdtemp(prefix="px-pq-")
        assemble_patchqueue(tmpdir, link, repo, start_tag, end_tag)
        assemble_extra_sources(tmpdir, repo, spec, link)
        with FileUpdate(args.tarball) as outfile:
            tarball.make(tmpdir, outfile)

    finally:
        if args.keeptmp:
            print "Working directory retained at %s" % tmpdir
        else:
            shutil.rmtree(tmpdir)
