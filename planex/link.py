"""
Classes for dealing with pin and link files
"""

import json


class Link(object):
    """Represents pinned or linked repository"""

    def __init__(self, path):
        with open(path) as fileh:
            self.link = json.load(fileh)

    def patchqueue(self):
        """Return the patchqueue's patchqueue field"""
        return self.link.get('patchqueue', '')

    def patches(self):
        """Return the patchqueue's patches field"""
        return self.link.get('patches', '')
