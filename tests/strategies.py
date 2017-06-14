"""
Hypothesis strategies, used to generate data for property-based
testing of Planex modules.
"""

from collections import namedtuple
import os
import random
import string

from hypothesis import strategies as st


class File(object):
    """
    Represents a standard file with a name and some content.
    If no content is provided, random data is used.
    """

    def __init__(self, name, content=None):
        self.name = name
        self._content = content

    def __repr__(self):
        return "File(%r, %r)" % (self.name, self.content)

    @property
    def content(self):
        """
        Return the file's content.   If no content was provided when
        the object was created, random content will be generated lazily.
        """
        # rpmbuild complains if source files are less than 13 bytes.
        # Generating these bytes with hypothesis is expensive, and
        # this effort is wasted if they are not used, so we will
        # generate them lazily.   We use a random string so it is
        # easy to verify that a file was properly copied into an
        # RPM.
        if self._content is None:
            self._content = "".join(random.sample(string.printable, 20))
        return self._content

    def write(self, directory):
        """
        Write content to a file in directory.
        """
        path = open(os.path.join(directory, self.name))
        with open(path, "w") as out:
            out.writelines(self.content)
        return path


class Patch(namedtuple("Patch", "patch guards")):
    """Represents a patch with optional guards"""
    def __str__(self):
        entry = self.patch.name
        if self.guards:
            entry += " #%s" % ",".join([str(g) for g in self.guards])
        return entry

    def has_negative_guards(self):
        """Return true if the patch has any negative guards"""
        return any([g.sign == '-' for g in self.guards])

    def has_positive_guards(self):
        """Return true if the patch has any positive guards"""
        return any([g.sign == '+' for g in self.guards])

    def write(self, directory):
        """Write contents of the patch out to a file in the given
        directory"""
        return self.patch.write(directory)


class Guard(namedtuple("Guard", "sign label")):
    """Represents a patch guard"""
    def __str__(self):
        return self.sign + self.label


class PatchQueue(namedtuple("PatchQueue", "patches")):
    """Represents a patchqueue"""
    def __str__(self):
        return self.series()

    def series(self):
        """Return the PatchQueue's series file."""
        return "\n".join([str(p) for p in self.patches])


def files():
    """Returns a strategy which generates a File object with random
    contents.
    """
    return st.builds(File, st.text(alphabet="abcdefghijklmnopqrstuvwxyz",
                                   min_size=1, max_size=5))


def guard_names():
    """Returns a strategy which generates a patchqueue guard name.
    """
    return st.sampled_from(["alpha", "bravo", "charlie", "delta"])


def guards():
    """Returns a strategy which generates a patchqueue guard.
    """
    return st.builds(Guard, st.sampled_from(["+", "-"]), guard_names())


def patches():
    """Returns a strategy which generates a Patch object.
    At present, planex.patchqueue.Patchqueue only supports a single
    guard on each patch.
    """
    # If support for multiple guards is added, the max_size constraint
    # can be increased.
    return st.builds(Patch, files(), st.sets(guards(), min_size=0, max_size=1))


def patchqueues():
    """Returns a strategy which generates a PatchQueue object containing
    a list of uniquely-named Patch objects.
    """
    return st.builds(PatchQueue,
                     st.lists(patches(),
                              unique_by=lambda x: x.patch.name,
                              max_size=5))
