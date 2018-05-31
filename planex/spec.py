"""Classes for handling RPM spec files.   The classes defined here
   are mostly just wrappers around rpm.rpm, adding information which
   the rpm library does not currently provide."""
from __future__ import print_function

import os
import re
import sys
import tempfile

from itertools import chain


from planex.blobs import Blob, GitBlob, Archive, GitArchive, \
    Patchqueue, GitPatchqueue
from planex.macros import nevra, rpm, rpm_macros

import planex.patchqueue


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


def _parse_name(name):
    """
    Parse [name] a string composed by a word and an optional number into the
    name and the number as an integer (0 if not present). E. g.

    - Source -> 0
    - Patch001 -> 1
    - Test12 -> 12

    Raises KeyError if [name] cannot be parsed
    """
    matcher = re.compile(r"^[a-zA-Z]+(\d*)$")
    match = matcher.match(name)

    if match is None:
        raise KeyError(name)

    (idx, ) = match.groups()
    if idx == '':
        return 0
    return int(idx)


class InvalidSchemaVersion(KeyError):
    """Error raised if the schemaVersion field in the pins is not supported"""
    pass


def update_with_schema_version_2(spec, link):
    """Update spec with a schemaVersion 2 link"""
    for name, value in link.patch_sources.items():
        idx = _parse_name(name)
        spec.add_archive(name,
                         Archive(spec, value["URL"], link.path,
                                 value["patches"]))

    for name, value in link.patchqueue_sources.items():
        idx = _parse_name(name)
        spec.add_patchqueue(idx,
                            Patchqueue(spec, value["URL"], link.path,
                                       value["patchqueue"]))


def update_with_schema_version_3(spec, link):
    """Update spec with a schemaVersion 3 link"""
    if link.ignore_autosetup:
        spec.disable_autosetup()

    for name, value in link.sources.items():
        idx = _parse_name(name)
        url = value["URL"]
        if url.startswith("ssh://"):
            source = GitBlob(spec, url, link.path,
                             value.get("prefix"), value.get("commitish"))
        else:
            source = Blob(spec, url, link.path)
        spec.add_source(idx, source)

    for name, value in link.archives.items():
        idx = _parse_name(name)
        url = value["URL"]
        if url.startswith("ssh://"):
            archive = GitArchive(spec, url, link.path,
                                 value.get("prefix"), value.get("commitish"))
        else:
            archive = Archive(spec, url, link.path, value.get("prefix"))
        spec.add_archive(idx, archive)

    for name, value in link.patchqueue_sources.items():
        idx = _parse_name(name)
        url = value["URL"]
        if url.startswith("ssh://"):
            patchqueue = GitPatchqueue(spec, url, link.path,
                                       value.get("prefix"),
                                       value.get("commitish"))
        else:
            patchqueue = Patchqueue(spec, url, link.path, value.get("prefix"))
        spec.add_patchqueue(idx, patchqueue)


def load(specpath, link=None, check_package_name=True, defines=None):
    """
    Load the spec file at specpath and apply link if provided.
    """

    spec = Spec(specpath, check_package_name=check_package_name,
                defines=defines)

    if link is None:
        return spec

    if link.schema_version == 2:
        update_with_schema_version_2(spec, link)
    elif link.schema_version == 3:
        update_with_schema_version_3(spec, link)
    else:
        raise InvalidSchemaVersion(link.schema_version)

    return spec


# pylint: disable=too-many-instance-attributes
class Spec(object):
    """Represents an RPM spec file"""

    def __init__(self, path, check_package_name=True, defines=None):

        self.macros = dict(defines) if defines else {}
        self._sources = {}
        self._patches = {}
        self._archives = {}
        self._patchqueues = {}
        self._ignore_autosetup = False

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
                spec_name = self.name()
                if isinstance(spec_name, bytes):
                    spec_name = spec_name.decode()
                if file_basename != spec_name:
                    raise SpecNameMismatch(
                        "spec file name '%s' does not match package name '%s'"
                        % (path, self.name()))

        for filepath, index, sourcetype in reversed(self.spec.sources):
            blob = Blob(self, filepath, path)
            if sourcetype == 1:
                self.add_source(index, blob)
            elif sourcetype == 2:
                self.add_patch(index, blob)

    def specpath(self):
        """Return the path to the spec file"""
        return self.path

    # pylint: disable=too-many-locals
    def rewrite_spec(self, srpm_sources=None, manifests=None):
        """
        Rewrite the sources and patches in the spec file, also inserting the
        names of all patchqueue patches into it.

        If [srpm_sources] is a list of sources, it will add comments in the
        spec file describing the origin of the source.
        If [manifests] is true it will add `Provides: gitsha(url) = sha` using
        the Git* objects or the .gitarchive-info files.
        """

        # If there is nothing to rewrite, don't rewrite!
        if not (self._sources or self._patches or self._patchqueues):
            return self.spectext

        # If there are patches, make sure we use autosetup or autopatch
        if not self._ignore_autosetup and (
                self._patchqueues or self._patches):
            planex.patchqueue.check_spec_supports_patchqueues(self)

        def is_source_or_patch_line(line):
            """True if the line does start with Source or Patch"""
            source = re.compile("^source", re.IGNORECASE)
            patch = re.compile("^patch", re.IGNORECASE)
            return bool(patch.match(line) or source.match(line))

        def first_index(iterable, predicate):
            """
            Returns the index of first value in the iterable
            for which predicate(value) is true.
            """
            return next(i for i, v in enumerate(iterable) if predicate(v))

        split_at = first_index(self.spectext, is_source_or_patch_line)

        newspec_header = self.spectext[:split_at]
        newspec_filtered_body = (
            line for line
            in self.spectext[split_at+1:]
            if not is_source_or_patch_line(line)
        )

        # we are sorting patches and sources to avoid tripping on weird
        # centos bug like https://bugzilla.redhat.com/show_bug.cgi?id=1359084
        def sorted_by_key(dictionary):
            """Return an iterable of key, value tuples ordered by key"""
            return sorted(dictionary, key=lambda kv: kv[0])

        if srpm_sources is not None:
            file_sources = self._contents_from_resources(srpm_sources)
        else:
            file_sources = []

        def source_content(kind, index, blob):
            """Content of [kind]X line with or without metadata."""
            path = os.path.basename(blob.path) \
                if isinstance(blob, GitBlob) else blob.url
            source_line = "{}{}: {}\n".format(kind, index, path)

            # find an eventual archive that provides the data
            resource = [
                resource for (resource, collection) in file_sources
                if blob.basename in collection
            ]
            if not resource:
                return source_line

            resource = resource.pop()
            if isinstance(resource, (GitBlob, GitArchive)):
                meta = "# {}{}: {}#{}".format(
                    kind, index, resource.url, resource.commitish)
            else:
                meta = "# {}{}: {}".format(kind, index, resource.url)
            return "{}\n{}".format(meta, source_line)

        sources = (
            source_content("Source", index, blob)
            for index, blob in sorted_by_key(self._sources.items())
        )
        patches = (
            source_content("Patch", index, blob)
            for index, blob in sorted_by_key(self._patches.items())
        )

        patchqueues = [self._patchqueues[key] for key
                       in sorted(self._patchqueues.keys())]
        series = sum([pq.series() for pq in patchqueues], [])
        base_index = 1 + self.highest_patch()
        further_patches = (
            "Patch{}: {}\n".format(base_index + index, patch)
            for index, patch in enumerate(series)
        )
        further_patches_metadata = (
            "# Patchqueue: {}#{}\n".format(pq.url, pq.commitish)
            if isinstance(pq, GitPatchqueue)
            else "# Patchqueue: {}\n".format(pq.url)
            for pq in patchqueues if srpm_sources is not None
        )

        if manifests is None:
            manifests = {}

        manifest_metadata = [
            "Provides: gitsha({}) = {}\n".format(url, sha)
            for url, sha in manifests.items()
        ]

        def append_manifest(acc, newline):
            "Appends the manifest after each binary subpackage declaration"
            acc.append(newline)
            # Leave the space as this should append only to subpackages
            if newline.startswith("%package "):
                acc.extend(manifest_metadata)
            return acc

        newspec = chain(
            newspec_header, ("\n",),
            sources, patches, ("\n",),
            further_patches_metadata, further_patches, ("\n",),
            manifest_metadata, ("\n",),
            reduce(append_manifest, newspec_filtered_body, [])
        )
        return "".join(newspec)

    def disable_autosetup(self):
        """
        Disable the autosetup/autopatch check otherwise performed when
        patches or patchqueues are present
        """
        self._ignore_autosetup = True

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

    def add_source(self, index, source):
        """Add a new source file"""
        assert isinstance(source, Blob)
        self._sources[index] = source

    def add_patch(self, index, patch):
        """Add a new patch file"""
        assert isinstance(patch, Blob)
        self._patches[index] = patch

    def add_archive(self, index, archive):
        """Add a new tarball archive"""
        assert isinstance(archive, Archive)
        self._archives[index] = archive

    def add_patchqueue(self, index, patchqueue):
        """Add a new patchqueue"""
        assert isinstance(patchqueue, Patchqueue)
        self._patchqueues[index] = patchqueue

    def resources_dict(self):
        """Return all resources from the spec in a dict"""
        iterator = [
            (self._sources, "Source"),
            (self._patches, "Patch"),
            (self._archives, "Archive"),
            (self._patchqueues, "PatchQueue")
        ]
        resources = {}
        for resource, string in iterator:
            for key, value in resource.items():
                resources["{}{}".format(string, key)] = value
        return resources

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
        Find the URL from which source should be downloaded.
        """
        target_basename = os.path.basename(target)
        for resource in self.resources():
            if os.path.basename(resource.path) == target_basename:
                return resource

        raise KeyError(target_basename)

    def _contents_from_resources(self, sources):
        """
        Return a zip of (resource, collection) where resource is a source,
        archive or patchqueue, and collection is the list of sources that
        we will copy or extract from it.
        """
        resources = [resource for resource in self.resources()
                     if resource.is_fetchable]

        collection_batches = [
            [source for source in sources if source in resource]
            for resource in resources
        ]

        filtered_batches = [
            [
                source for source in sources
                # make sure that nothing later on is fetching the same source
                if not any(source in collection
                           for collection in collection_batches[idx+1:])
            ]
            for (idx, sources) in enumerate(collection_batches)
        ]

        return zip(resources, filtered_batches)

    def extract_sources(self, sources, destdir):
        """
        Extract source 'name' to destdir.   Returns a list of skipped
        archives.   Raises KeyError if the requested source cannot be found.
        """
        # below we rely in an essential way on the fact that
        # resources are sorted

        pending = set(sources)
        skipped = []
        for (resource, collection) in self._contents_from_resources(sources):
            if not collection:
                skipped.append(resource.basename)
                continue
            resource.extract_sources(collection, destdir)
            pending -= set(collection)

        if pending != set():
            raise KeyError(pending)

        return skipped

    def sources(self):
        """List all sources defined in the spec file"""

        # RPM only looks at the basename part of the Source URL - the
        # part after the rightmost /.   We must match this behaviour.
        #
        # Examples:
        #    http://www.example.com/foo/bar.tar.gz -> bar.tar.gz
        #    http://www.example.com/foo/bar.cgi#/baz.tbz -> baz.tbz

        ret = [(source.path, source.url)
               for _, source in sorted(self._sources.items())]
        ret += [(patch.path, patch.url)
                for _, patch in sorted(self._patches.items())]
        patchqueues = [self._patchqueues[key] for key
                       in sorted(self._patchqueues.keys())]
        patches = sum([pq.series() for pq in patchqueues], [])
        patches = [(p, "") for p in patches]
        ret += patches
        return ret

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
        patches_indices = self._patches.keys()
        fallback = (-1,)
        return max(chain(patches_indices, fallback))
