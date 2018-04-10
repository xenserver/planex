"""
tarball: Utilities for tar archives
"""

import os
import tarfile


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

    def getnames(self):
        """
        Return a list of the names of the files in the tarball
        """
        source_path = os.path.join(self.archive_root, self.prefix)
        names = [mem.name for mem in self.tarfile.getmembers()
                 if mem.isfile() and mem.path.startswith(source_path)]
        return [os.path.relpath(name, source_path) for name in names]

    def extractfile(self, source):
        """
        Extract a file from the tarball, returning a file-like object
        """
        # Get the TarInfo object representing the file and re-set its
        # name.   Otherwise the file will be written to its full path.
        source_path = os.path.join(self.archive_root, self.prefix, source)
        return self.tarfile.extractfile(source_path)

    def extract(self, sources, destdir):
        """
        Extract the files listed in [sources] from the tarball,
        saving them to destdir.
        """
        # Get the TarInfo object representing the file and re-set its
        # name.   Otherwise the file will be written to its full path.
        if not sources:
            raise ValueError("Empty source list")

        source_paths = [os.path.join(self.archive_root, self.prefix, source) for source in sources]
        mems = [self.tarfile.getmember(source_path) for source_path in source_paths]
        for mem in mems:
            mem.name = os.path.basename(mem.name)
        self.tarfile.extractall(path=destdir, members=mems)
        for mem in mems:
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


def make(inputdir, outputfile, mode=None):
    """
    Create a new tarball named outputfile and recursively add all files
    in inputdir to it.
    """
    tarmode = "w"
    if mode is not None:
        tarmode += ":" + mode

    def reset(tarinfo):
        """
        Clean file ownership and naming when adding to archive
        """
        tarinfo.uid = 0
        tarinfo.gid = 0
        tarinfo.uname = "root"
        tarinfo.gname = "root"
        tarinfo.mtime = 0
        tarinfo.name = os.path.relpath(tarinfo.name, inputdir[1:])
        return tarinfo

    with tarfile.open(fileobj=outputfile, mode=tarmode) as tar:
        tar.add(inputdir, filter=reset)
