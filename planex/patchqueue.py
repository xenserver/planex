"""
Utilities for handling patchqueues
"""

import re

import planex.tarball


class SpecMissingAutosetup(Exception):
    """Exception raised if the spec file is missing %autosetup -p1"""
    pass


class Patchqueue(object):
    """Represents a patchqueue archive"""
    def __init__(self, filename, branch="master"):
        self.filename = filename
        self.branch = branch
        self.tarball = planex.tarball.Tarball(self.filename, prefix=branch)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        """
        Close the patchqueue tarball
        """
        self.tarball.close()

    def series(self, guard=None):
        """
        Return a list of patches in the patchqueue
        """
        series = self.tarball.extractfile("series")
        return list(parse_patchseries(series, guard))

    def extract(self, source, dest):
        """
        Extract source from the patchqueue, saving it to dest
        """
        self.tarball.extract(source, dest)

    def extract_all(self, destdir):
        """
        Extract all patches from the patchqueue, saving to destdir
        """
        # Extract all patches into the tmpdir
        for patch in self.series():
            self.extract(patch, destdir)


def parse_patchseries(series, guard=None):
    """
    Parse series file and return the list of patches
    """
    guard_re = re.compile(r'([\S]+)(\s#.*)?')

    for line in series:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        match = guard_re.match(line)
        if match.group(2):
            gtype = match.group(2)[2]
            guard_patch = match.group(2)[3:]

            if gtype == '+' and guard != guard_patch:
                continue
            if gtype == '-' and guard == guard_patch:
                continue

        yield match.group(1)


def check_spec_supports_patchqueues(spec):
    """
    Create a list of patches from a patchqueue and update the spec file
    """
    # check specfile integrity for patchqueues
    if not any(line.startswith(r"%autosetup") or
               line.startswith(r"%autopatch")
               for line in spec.spectext):
        raise SpecMissingAutosetup(spec.path)
