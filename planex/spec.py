"""Classes for handling RPM spec files.   The classes defined here
   are mostly just wrappers around rpm.rpm, adding information which
   the rpm library does not currently provide."""


import os
import re
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


def specdir():
    """Return the expanded value of the RPM %_specrpmdir macro"""
    return rpm.expandMacro('%_specdir')


def sourcedir():
    """Return the expanded value of the RPM %_sourcedir macro"""
    return rpm.expandMacro('%_sourcedir')


def flatten(lst):
    """Flatten a list of lists"""
    return sum(lst, [])


def identity(name):
    """Identity mapping"""
    return name


def identity_list(name):
    """Identity mapping, injected into a list"""
    return [name]


class SpecNameMismatch(Exception):
    """Exception raised when a spec file's name does not match the name
       of the package defined within it"""
    pass


class Spec(object):
    """Represents an RPM spec file"""

    def __init__(self, path, target="rpm", map_name=None, dist="",
                 check_package_name=True, topdir=None):
        if map_name:
            self.map_package_name = map_name
        else:
            self.map_package_name = identity_list

        # _topdir defaults to $HOME/rpmbuild
        if topdir:
            rpm.addMacro('_topdir', topdir)

        rpm.addMacro('_specdir', os.path.dirname(path))

        self.path = os.path.join(specdir(), os.path.basename(path))
        with open(path) as spec:
            self.spectext = spec.readlines()

        # '%dist' in the host (where we build the source package)
        # might not match '%dist' in the chroot (where we build
        # the binary package).   We must override it on the host,
        # otherwise the names of packages in the dependencies won't
        # match the files actually produced by mock.
        self.dist = ""
        if target == "rpm":
            self.dist = dist

        rpm.addMacro('dist', self.dist)
        try:
            self.spec = rpm.ts().parseSpec(path)
        except ValueError as exn:
            exn.args = (exn.args[0].rstrip() + ' ' + path, )
            raise

        if check_package_name:
            file_basename = os.path.basename(path).split(".")[0]
            if file_basename != self.name():
                raise SpecNameMismatch(
                    "spec file name '%s' does not match package name '%s'" %
                    (path, self.name()))

        self.rpmfilenamepat = rpm.expandMacro('%_build_name_fmt')
        self.srpmfilenamepat = rpm.expandMacro('%_build_name_fmt')
        self.map_arch = identity

    def specpath(self):
        """Return the path to the spec file"""
        return self.path

    def provides(self):
        """Return a list of package names provided by this spec"""
        provides = flatten([pkg.header['provides'] + [pkg.header['name']]
                            for pkg in self.spec.packages])

        # RPM 4.6 adds architecture constraints to dependencies.  Drop them.
        provides = [re.sub(r'\(x86-64\)$', '', pkg) for pkg in provides]
        return set(flatten([self.map_package_name(p) for p in provides]))

    def name(self):
        """Return the package name"""
        return self.spec.sourceHeader['name']

    def version(self):
        """Return the package version"""
        return self.spec.sourceHeader['version']

    def source_urls(self):
        """Return the URLs from which the sources can be downloaded"""
        return [source for (source, _, _) in reversed(self.spec.sources)]

    def source_paths(self):
        """Return the filesystem paths to source files"""

        # RPM only looks at the basename part of the Source URL - the
        # part after the rightmost /.   We must match this behaviour.
        #
        # Examples:
        #    http://www.example.com/foo/bar.tar.gz -> bar.tar.gz
        #    http://www.example.com/foo/bar.cgi#/baz.tbz -> baz.tbz

        return [os.path.join(sourcedir(), os.path.basename(url))
                for url in self.source_urls()]

    # RPM build dependencies.   The 'requires' key for the *source* RPM is
    # actually the 'buildrequires' key from the spec
    def buildrequires(self):
        """Return the set of packages needed to build this spec
           (BuildRequires)"""
        return set(flatten([self.map_package_name(r) for r
                            in self.spec.sourceHeader['requires']]))

    def source_package_path(self):
        """Return the path of the source package which building this
           spec will produce"""
        hdr = self.spec.sourceHeader
        rpm.addMacro('NAME', self.map_package_name(hdr['name'])[0])
        rpm.addMacro('VERSION', hdr['version'])
        rpm.addMacro('RELEASE', hdr['release'])
        rpm.addMacro('ARCH', 'src')

        # There doesn't seem to be a macro for the name of the source
        # rpm, but the name appears to be the same as the rpm name format.
        # Unfortunately expanding that macro gives us a leading 'src' that we
        # don't want, so we strip that off

        srpmname = os.path.basename(rpm.expandMacro(self.srpmfilenamepat))

        rpm.delMacro('NAME')
        rpm.delMacro('VERSION')
        rpm.delMacro('RELEASE')
        rpm.delMacro('ARCH')

        return os.path.join(srpmdir(), srpmname)

    def binary_package_paths(self):
        """Return a list of binary packages built by this spec"""
        def rpm_name_from_header(hdr):
            """Return the name of the binary package file which
               will be built from hdr"""
            rpm.addMacro('NAME', self.map_package_name(hdr['name'])[0])
            rpm.addMacro('VERSION', hdr['version'])
            rpm.addMacro('RELEASE', hdr['release'])
            rpm.addMacro('ARCH', self.map_arch(hdr['arch']))
            rpmname = rpm.expandMacro(self.rpmfilenamepat)
            rpm.delMacro('NAME')
            rpm.delMacro('VERSION')
            rpm.delMacro('RELEASE')
            rpm.delMacro('ARCH')
            return os.path.join(rpmdir(), rpmname)
        return [rpm_name_from_header(pkg.header) for pkg in self.spec.packages]
