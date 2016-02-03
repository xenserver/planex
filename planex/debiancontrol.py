"""
Utility functions for generating Debian control files from RPM
spec files.
"""

import textwrap

from planex.tree import Tree
from planex import mappkgname


STANDARDS_VERSION = "3.9.3"


def control_from_spec(spec):
    """
    Create the contents of the debian/control file from spec.
    """
    res = Tree()
    source_deb_from_spec(spec, res)
    for pkg in spec.packages:
        binary_deb_from_spec(pkg, res)
    return res


def source_deb_from_spec(spec, tree):
    """
    Create the source package stanza of the debian/source file from spec.
    """
    res = ""
    res += "Source: %s\n" % \
        mappkgname.map_package(spec.sourceHeader['name'])[0]
    res += "Priority: %s\n" % "optional"
    res += "Maintainer: %s\n" % "Euan Harris <euan.harris@citrix.com>"
    res += "Section: %s\n" % mappkgname.map_section(spec.sourceHeader['group'])
    res += "Standards-Version: %s\n" % STANDARDS_VERSION

    res += "Build-Depends:\n"
    build_depends = ["debhelper (>= 8)", "dh-ocaml (>= 0.9)", "ocaml-nox",
                     "python"]
    for pkg, version in zip(spec.sourceHeader['requires'],
                            spec.sourceHeader['requireVersion']):
        deps = mappkgname.map_package(pkg)
        for dep in deps:
            if version:
                dep += " (>= %s)" % version
            build_depends.append(dep)

    res += ",\n".join(set([" %s" % d for d in build_depends]))
    res += "\n\n"

    tree.append('debian/control', res)


def binary_deb_from_spec(spec, tree):
    """
    Create the binary package stanza of the debian/source file from spec.
    """
    res = ""
    res += "Package: %s\n" % mappkgname.map_package_name(spec.header)
    if spec.header['arch'] in ["x86_64", "i686", "armhf", "armv7l"]:
        res += "Architecture: any\n"
    else:
        res += "Architecture: all\n"

    res += "Depends:\n"
    depends = ["${ocaml:Depends}", "${shlibs:Depends}", "${misc:Depends}"]
    for pkg, version in zip(spec.header['requires'],
                            spec.header['requireVersion']):
        deps = mappkgname.map_package(pkg)
        for dep in deps:
            if version:
                dep += " (>= %s)" % version
            depends.append(dep)
    res += ",\n".join([" %s" % d for d in depends])
    res += "\n"

    # XXX These lines should only be added for ocaml packages
    res += "Provides: ${ocaml:Provides}\n"
    res += "Recommends: ocaml-findlib\n"

    res += "Description: %s\n" % spec.header['summary']
    res += format_description(spec.header['description'])
    res += "\n\n"

    tree.append('debian/control', res)


def format_description(description):
    """
    Format the package description to suit Debian constraints:
    correct line length; initial one space indent; blank lines
    must be replaced by dots
    """

    paragraphs = "".join(description).split("\n\n")
    wrapped = ["\n".join(textwrap.wrap(p, initial_indent=" ",
                                       subsequent_indent=" "))
               for p in paragraphs]
    return "\n .\n".join(wrapped)
