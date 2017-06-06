"""
Classes for dealing with pin and link files
"""

import json


class Link(object):
    """Represents pinned or linked repository"""

    def __init__(self, path):
        with open(path) as fileh:
            self.link = json.load(fileh)

    @property
    def url(self):
        """Return the URL from which to fetch the patchqueue tarball"""
        return self.link.get('URL', None)

    @property
    def commitish(self):
        """Return the Git commitish to use when constructing patchqueue.
           Used mainly for pinning."""
        return self.link.get('commitish', None)

    @property
    def patchqueue(self):
        """Return the path to the patchqueue inside the patchqueue tarball"""
        return self.link.get('patchqueue', None)

    @property
    def sources(self):
        """Return the path to extra sources inside the patchqueue tarball"""
        return self.link.get('sources', None)

    @property
    def patches(self):
        """Return the path to extra patches inside the patchqueue tarball"""
        return self.link.get('patches', None)

    @property
    def base_commitish(self):
        """Return the commitish from which to fetch the patchqueue"""
        return self.link.get('base_commitish', None)

    @property
    def base(self):
        """Return the base repository on top of which to apply the
           patchqueue"""
        return self.link.get('base', None)
