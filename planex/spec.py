"""Classes for handling RPM spec files.   The classes defined here
   are mostly just wrappers around rpm.rpm, adding information which
   the rpm library does not currently provide."""
from __future__ import print_function

from collections import OrderedDict

import contextlib
import os
import re
import urlparse
import sys
import tempfile

import rpm

# Could have a decorator / context manager to set and unset all the RPM macros
# around methods such as 'provides'


# Directories where rpmbuild/mock expects to find inputs
# and writes outputs
def rpmdir():
    """Return the expanded value of the RPM %_rpmdir macro"""
    return rpm.expandMacro('%_rpmdir')


def srpmdir():
    """Return the expanded value of the RPM %_srcrpmdir macro"""
    return rpm.expandMacro('%_srcrpmdir')


def flatten(lst):
    """Flatten a list of lists"""
    return sum(lst, [])


@contextlib.contextmanager
def rpm_macros(macros):
    """Context manager to add and remove all macros in the dictionary"""
    if macros is None:
        macros = OrderedDict()

    for key, value in macros.items():
        rpm.addMacro(key, value)
    yield
    for key, _ in reversed(macros.items()):
        rpm.delMacro(key)


def append_macros(macros1, macros2):
    """Return an ordered dict, making sure that the macros of macros2 apppear
    after the macros in macros1, preserving their order."""
    new_dict = OrderedDict((k, v) for k, v in macros1.items())

    for key, value in macros2.items():
        # To append to an ordered dict we must first delete the duplicate key
        # if present
        if key in new_dict:
            del new_dict[key]
        new_dict[key] = value

    return new_dict


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

        self.macros = OrderedDict(defines) if defines else OrderedDict()

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

            self.rpmfilenamepat = rpm.expandMacro('%_build_name_fmt')
            self.srpmfilenamepat = rpm.expandMacro('%_build_name_fmt')

    def specpath(self):
        """Return the path to the spec file"""
        return self.path

    def provides(self):
        """Return a list of package names provided by this spec"""
        provides = flatten([pkg.header['provides'] + [pkg.header['name']]
                            for pkg in self.spec.packages])

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
        hdr = self.spec.sourceHeader
        hardcoded_macros = OrderedDict([
            ('name', hdr['name']),
        ])

        with rpm_macros(append_macros(self.macros, hardcoded_macros)):
            return rpm.expandMacro(macro)

    def source_paths(self):
        """Return the filesystem paths to source files"""

        # RPM only looks at the basename part of the Source URL - the
        # part after the rightmost /.   We must match this behaviour.
        #
        # Examples:
        #    http://www.example.com/foo/bar.tar.gz -> bar.tar.gz
        #    http://www.example.com/foo/bar.cgi#/baz.tbz -> baz.tbz

        hdr = self.spec.sourceHeader
        hardcoded_macros = OrderedDict([
            ('name', hdr['name']),
        ])

        # apply custom macros and then append the harcoded overrides
        with rpm_macros(append_macros(self.macros, hardcoded_macros)):
            paths = [os.path.join(rpm.expandMacro("%_sourcedir"),
                                  os.path.basename(url))
                     for url in self.source_urls()]

        return paths

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
        """Return the path of the source package which building this
           spec will produce"""
        hdr = self.spec.sourceHeader
        hardcoded_macros = OrderedDict([
            ('NAME', hdr['name']),
            ('VERSION', hdr['version']),
            ('RELEASE', hdr['release']),
            ('ARCH', 'src')
        ])

        with rpm_macros(append_macros(self.macros, hardcoded_macros)):
            # There doesn't seem to be a macro for the name of the source
            # rpm, but the name appears to be the same as the rpm name
            # format. Unfortunately expanding that macro gives us a leading
            # 'src' that we don't want, so we strip that off
            srpmname = os.path.basename(rpm.expandMacro(self.srpmfilenamepat))
            result = os.path.join(srpmdir(), srpmname)

        return result

    def binary_package_paths(self):
        """Return a list of binary packages built by this spec"""
        def rpm_name_from_header(hdr):
            """Return the name of the binary package file which
               will be built from hdr"""

            hardcoded_macros = OrderedDict([
                ('NAME', hdr['name']),
                ('VERSION', hdr['version']),
                ('RELEASE', hdr['release']),
                ('ARCH', hdr['arch'])
            ])

            with rpm_macros(append_macros(self.macros, hardcoded_macros)):
                rpmname = rpm.expandMacro(self.rpmfilenamepat)
                result = os.path.join(rpmdir(), rpmname)

            return result

        return [rpm_name_from_header(pkg.header) for pkg in self.spec.packages]

    def highest_patch(self):
        """Return the number the highest numbered patch or -1"""
        patches = [num for (_, num, sourcetype) in self.spec.sources
                   if sourcetype == 2]
        patches.append(-1)
        return max(patches)

    def all_sources(self):
        """List all sources defined in the spec file"""
        urls = [urlparse.urlparse(url) for url in self.source_urls()]
        return zip(self.source_paths(), urls)

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
