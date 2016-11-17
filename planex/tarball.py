"""
tarball: Utilities for tar archives
"""

import fileinput
import logging
import os
import sys
import tarfile

import planex.util as util


class Tarball(object):
    """Represents a source archive tarball"""
    def __init__(self, filename=None, fileobj=None, prefix=""):
        self.filename = filename
        self.tarfile = tarfile.open(name=filename, fileobj=fileobj)
        self.archive_root = archive_root(self.tarfile)
        self.prefix = prefix

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        """
        Close the tarball
        """
        self.tarfile.close()

    def extractfile(self, source):
        """
        Extract a file from the tarball, returning a file-like object
        """
        # Get the TarInfo object representing the file and re-set its
        # name.   Otherwise the file will be written to its full path.
        source_path = os.path.join(self.archive_root, self.prefix, source)
        return self.tarfile.extractfile(source_path)

    def extract(self, source, destdir):
        """
        Extract a file from the tarball, saving it to destdir.
        """
        # Get the TarInfo object representing the file and re-set its
        # name.   Otherwise the file will be written to its full path.
        source_path = os.path.join(self.archive_root, self.prefix, source)
        mem = self.tarfile.getmember(source_path)
        mem.name = os.path.basename(source_path)
        self.tarfile.extract(mem, destdir)
        os.utime(os.path.join(destdir, mem.name), None)


def archive_root(tar):
    """
    Return the name of the top level directory of the tarball
    """
    names = tar.getnames()
    topname = os.path.commonprefix(names)
    if topname in names:
        top_element = tar.getmember(topname)
        if top_element.isdir():
            return topname
    return ''


def extract_topdir(tmp_specfile, source):
    """
    Set the topdir name taken from the source tarball
    """
    for line in fileinput.input(tmp_specfile, inplace=True):
        if 'autosetup' in line:
            tar = tarfile.open(source)
            names = tar.getnames()
            topname = os.path.commonprefix(names)
            if topname in names:
                top_element = tar.getmember(topname)
                if top_element.isdir():
                    print "%s -n %s" % (line.strip(), topname)
            else:
                print "%s -c" % line.strip()
        else:
            print line,


def extract_file(tar, name_in, name_out):
    """
    Extract a file from a tarball
    """
    logging.debug("Extracting %s to %s", name_in, name_out)
    if name_in not in tar.getnames():
        sys.exit("%s: %s not found in archive" % (sys.argv[0], name_in))
    mem = tar.getmember(name_in)
    mem.name = os.path.basename(name_out)
    tar.extract(mem, os.path.dirname(name_out))
    os.utime(name_out, None)


def make(inputdir, outputfile):
    """
    Create a new tarball named outputfile and recursively add all files
    in inputdir to it.
    """
    tarmode = "w"
    if outputfile.endswith("gz"):
        tarmode += ":gz"
    if outputfile.endswith("bz2"):
        tarmode += ":bz2"

    def reset(tarinfo):
        """
        Clean file ownership and naming when adding to archive
        """
        tarinfo.uid = 0
        tarinfo.gid = 0
        tarinfo.uname = "root"
        tarinfo.gname = "root"
        tarinfo.name = os.path.relpath(tarinfo.name, inputdir[1:])
        return tarinfo

    util.makedirs(os.path.dirname(outputfile))
    with tarfile.open(outputfile, mode=tarmode) as tar:
        tar.add(inputdir, filter=reset)
