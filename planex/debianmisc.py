"""
Library of utility functions for generating Debian packages from RPM
spec files.
"""

import rpm
from planex.tree import Tree
from planex import mappkgname
import os
import re
from planex import rpmextra


def conffiles_from_spec(spec, specpath):
    """
    Create contents of the debian/conffiles file.
    """
    # Configuration files, not to be overwritten on upgrade.
    # Files in /etc are automatically marked as config files,
    # so we only need to list files here if they are in a
    # different place.
    res = Tree()
    pkgname = mappkgname.map_package_name(spec.sourceHeader)
    files = rpmextra.files_from_spec(pkgname, specpath)
    if pkgname + "-%config" in files:
        for filename in files[pkgname + "-%config"]:
            res.append('debian/conffiles', "%s\n" % filename)
    return res


def filelists_from_spec(spec, specpath):
    """
    Create package contents file from spec.
    """
    res = Tree()
    for pkg in spec.packages:
        name = "%s.install.in" % mappkgname.map_package_name(pkg.header)
        res.append("debian/%s" % name,
                   files_from_pkg(spec.sourceHeader['name'], pkg, specpath))
    return res


def files_from_pkg(basename, pkg, specpath):
    """
    Return list of files which will be included in the package,
    with Debian-compatible pathnames.
    """
    # should be able to build this from the files sections - can't find how
    # to get at them from the spec object
    res = ""
    files = rpmextra.files_from_spec(basename, specpath)
    for filename in files.get(pkg.header['name'], []):
        # Debian packages must not contain compiled Python files.
        # Instead, the python2 helper arranges to compile these
        # files when they are installed.
        if os.path.splitext(filename)[1] in [".pyc", ".pyo"]:
            continue

        rpm.addMacro("_libdir", "usr/lib")
        rpm.addMacro("_bindir", "usr/bin")

        # deb just wants relative paths
        src = rpm.expandMacro(filename).lstrip("/")
        rpm.delMacro("_bindir")
        rpm.delMacro("_libdir")
        rpm.addMacro("_libdir", "/usr/lib")
        rpm.addMacro("_bindir", "/usr/bin")
        dst = rpm.expandMacro(filename)

        # destination paths should be directories, not files.
        # if the file is foo and the path is /usr/bin/foo, the
        # package will end up install /usr/bin/foo/foo
        if not dst.endswith("/"):
            dst = os.path.dirname(dst)
        rpm.delMacro("_bindir")
        rpm.delMacro("_libdir")
        res += "%s %s\n" % (src, dst)
    return res


# Patches can be added to debian/patches, with a series file
# We use dpkg-source -b --auto-commit <dir>

def patches_from_spec(spec, src_dir):
    """
    Create the contents of the debian/patches directory,
    which holds local patches to be applied to the pristine
    sources.
    """
    res = Tree()
    patches = [(seq, name) for (name, seq, typ) in spec.sources
               if typ == 2]
    patches = [name for (seq, name) in sorted(patches)]
    for patch in patches:
        with open(os.path.join(src_dir, patch)) as patchfile:
            contents = patchfile.read()
            permissions = os.fstat(patchfile.fileno()).st_mode
        res.append(os.path.join("debian/patches", patch),
                   contents, permissions)
        res.append("debian/patches/series", "%s\n" % patch)
    return res


def compat_from_spec(_):
    """
    Create the contents of the debian/compat file.
    """
    res = Tree()
    res.append("debian/compat", "8")
    return res


def format_from_spec(_, isnative):
    """
    Create the contents of the debian/format file.
    """
    res = Tree()
    fmt = "native" if isnative else "quilt"
    res.append("debian/source/format", "3.0 (%s)\n" % fmt)
    return res


def copyright_from_spec(_):
    """
    Create the contents of the debian/copyright file.
    Currently not filled correctly.
    """
    res = Tree()
    res.append("debian/copyright", "FIXME")
    return res


def principal_source_file(spec):
    """
    Return our best guess at the main source file defined
    in spec.   This will be used as the pristine tarball
    in the generated Debian package;  all other sources will
    be packed as patches.
    """
    return os.path.basename([name for (name, seq, filetype)
                             in spec.sources
                             if seq == 0 and filetype == 1][0])


def is_native(_spec):
    """
    Guess whether the package should be a 'native' Debian package,
    based on the type of the principal source file.
    """
    # See https://wiki.debian.org/DebianMentorsFaq for more
    # information on native and non-native packages.
    tarball = principal_source_file(_spec)
    match = re.match(r"^(.+)((\.tar\.(gz|bz2|lzma|xz)|\.tbz)$)", tarball)
    return match is None
