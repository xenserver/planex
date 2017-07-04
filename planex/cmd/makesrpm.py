"""
planex-make-srpm: Wrapper around rpmbuild
"""

import sys
import subprocess
import fileinput
import os
import re
import shutil
import tarfile
import tempfile

import argparse
import argcomplete
from planex.cmd.args import add_common_parser_options
from planex.spec import Spec
from planex.link import Link
from planex.patchqueue import Patchqueue
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


def get_commit_id(info_file):
    """
    Read the commit id from the .gitarchive-info file
    """
    changeset = re.compile(r'^Changeset: (.*)$')
    for line in info_file:
        match = changeset.match(line)
        if match:
            changeset = match.group(1)
            return changeset
    return None


def add_gitsha_provides(manifests):
    """
    Add the source line and additional provides to the current location
    """
    for key in manifests:
        print 'Provides: gitsha({0}) = {1}'.format(key, manifests[key])


def add_manifest_entry(manifests, specfile):
    """
    Add provides entries to the specfile that show the manifest data
    """
    # Have to do this in two passes, find the highest source and then
    # add one higher
    source = re.compile(r'^Source0: .*$')
    for line in fileinput.input(specfile, inplace=True):
        print line,
        match = source.match(line)
        if match:
            add_gitsha_provides(manifests)


def extract_commit(source, manifests):
    """
    Try to extract git archive information from a source entry
    """
    if tarfile.is_tarfile(source):
        with Tarball(source) as tarball:
            try:
                archive_info = tarball.extractfile('.gitarchive-info')
                if archive_info:
                    name = os.path.basename(source)
                    origin_name = '{0}.origin'.format(source)
                    if os.path.exists(origin_name):
                        with open(origin_name, 'r') as origin_file:
                            name = origin_file.readline()
                    manifests[name.strip()] = get_commit_id(archive_info)
            except KeyError:
                pass


def populate_working_directory(tmpdir, spec, link, sources, patchqueue):
    """
    Build a working directory containing everything needed to build the SRPM.
    """
    # Copy spec to working area
    tmp_specfile = os.path.join(tmpdir, os.path.basename(spec))
    shutil.copyfile(spec, tmp_specfile)

    manifests = {}

    # Copy sources to working area
    for source in sources:
        extract_commit(source, manifests)
        shutil.copy(source, tmpdir)

    if manifests:
        add_manifest_entry(manifests, tmp_specfile)
    else:
        print "No .gitarchive-info found for {0}".format(spec)

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
    tmpdir = tempfile.mkdtemp(prefix="px-srpm-")

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
