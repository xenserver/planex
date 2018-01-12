"""
planex-make-srpm: Wrapper around rpmbuild
"""
from __future__ import print_function

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
import planex.cmd.args
from planex.spec import Spec
from planex.link import Link
from planex.patchqueue import Patchqueue
from planex.tarball import Tarball

PATCHQUEUES = 'patchqueues'
PATCHES = 'patches'


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description='Pack sources and patchqueues into a source RPM',
        parents=[planex.cmd.args.common_base_parser(),
                 planex.cmd.args.rpm_define_parser(),
                 planex.cmd.args.keeptmp_parser()])
    parser.add_argument("spec", metavar="SPEC", help="Spec file")
    parser.add_argument("sources", metavar="SOURCE/PATCHQUEUE", nargs='*',
                        help="Source and patchqueue files")
    argcomplete.autocomplete(parser)

    parsed_args = parser.parse_args(argv)
    links = [arg for arg in argv
             if arg.endswith(".lnk") or arg.endswith(".pin")]
    parsed_args.link = None
    if links:
        parsed_args.link = Link(links[0])

    parsed_args.patchdata = {}
    if parsed_args.link:
        link = parsed_args.link
        if link.schema_version == 1:
            patchqueues = [arg for arg in argv if arg.endswith("patches.tar")]
            if patchqueues:
                parsed_args.patchdata[PATCHES] = patchqueues
        else:
            parsed_args.patchdata[PATCHES] = []
            for patch in link.patch_sources:
                target = [arg for arg in argv if
                          arg.endswith('%s.tar' % (patch))]
                if target:
                    parsed_args.patchdata[PATCHES].append(target[0])

            parsed_args.patchdata[PATCHQUEUES] = []
            for patchqueue in link.patchqueue_sources:
                target = [arg for arg in argv if
                          arg.endswith('%s.tar' % (patchqueue))]
                if target:
                    parsed_args.patchdata[PATCHQUEUES].append(target[0])

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
        cmd.append(" ".join(define))
    cmd.append('--define')
    cmd.append('_sourcedir %s' % tmpdir)
    cmd.append('-bs')
    cmd.append(specfile)

    return subprocess.call(cmd)


def get_commit_id(info_file):
    """
    Read the commit id from the .gitarchive-info file
    """
    regex = re.compile(r'^Changeset: (.*)$')
    for line in info_file:
        match = regex.match(line)
        if match:
            changeset = match.group(1)
            # Skip if .gitarchive-info hasn't passed through `git archive`
            # rpm chokes in the following way:
            #   Illegal char '$' in: Provides: gitsha(source.tar) = $Format:%H$
            if changeset.startswith("$Format"):
                continue
            return changeset
    return None


def add_gitsha_provides(manifests):
    """
    Add the source line and additional provides to the current location
    """
    for key in manifests:
        print('Provides: gitsha({0}) = {1}'.format(key, manifests[key]))


def add_manifest_entry(manifests, specfile):
    """
    Add provides entries to the specfile that show the manifest data
    """
    # Have to do this in two passes, find the highest source and then
    # add one higher
    source = re.compile(r'^Source0: .*$')
    for line in fileinput.input(specfile, inplace=True):
        print(line, end="")
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


def extract_tarball_patches(tmpdir, spec, tarball, sources, patches):
    """ Extract a set of patches from a tarball """
    if sources is not None:
        for source in spec.local_sources():
            path = os.path.join(sources, source)
            tarball.extract(path, tmpdir)
    if patches is not None:
        for patch in spec.local_patches():
            path = os.path.join(patches, patch)
            tarball.extract(path, tmpdir)


def extract_v2_patches(tmpdir, spec, tmp_specfile, link, patchdata):
    """ Extract patches from a v2 lnk/pin file """
    if PATCHES in patchdata:
        patches = patchdata[PATCHES]
        for patchsource in link.patch_sources:
            tarname = '%s.tar' % patchsource
            patchset = [patch for patch in patches
                        if os.path.basename(patch) == tarname][0]
            with Tarball(patchset) as tarball:
                extract_tarball_patches(
                    tmpdir, spec, tarball, None,
                    link.patch_sources[patchsource]['patches'])

    if PATCHQUEUES in patchdata:
        patchqueues = patchdata[PATCHQUEUES]
        sources = link.patchqueue_sources
        for patchqueue in sources:
            tarname = '%s.tar' % patchqueue
            patchset = [pq for pq in patchqueues
                        if os.path.basename(pq) == tarname][0]
            with Patchqueue(patchset,
                            branch=sources[patchqueue]
                            ['patchqueue']) as patches:
                patches.extract_all(tmpdir)
                patches.add_to_spec(spec, tmp_specfile)


def populate_working_directory(tmpdir, spec, link, sources, patchdata):
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
        print("No .gitarchive-info found for {0}".format(spec))

    spec = Spec(tmp_specfile, check_package_name=False)

    # Expand patchqueue to working area, rewriting spec as needed
    if link:
        if link.schema_version == 1 and 'patches' in patchdata:
            patch_path = str(patchdata['patches'][0])
            # Extract patches
            if link.patchqueue is not None:
                print ('patches %s' % (patch_path))
                with Patchqueue(patch_path,
                                branch=link.patchqueue) as patches:
                    patches.extract_all(tmpdir)
                    patches.add_to_spec(spec, tmp_specfile)

            # Extract non-patchqueue sources
            with Tarball(patch_path) as tarball:
                extract_tarball_patches(tmpdir, spec, tarball, link.sources,
                                        link.patches)
        elif link.schema_version >= 2:
            extract_v2_patches(tmpdir, spec, tmp_specfile, link, patchdata)

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
                                              args.sources, args.patchdata)
        sys.exit(rpmbuild(args, tmpdir, specfile))

    except (tarfile.TarError, tarfile.ReadError) as exc:
        print("Error when extracting patchqueue from tarfile")
        print("Exception: %s" % exc)

    finally:
        # Clean temporary area (unless debugging)
        if args.keeptmp:
            print("Working directory retained at %s" % tmpdir)
        else:
            shutil.rmtree(tmpdir)
