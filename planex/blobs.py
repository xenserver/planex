"""Classes for handling different kind of datablobs in the spec."""
from __future__ import print_function

import os
import shutil

# pylint: disable=relative-import
from six.moves.urllib.parse import urlparse

import planex.patchqueue
from planex.macros import nevra, rpm, rpm_macros, expandmacros
from planex.tarball import Tarball


class Blob(object):
    """
    A file which will be packed into the SRPM.   The file is treated
    as an opaque blob - the tools will not look inside it.
    """

    def __init__(self, spec, url, defined_by):
        with rpm_macros(spec.macros, nevra(spec.spec.sourceHeader)):
            self._spec = spec
            self._url = rpm.expandMacro(url)
            self._defined_by = defined_by

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __contains__(self, name):
        return os.path.basename(name) == os.path.basename(self.path)

    @property
    def is_repo(self):
        """Return if the blob represents a git repository"""
        return False

    @property
    def spec(self):
        """Return the spec which contains this resource"""
        return self._spec

    @property
    def basename(self):
        """Return the basename of this resource"""
        return os.path.basename(self.url)

    @property
    @expandmacros
    def url(self):
        """Return the URL of this resource"""
        return self._url

    @property
    def defined_by(self):
        """Return the name of file which defined this resource"""
        return self._defined_by

    @property
    @expandmacros
    def path(self):
        """ Return the local path to this resource"""

        # RPM only looks at the basename part of the Source URL - the
        # part after the rightmost /.   We must match this behaviour.
        #
        # Examples:
        #    http://www.example.com/foo/bar.tar.gz -> bar.tar.gz
        #    http://www.example.com/foo/bar.cgi#/baz.tbz -> baz.tbz

        return os.path.join("%_sourcedir", os.path.basename(self.url))

    @property
    def is_fetchable(self):
        """
        Return True if the resource can be fetched.
        A resource can be fetched if its URL points to a remote
        server or the URL is a plain path to a file which exists
        on the local machine.
        """
        return (urlparse(self.url).netloc not in ['', 'file'] or
                os.path.isfile(self.url))

    def extract_source(self, name, destdir):
        """
        Extract source 'name' to destdir.   Raises KeyError if the
        requested source cannot be found.
        """
        # For a file, extract_source copies the whole file to the
        # destination without unpacking it.
        if name not in self:
            raise KeyError(name)
        shutil.copyfile(self.path,
                        os.path.join(destdir, os.path.basename(name)))

    def extract_sources(self, names, destdir):
        """
        Extract all the source [names] to [destdir].   Raises [KeyError]
        for the first requested source that cannot be found.
        """
        for name in names:
            self.extract_source(name, destdir)

    @property
    def force_rebuild(self):
        """
        True if this source should always be re-fetched.
        Used for pinned sources which should be recreated
        from their repositories for each build.
        """
        return False


class GitBlob(Blob):
    """
    A blob produced from a local repository.   The blob is a tarball
    produced by `git archive` but the tools will not look inside it.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, spec, url, defined_by, prefix, commitish):
        with rpm_macros(spec.macros, nevra(spec.spec.sourceHeader)):
            super(GitBlob, self).__init__(spec, url, defined_by)
            self._prefix = rpm.expandMacro(prefix) if prefix is not None \
                else rpm.expandMacro("%{name}-%{version}")
            self._commitish = rpm.expandMacro(commitish)

    @property
    def is_repo(self):
        """Return if the blob represents a git repository"""
        return True

    @property
    @expandmacros
    def prefix(self):
        """Return the directory prefix of files in this resource"""
        return os.path.normpath(self._prefix) + "/" \
            if self._prefix is not None else None

    @property
    @expandmacros
    def commitish(self):
        """Return the commitish to fetch for this resource"""
        return self._commitish

    @property
    @expandmacros
    def path(self):
        """ Return the local path to this resource"""

        # RPM only looks at the basename part of the Source URL - the
        # part after the rightmost /.   We must match this behaviour.
        #
        # Examples:
        #    ssh://git@www.example.com/foo/bar.git -> bar.tar.gz

        (name, _) = os.path.splitext(os.path.basename(self.url))
        return os.path.join("%_sourcedir", "{}.tar.gz".format(name))

    @property
    def force_rebuild(self):
        """
        True if this source should always be re-fetched.
        Pinned sources which should be recreated from their repositories
        for each build.
        """
        return True


class Archive(Blob):
    """A tarball archive which will be unpacked into the SRPM"""

    def __init__(self, spec, url, defined_by, prefix):
        with rpm_macros(spec.macros, nevra(spec.spec.sourceHeader)):
            super(Archive, self).__init__(spec, url, defined_by)
            self._prefix = rpm.expandMacro(prefix)
        self._names = None

    def __contains__(self, name):
        # the extraction of the names is delayed as we may not yet
        # have downloaded the Archive at the time of creating the
        # object
        if self._names is None:
            with Tarball(self.path) as tarball:
                self._names = [os.path.basename(n) for n in tarball.getnames()]
        return name in self._names

    @property
    @expandmacros
    def prefix(self):
        """Return the directory prefix of files in this resource"""
        return os.path.normpath(self._prefix) + "/"

    @property
    @expandmacros
    def path(self):
        """ Return the local path to this resource"""

        # RPM only looks at the basename part of the Source URL - the
        # part after the rightmost /.   We must match this behaviour.
        #
        # Examples:
        #    http://www.example.com/foo/bar.tar.gz -> bar.tar.gz
        #    http://www.example.com/foo/bar.cgi#/baz.tbz -> baz.tbz

        return os.path.join("%_sourcedir", "{}".format(self.basename))

    def extract_source(self, name, destdir):
        """
        Extract source 'name' to destdir.   Raises KeyError if the
        requested source cannot be found.
        """
        # For an archive, extract_source extracts the file from the archive
        # and writes it to the destination.
        with Tarball(self.path) as tarball:
            target_path = os.path.normpath(os.path.join(self.prefix, name))
            tarball.extract((target_path,), destdir)

    def extract_sources(self, names, destdir):
        """
        Extract all the source [names] to [destdir].   Raises [KeyError]
        for the first requested source that cannot be found.
        """
        with Tarball(self.path) as tarball:
            target_paths = [
                os.path.normpath(os.path.join(self.prefix, name))
                for name in names
            ]
            tarball.extract(target_paths, destdir)


class GitArchive(Archive):
    """
    An archive produced from a local repository.   The blob is a tarball
    produced by `git archive`.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, spec, url, defined_by, prefix, commitish):
        with rpm_macros(spec.macros, nevra(spec.spec.sourceHeader)):
            super(GitArchive, self).__init__(spec, url, defined_by, prefix)
            self._prefix = rpm.expandMacro(prefix)
            self._commitish = rpm.expandMacro(commitish)

    @property
    def is_repo(self):
        """Return if the blob represents a git repository"""
        return True

    @property
    @expandmacros
    def commitish(self):
        """Return the commitish to fetch for this resource"""
        return self._commitish

    @property
    @expandmacros
    def path(self):
        """ Return the local path to this resource"""

        # RPM only looks at the basename part of the Source URL - the
        # part after the rightmost /.   We must match this behaviour.
        #
        # Examples:
        #    ssh://git@www.example.com/foo/bar.git -> bar.tar.gz

        (name, _) = os.path.splitext(os.path.basename(self.url))
        return os.path.join("%_sourcedir", "{}.tar.gz".format(name))

    @property
    def force_rebuild(self):
        """
        True if this source should always be re-fetched.
        Pinned sources which should be recreated from their repositories
        for each build.
        """
        return True


class Patchqueue(Archive):
    """A patchqueue archive which will be unpacked into the SRPM"""

    def __contains__(self, patch):
        # As for the Archive class, this should never be called
        # before the archive has been fetched
        return patch in self.series()

    def series(self):
        """Return the contents of the patchqueue's series file"""
        # we cache the extraction of the series to speet up the
        # self.__contains__ method
        if self._names is None:
            with planex.patchqueue.Patchqueue(self.path, self.prefix) as queue:
                self._names = queue.series()
        return self._names


class GitPatchqueue(Patchqueue):
    """
    A patchqueue produced from a local repository.   The blob is a tarball
    produced by `git archive`.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, spec, url, defined_by, prefix, commitish):
        with rpm_macros(spec.macros, nevra(spec.spec.sourceHeader)):
            super(GitPatchqueue, self).__init__(spec, url, defined_by, prefix)
            self._prefix = rpm.expandMacro(prefix)
            self._commitish = rpm.expandMacro(commitish)

    @property
    def is_repo(self):
        """Return if the blob represents a git repository"""
        return True

    @property
    @expandmacros
    def commitish(self):
        """Return the commitish to fetch for this resource"""
        return self._commitish

    @property
    @expandmacros
    def path(self):
        """ Return the local path to this resource"""

        # RPM only looks at the basename part of the Source URL - the
        # part after the rightmost /.   We must match this behaviour.
        #
        # Examples:
        #    ssh://git@www.example.com/foo/bar.pg.git -> bar.pg.tar.gz

        (name, _) = os.path.splitext(os.path.basename(self.url))
        return os.path.join("%_sourcedir", "{}.tar.gz".format(name))

    @property
    def force_rebuild(self):
        """
        True if this source should always be re-fetched.
        Pinned sources which should be recreated from their repositories
        for each build.
        """
        return True
