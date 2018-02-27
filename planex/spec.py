"""Classes for handling RPM spec files.   The classes defined here
   are mostly just wrappers around rpm.rpm, adding information which
   the rpm library does not currently provide."""
from __future__ import print_function

import contextlib
import os
import re
import urlparse
import shutil
import sys
import tempfile

import rpm

from planex.tarball import Tarball
import planex.patchqueue


@contextlib.contextmanager
def rpm_macros(*macros):
    """
    Context manager to add and remove stacked RPM macro 'environments'.
    Macro definitions which occur later in 'macros' override definitions
    made earlier.
    """
    for macro in macros:
        for key, value in macro.items():
            rpm.addMacro(key, value)
    yield
    for macro in reversed(macros):
        for key in macro.keys():
            rpm.delMacro(key)


def nevra(package):
    """
    Returns a dictionary of macro definitions for the Name, Epoch, Version,
    Release and Architecture of package.   This dictionary can be passed to
    rpm_macros() to set up an appropriate environment for macro expansion.
    """
    return {
        'name':    package['name'],
        'epoch':   str(package['epoch'] or 1),
        'version': package['version'],
        'release': package['release'],
        'arch':    package['arch']
    }


class SpecNameMismatch(Exception):
    """Exception raised when a spec file's name does not match the name
       of the package defined within it"""
    pass


def parse_spec_quietly(path):
    """
    Parse spec file at 'path' and return an rpm.spec object.
    This function suppresses any errors about missing sources which
    librpm writes to stderr.
    """
    with tempfile.TemporaryFile() as nullfh:
        try:
            # collect all output to stderr then filter out
            # errors about missing sources
            errcpy = os.dup(2)
            try:
                os.dup2(nullfh.fileno(), 2)
                return rpm.ts().parseSpec(path)
            finally:
                os.dup2(errcpy, 2)
                os.close(errcpy)

        except ValueError as exn:
            nullfh.seek(0, os.SEEK_SET)
            # https://github.com/PyCQA/pylint/issues/1435
            # pylint: disable=E1133
            for line in nullfh:
                line = line.strip()
                if not line.endswith(': No such file or directory'):
                    print(line, file=sys.stderr)
            exn.args = (exn.args[0].rstrip() + ' ' + path, )
            raise


def expandmacros(func):
    """Decorator to expand RPM macros in strings"""
    def func_wrapper(self):
        """Decorator wrapper"""
        with rpm_macros(self.spec.macros, nevra(self.spec.spec.sourceHeader)):
            return rpm.expandMacro(func(self))
    return func_wrapper


class File(object):
    """A file which will be packed into the SRPM"""

    def __init__(self, spec, name, url, defined_by):
        self._spec = spec
        self._name = name
        self._url = url
        self._defined_by = defined_by

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @property
    def spec(self):
        """Return the spec which contains this resource"""
        return self._spec

    @property
    def name(self):
        """Return the name of this resource"""
        return self._name

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
        return (urlparse.urlparse(self.url).netloc not in ['', 'file'] or
                os.path.isfile(self.url))

    def extract_source(self, name, destdir):
        """
        Extract source 'name' to destdir.   Raises KeyError if the
        requested source cannot be found.
        """
        # For a file, extract_source copies the whole file to the
        # destination without unpacking it.
        if os.path.basename(name) != os.path.basename(self.path):
            raise KeyError(name)
        shutil.copyfile(self.path,
                        os.path.join(destdir, os.path.basename(name)))

    @property
    def force_rebuild(self):
        """
        True if this source should always be re-fetched.
        Used for pinned sources which should be recreated
        from their repositories for each build.
        """
        return False


class GitArchive(File):
    """An archive produced from a local repository"""

    def __init__(self, spec, name, url, defined_by, prefix, commitish):
        super(GitArchive, self).__init__(spec, name, url, defined_by)
        self._prefix = prefix
        self._commitish = commitish

    @property
    @expandmacros
    def prefix(self):
        """Return the directory prefix of files in this resource"""
        return os.path.normpath(self._prefix) + "/"

    @property
    @expandmacros
    def commitish(self):
        """Return the commitish to fetch for this resource"""
        return self._commitish

    @property
    def force_rebuild(self):
        """
        True if this source should always be re-fetched.
        Pinned sources which should be recreated from their repositories
        for each build.
        """
        return True


class Archive(File):
    """A tarball archive which will be unpacked into the SRPM"""

    def __init__(self, spec, name, url, defined_by, prefix):
        super(Archive, self).__init__(spec, name, url, defined_by)
        self._prefix = prefix

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

        return os.path.join("%_sourcedir", "{}.tar".format(self.name))

    def extract_source(self, name, destdir):
        """
        Extract source 'name' to destdir.   Raises KeyError if the
        requested source cannot be found.
        """
        # For an archive, extract_source extracts the file from the archive
        # and writes it to the destination.
        with Tarball(self.path) as tarball:
            target_path = os.path.normpath(os.path.join(self.prefix, name))
            tarball.extract(target_path, destdir)


class Patchqueue(Archive):
    """A patchqueue archive which will be unpacked into the SRPM"""

    def series(self):
        """Return the contents of the patchqueue's series file"""
        with planex.patchqueue.Patchqueue(self.path, self.prefix) as queue:
            return queue.series()


def load(specpath, link=None, check_package_name=True, defines=None):
    """
    Load the spec file at specpath and apply link if provided.
    """

    spec = Spec(specpath, check_package_name=check_package_name,
                defines=defines)
    if link:
        if link.schema_version == 1:
            if link.sources:
                spec.add_archive("patches", link.url, link.path, link.sources)
            if link.patches:
                spec.add_archive("patches", link.url, link.path, link.patches)
            if link.patchqueue:
                spec.add_patchqueue("patches", link.url, link.path,
                                    link.patchqueue)
        elif link.schema_version >= 2:
            # hack - this should parse the names store them with just indices
            for name, value in link.sources.items():
                if value["URL"].startswith("ssh://"):
                    spec.add_gitarchive(name.lower(), value["URL"],
                                        link.path, value.get("prefix"),
                                        value.get("commitish"))
                else:
                    spec.add_source(name.lower(), value["URL"], link.path)
            for name, value in link.patch_sources.items():
                spec.add_archive(name.lower(), value["URL"], link.path,
                                 value["patches"])
            for name, value in link.patchqueue_sources.items():
                spec.add_patchqueue(name.lower(), value["URL"], link.path,
                                    value["patchqueue"])

    return spec


class Spec(object):
    """Represents an RPM spec file"""

    def __init__(self, path, check_package_name=True, defines=None):

        self.macros = dict(defines) if defines else {}
        self._sources = {}
        self._patches = {}
        self._archives = {}
        self._patchqueues = {}

        # _topdir defaults to $HOME/rpmbuild
        # If present, it needs to be applied once at the beginning
        if '_topdir' in self.macros:
            rpm.addMacro('_topdir', self.macros['_topdir'])

        # '%dist' in the host (where we build the source package)
        # might not match '%dist' in the chroot (where we build
        # the binary package).   We must override it on the host,
        # otherwise the names of packages in the dependencies won't
        # match the files actually produced by mock.
        if 'dist' not in self.macros:
            self.macros['dist'] = ""

        with rpm_macros(self.macros):
            self.path = path
            with open(path) as spec:
                self.spectext = spec.readlines()
            self.spec = parse_spec_quietly(path)

            if check_package_name:
                file_basename = os.path.basename(path).split(".")[0]
                if file_basename != self.name():
                    raise SpecNameMismatch(
                        "spec file name '%s' does not match package name '%s'"
                        % (path, self.name()))

        for source in reversed(self.spec.sources):
            if source[2] == 1:
                self.add_source("source%d" % source[1], source[0], path)
            elif source[2] == 2:
                self.add_patch("patch%d" % source[1], source[0], path)

    def specpath(self):
        """Return the path to the spec file"""
        return self.path

    def expand_patchqueues(self):
        """
        Insert the names of all patchqueue patches into the spec file
        """
        patchqueues = [self._patchqueues[key] for key
                       in sorted(self._patchqueues.keys())]
        if not patchqueues:
            return self.spectext

        series = sum([pq.series() for pq in patchqueues], [])
        spec = planex.patchqueue.expand_patchqueue(self, series)
        return "".join(list(spec))

    def provides(self):
        """Return a list of package names provided by this spec"""
        provides = sum([pkg.header['provides'] + [pkg.header['name']]
                        for pkg in self.spec.packages], [])

        # RPM 4.6 adds architecture constraints to dependencies.  Drop them.
        provides = [re.sub(r'\(x86-64\)$', '', pkg) for pkg in provides]
        return set(provides)

    def name(self):
        """Return the package name"""
        return self.spec.sourceHeader['name']

    def version(self):
        """Return the package version"""
        return self.spec.sourceHeader['version']

    # RPM runtime dependencies.   These are not required to build this
    # package, but will need to be installed when building any other
    # package which BuildRequires this one.
    def requires(self):
        """Return the set of packages needed by this package at runtime
           (Requires)"""
        return set.union(*[set(p.header['REQUIRES'])
                           for p in self.spec.packages])

    # RPM build dependencies.   The 'requires' key for the *source* RPM is
    # actually the 'buildrequires' key from the spec
    def buildrequires(self):
        """Return the set of packages needed to build this spec
           (BuildRequires)"""
        return set(self.spec.sourceHeader['requires'])

    def source_package_path(self):
        """
        Return the path of the source package which building this spec
        will produce
        """
        # There doesn't seem to be a macro for the name of the source rpm
        # but we can construct one using the 'NVR' RPM tag which returns the
        # package's name-version-release string.  Naming is not critically
        # important as these source RPMs are only used internally - mock
        # will write a new source RPM along with the binary RPMS.
        srpmname = self.spec.sourceHeader['nvr'] + ".src.rpm"
        return rpm.expandMacro(os.path.join('%_srcrpmdir', srpmname))

    def add_source(self, name, url, defined_by):
        """Add a new source file"""
        self._sources[name] = File(self, name, url, defined_by)

    def add_patch(self, name, url, defined_by):
        """Add a new patch file"""
        self._patches[name] = File(self, name, url, defined_by)

    def add_archive(self, name, url, defined_by, prefix):
        """Add a new tarball archive"""
        self._archives[name] = Archive(self, name, url, defined_by, prefix)

    def add_gitarchive(self, name, url, defined_by, prefix, commitish):
        """Add a new Git archive"""
        self._sources[name] = GitArchive(self, name, url, defined_by, prefix,
                                         commitish)

    def add_patchqueue(self, name, url, defined_by, prefix):
        """Add a new patchqueue"""
        self._patchqueues[name] = Patchqueue(self, name, url, defined_by,
                                             prefix)

    def resources(self):
        """List all resources to be packed into the source package"""

        return ([self._sources[key] for key
                 in sorted(self._sources.keys())] +
                [self._patches[key] for key
                 in sorted(self._patches.keys())] +
                [self._archives[key] for key
                 in sorted(self._archives.keys())] +
                [self._patchqueues[key] for key
                 in sorted(self._patchqueues.keys())])

    def resource(self, target):
        """
        Find the URL from which source should be downloaded
        """
        target_basename = os.path.basename(target)
        for resource in self.resources():
            if os.path.basename(resource.path) == target_basename:
                return resource

        raise KeyError(target_basename)

    def extract_source(self, source, destdir):
        """
        Extract source 'name' to destdir.   Raises KeyError if the
        requested source cannot be found.
        """
        resources = [resource for resource in self.resources()
                     if resource.is_fetchable]
        for resource in resources:
            try:
                resource.extract_source(source, destdir)
                print("Extracted %s from %s" % (source, resource.name))
                return
            except KeyError:
                pass
        raise KeyError(source)

    def sources(self):
        """List all sources defined in the spec file"""

        # RPM only looks at the basename part of the Source URL - the
        # part after the rightmost /.   We must match this behaviour.
        #
        # Examples:
        #    http://www.example.com/foo/bar.tar.gz -> bar.tar.gz
        #    http://www.example.com/foo/bar.cgi#/baz.tbz -> baz.tbz

        with rpm_macros(self.macros, nevra(self.spec.sourceHeader)):
            ret = [(os.path.join(rpm.expandMacro("%_sourcedir"),
                                 os.path.basename(url)), url)
                   for (url, _, _) in reversed(self.spec.sources)]

        patchqueues = [self._patchqueues[key] for key
                       in sorted(self._patchqueues.keys())]
        patches = sum([pq.series() for pq in patchqueues], [])
        patches = [(p, "") for p in patches]
        ret += patches
        return ret

    def source(self, target):
        """
        Find the URL from which source should be downloaded
        """
        target_basename = os.path.basename(target)
        for path, url in self.sources():
            if os.path.basename(path) == target_basename:
                return path, url

        raise KeyError(target_basename)

    def binary_package_paths(self):
        """Return a list of binary packages built by this spec"""

        def rpm_name_from_header(hdr):
            """
            Return the name of the binary package file which
            will be built from hdr
            """
            with rpm_macros(self.macros, nevra(hdr)):
                rpmname = hdr.sprintf(rpm.expandMacro("%{_build_name_fmt}"))
                return rpm.expandMacro(os.path.join('%_rpmdir', rpmname))

        return [rpm_name_from_header(pkg.header) for pkg in self.spec.packages]

    def highest_patch(self):
        """Return the number the highest numbered patch or -1"""
        patches = [num for (_, num, sourcetype) in self.spec.sources
                   if sourcetype == 2]
        patches.append(-1)
        return max(patches)
