"""
planex-patchqueue: Create a patchqueue containing the difference between
the tag pointed to by a spec file and a Git repository.
"""

import argparse
import os
import shutil
import tempfile

import argcomplete

from planex.link import Link
from planex.spec import Spec
import planex.git as git
import planex.tarball as tarball
import planex.util as util


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description='Create a patchqueue from a linked Git repository')
    util.add_common_parser_options(parser)
    parser.add_argument("link", metavar="LINK", help="link file")
    parser.add_argument("tarball", metavar="TARBALL", help="tarball")
    parser.add_argument("--keeptmp", action="store_true",
                        help="Do not clean up working directory")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv=None):
    """
    Entry point
    """
    args = parse_args_or_exit(argv)
    link = Link(args.link)

    # Repo and ending tag are specified in the link file
    repo = link.url
    end_tag = link.commitish
    if end_tag is None:
        end_tag = "HEAD"

    # Start tag is based on the version specified in the spec file,
    # but the tag name may be slightly different (v1.2.3 rather than 1.2.3)
    # If the link file does not list a spec file, assume that there is one in
    # the usual place
    if link.specfile is not None:
        spec_path = os.path.join(link.url, ".git/patches", link.specfile)
    else:
        basename = os.path.splitext(os.path.basename(args.link))[0]
        spec_path = os.path.join("SPECS", "%s.spec" % basename)
    spec = Spec(spec_path)

    start_tag = link.base_commitish
    if start_tag is None:
        start_tag = spec.version()
        if start_tag not in git.tags(repo):
            start_tag = "v%s" % start_tag

    try:
        # Assemble the contents of the patch queue in a temporary directory
        tmpdir = tempfile.mkdtemp()
        patchqueue = os.path.join(tmpdir, link.patchqueue)
        os.makedirs(patchqueue)
        patches = git.format_patch(repo, start_tag, end_tag, patchqueue)
        with open(os.path.join(patchqueue, "series"), "w") as series:
            for patch in patches:
                series.write(os.path.basename(patch) + "\n")

        # Archive the assembled patch queue
        tarball.make(tmpdir, args.tarball)

    finally:
        if args.keeptmp:
            print "Working directory retained at %s" % tmpdir
        else:
            shutil.rmtree(tmpdir)
