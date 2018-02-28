"""
Classes for dealing with pin and link files
"""

import json
import re


class UnsupportedProperty(RuntimeError):
    """ Error to be raised if we're asked for properties not present in this
    schema version
    """
    pass


class Link(object):
    """Represents pinned or linked repository"""

    def __init__(self, path):
        self.path = path
        with open(path) as fileh:
            self.link = json.load(fileh)

    @property
    def schema_version(self):
        """Return the schema version of the link file"""
        # Default to v1 if not present, for legacy lnks
        return int(self.link.get('SchemaVersion', 1))

    @property
    def linkpath(self):
        """Return the path to the link file"""
        return self.path

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
        if self.schema_version > 1:
            raise UnsupportedProperty('patchqueue only supported on v1')
        return self.link.get('patchqueue', None)

    @property
    def sources(self):
        """Return the path to extra sources inside the patchqueue tarball"""
        if self.schema_version < 2:
            return self.link.get('sources', None)

        patch_matcher = re.compile(r'source\d+', re.IGNORECASE)
        return {k: v for k, v
                in self.link.iteritems()
                if patch_matcher.match(k)}

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

    @property
    def patch_sources(self):
        """Return the ordered set of patch source definitions"""
        if self.schema_version < 2:
            raise UnsupportedProperty('patch_sources requries at least'
                                      'schema version 2')

        patch_matcher = re.compile(r'patch\d+', re.IGNORECASE)
        return {k: v for k, v
                in self.link.iteritems()
                if patch_matcher.match(k)}

    @property
    def patchqueue_sources(self):
        """Return the ordered set of patchqueue definitions"""
        if self.schema_version < 2:
            raise UnsupportedProperty('patchqueue_sources requries at least'
                                      'schema version 2')

        patch_matcher = re.compile(r'patchqueue\d+', re.IGNORECASE)
        return {k: v for k, v
                in self.link.iteritems()
                if patch_matcher.match(k)}

    @property
    def has_patches(self):
        """ Test if the lnk defines patches """
        return ((self.schema_version == 1 and self.patches is not None) or
                (self.schema_version >= 2 and
                 (self.patch_sources or self.patchqueue_sources)))
