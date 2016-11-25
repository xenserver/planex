"""
planex-make-srpm: Wrapper around rpmbuild
"""

import sys
import subprocess
import os
import shutil
import tarfile
import tempfile

import argparse
import argcomplete
from planex.util import add_common_parser_options
from planex.spec import Spec
from planex.link import Link
from planex.patchqueue import Patchqueue
from planex.tarball import extract_topdir
from planex.tarball import Tarball


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description='Pack sources and patchqueues into a source RPM')
    add_common_parser_options(parser)
    parser.add_argument("spec", metavar="SPEC", help="Spec file")
    parser.add_argument("sources", metavar="SOURCE/PATCHQUEUE", nargs='*',
                        help="Source and patchqueue files")
    parser.add_argument(
        "-D", "--define", default=[], action="append",
        help="--define='MACRO EXPR' define MACRO with value EXPR")
    parser.add_argument(
        "--keeptmp", action="store_true",
        help="keep temporary files")
    argcomplete.autocomplete(parser)

    parsed_args = parser.parse_args(argv)
    links = [arg for arg in argv
             if arg.endswith(".lnk") or arg.endswith(".pin")]
    parsed_args.link = None
    if links:
        parsed_args.link = Link(links[0])

    patchqueues = [arg for arg in argv if arg.endswith("patches.tar")]
    parsed_args.patchqueue = None
    if patchqueues:
        parsed_args.patchqueue = patchqueues[0]

    return parsed_args


def rpmbuild(args, tmpdir, specfile):
    """
    Run rpmbuild on working directory
    """
    cmd = ['rpmbuild']
    if args.quiet:
        cmd.append('--quiet')
    for define in args.define:
        cmd.append('--define')
        cmd.append(define)
    cmd.append('--define')
    cmd.append('_sourcedir %s' % tmpdir)
    cmd.append('-bs')
    cmd.append(specfile)

    return subprocess.call(cmd)


def populate_working_directory(tmpdir, spec, link, sources, patchqueue):
    """
    Build a working directory containing everything needed to build the SRPM.
    """
    # Copy spec to working area
    tmp_specfile = os.path.join(tmpdir, os.path.basename(spec))
    shutil.copyfile(spec, tmp_specfile)

    # Copy sources to working area, rewriting spec as needed
    tarball_filters = ['.tar.gz', '.tar.bz2']
    for source in sources:
        if any([ext in source for ext in tarball_filters]):
            extract_topdir(tmp_specfile, source)
        shutil.copy(source, tmpdir)

    spec = Spec(tmp_specfile, check_package_name=False)

    # Expand patchqueue to working area, rewriting spec as needed
    if link and patchqueue:
        # Extract patches
        if link.patchqueue is not None:
            with Patchqueue(patchqueue,
                            branch=link.patchqueue) as patches:
                patches.extract_all(tmpdir)
                patches.add_to_spec(spec, tmp_specfile)

        # Extract non-patchqueue sources
        with Tarball(patchqueue) as tarball:
            if link.sources is not None:
                for source in spec.local_sources():
                    path = os.path.join(link.sources, source)
                    tarball.extract(path, tmpdir)
            if link.patches is not None:
                for patch in spec.local_patches():
                    path = os.path.join(link.patches, patch)
                    tarball.extract(path, tmpdir)

    return tmp_specfile


def main(argv=None):
    """
    Entry point
    """
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args_or_exit(argv)
    tmpdir = tempfile.mkdtemp()

    try:
        specfile = populate_working_directory(tmpdir, args.spec, args.link,
                                              args.sources, args.patchqueue)
        sys.exit(rpmbuild(args, tmpdir, specfile))

    except (tarfile.TarError, tarfile.ReadError) as exc:
        print "Error when extracting patchqueue from tarfile"
        print "Exception: %s" % exc

    finally:
        # Clean temporary area (unless debugging)
        if args.keeptmp:
            print "Working directory retained at %s" % tmpdir
        else:
            shutil.rmtree(tmpdir)
