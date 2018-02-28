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

    def add_to_spec(self, spec, outfile):
        """
        Insert patches into spec, writing output to outfile
        """
        with open(outfile, "w") as specfile_out:
            expanded = expand_patchqueue(spec, self.series())
            specfile_out.writelines(expanded)


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


def rewrite_spec(spec, patches, patchnum):
    """
    Expand a patchqueue as a sequence of patches in a spec file
    """
    done = False
    for line in spec.spectext:
        yield line
        upper_line = line.upper()
        if not done and (
                (upper_line.startswith('SOURCE') and patchnum == -1) or
                (upper_line.startswith('PATCH%s' % patchnum))):
            for patch in patches:
                patchnum += 1
                yield "Patch%d: %s\n" % (patchnum, patch)
            done = True


def expand_patchqueue(spec, series):
    """
    Create a list of patches from a patchqueue and update the spec file
    """
    patches = list(series)
    patchnum = spec.highest_patch()
    found_autosetup = False
    for line in spec.spectext:
        if "-p1 in line" and (line.startswith("%autosetup") or
                              line.startswith("%autopatch")):
            found_autosetup = True
            break
    if not found_autosetup:
        raise SpecMissingAutosetup()
    return rewrite_spec(spec, patches, patchnum)
