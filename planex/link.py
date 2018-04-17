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
        schema_version = self.link.get('SchemaVersion', None)
        if schema_version is None:
            raise UnsupportedProperty("SchemaVersion field is not present")
        schema_version = int(schema_version)
        if schema_version == 1:
            raise UnsupportedProperty("SchemaVersion 1 is no longer supported")
        return schema_version

    @property
    def ignore_autosetup(self):
        """Return the ignore autosetup value"""
        ignore_autosetup = self.link.get('IgnoreAutosetup', False)
        if not isinstance(ignore_autosetup, bool):
            raise ValueError(ignore_autosetup)
        return ignore_autosetup

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
    def sources(self):
        """Return the path to extra sources inside the patchqueue tarball"""
        patch_matcher = re.compile(r'^source\d*$', re.IGNORECASE)
        return {k: v for k, v
                in self.link.iteritems()
                if patch_matcher.match(k)}

    @property
    def patch_sources(self):
        """Return the ordered set of patch source definitions"""
        if self.schema_version > 2:
            raise UnsupportedProperty(
                "patchX is supported only in SchemaVersion 2")

        patch_matcher = re.compile(r'^patch\d*$', re.IGNORECASE)
        return {k: v for k, v
                in self.link.iteritems()
                if patch_matcher.match(k)}

    @property
    def patchqueue_sources(self):
        """Return the ordered set of patchqueue definitions"""
        patch_matcher = re.compile(r'^patchqueue\d*$', re.IGNORECASE)
        return {k: v for k, v
                in self.link.iteritems()
                if patch_matcher.match(k)}

    @property
    def has_patches(self):
        """ Test if the lnk defines patches """
        return self.patch_sources or self.patchqueue_sources
