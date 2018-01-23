"""Classes for handling RPM spec files.   The classes defined here
   are mostly just wrappers around rpm.rpm, adding information which
   the rpm library does not currently provide."""
from __future__ import print_function

import contextlib
import os
import re
import urlparse
import sys
import tempfile

import rpm

# Could have a decorator / context manager to set and unset all the RPM macros
# around methods such as 'provides'


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


class Spec(object):
    """Represents an RPM spec file"""

    def __init__(self, path, check_package_name=True, defines=None):

        self.macros = dict(defines) if defines else {}

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

    def specpath(self):
        """Return the path to the spec file"""
        return self.path

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

    def source_urls(self):
        """Return the URLs from which the sources can be downloaded"""
        return [source for (source, _, _) in reversed(self.spec.sources)]

    def expand_macro(self, macro):
        """Return the value of macro, expanded in the package's context"""
        with rpm_macros(self.macros, nevra(self.spec.sourceHeader)):
            return rpm.expandMacro(macro)

    def source_paths(self):
        """Return the filesystem paths to source files"""

        # RPM only looks at the basename part of the Source URL - the
        # part after the rightmost /.   We must match this behaviour.
        #
        # Examples:
        #    http://www.example.com/foo/bar.tar.gz -> bar.tar.gz
        #    http://www.example.com/foo/bar.cgi#/baz.tbz -> baz.tbz

        with rpm_macros(self.macros, nevra(self.spec.sourceHeader)):
            return [os.path.join(rpm.expandMacro("%_sourcedir"),
                                 os.path.basename(url))
                    for url in self.source_urls()]

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

    def sources(self):
        """List all sources defined in the spec file"""
        return zip(self.source_paths(), self.source_urls())

    def remote_sources(self):
        """List all sources with remote URLs defined in the spec file"""
        return [(path, url) for (path, url) in self.all_sources()
                if url.netloc != '']

    def local_sources(self):
        """List all local sources defined in the spec file"""
        patch_urls = [urlparse.urlparse(url) for (url, _, sourcetype)
                      in self.spec.sources if sourcetype == 1]
        return [url.path for url in patch_urls if url.netloc == '']

    def local_patches(self):
        """List all local patches defined in the spec file"""
        patch_urls = [urlparse.urlparse(url) for (url, _, sourcetype)
                      in self.spec.sources if sourcetype == 2]
        return [url.path for url in patch_urls if url.netloc == '']
