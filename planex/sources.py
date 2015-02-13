import os
import os.path
import re
import urlparse
from planex import exceptions
from planex.globals import SOURCES_DIR
from planex.util import run


class SCM(object):
    repos = "repos"

    def __init__(self, url, config):
        for protocol in ['git', 'hg']:
            if protocol not in urlparse.uses_fragment:
                urlparse.uses_fragment.append(protocol)

        (scheme, host, path, _, _, fragment) = urlparse.urlparse(url)
        repo_url = "%s://%s%s" % (scheme, host, path)  # Strip off fragment
        self.repo_name = path.split('/')[-1]

        def absolutize(path):
            if os.path.isabs(path):
                return path
            else:
                return os.path.join(os.getcwd(), path)

        if "repos_mirror_path" in config:
            self.repos_mirror_path = absolutize(config.repos_mirror_path)
        else:
            self.repos_mirror_path = "/nonexistant"

        self.repos_path = absolutize(config.repos_path)

        def strip_ext(ext):
            if self.repo_name.endswith(ext):
                self.repo_name = self.repo_name[:-len(ext)]

        strip_ext(".git")
        strip_ext(".hg")

        self.orig_url = url
        self.ty = scheme
        self.repo_url = repo_url
        self.fragment = fragment

        matches = re.search("([0-9a-f]*)\/([^\/]*)", fragment)
        if matches:
            self.scmhash = matches.group(1)
            self.version = matches.group(2)[len(self.repo_name) + 1:-7]
        else:
            self.scmhash = None
            self.version = None

    def set_hash_and_vsn(self, scmhash, version):
        self.scmhash = scmhash
        self.version = version

    @property
    def localpath(self):
        return os.path.join(self.repos_path, self.repo_name)

    @property
    def tarballprefix(self):
        assert(self.version is not None)
        return "%s-%s" % (self.repo_name, self.version)

    @property
    def archivename(self):
        assert(self.version is not None)
        return "%s.tar.gz" % (self.tarballprefix)

    @property
    def extendedurl(self):
        return "%s#%s/%s" % (self.repo_url, self.scmhash, self.archivename)

    def archive(self, sources_dir=SOURCES_DIR):
        for cmd in self.archive_commands(sources_dir):
            run(cmd)


class GitSource(SCM):
    def __init__(self, url, config):
        super(GitSource, self).__init__(url, config)
        if self.fragment:
            self.git_committish = self.fragment.split('/')[0]
        else:
            self.git_committish = "master"

        if not self.version:
            if os.path.exists(self.localpath):
                # Don't pin if the repo doesn't currently exist
                self.pin()

    @staticmethod
    def handles(ty):
        return ty == "git"

    def clone_commands(self):

        dst = self.localpath
        dst_dotgit = os.path.join(dst, ".git")

        # For a repo e.g. git://github.com/foo/bar.git
        # Check for a mirror of the form mirrorpath/github.com/foo/bar.git
        (_, host, urlpath, _, _, _) = urlparse.urlparse(self.repo_url)

        mirrorpath = os.path.join(self.repos_mirror_path, host,
                                  urlpath.strip("/"))

        if os.path.exists(mirrorpath):
            clone_cmd = [
                'git',
                'clone',
                mirrorpath,
                dst
            ]
            reset_urls_cmd = [
                'git',
                '--git-dir=%s' % dst_dotgit,
                'remote',
                'set-url',
                'origin',
                self.repo_url
            ]
            fetch_cmd = [
                'git',
                '--git-dir=%s' % dst_dotgit,
                'remote',
                'fetch',
                '--all',
                '-t'
            ]
            checkout_cmd = [
                'git',
                '--git-dir=%s' % dst_dotgit,
                '--work-tree=%s' % dst,
                'checkout',
                self.git_committish
            ]
            return [clone_cmd, reset_urls_cmd, fetch_cmd, checkout_cmd]
        else:
            clone_cmd = [
                'git',
                'clone',
                self.repo_url,
                dst
            ]
            checkout_cmd = [
                'git',
                '--git-dir=%s' % dst_dotgit,
                '--work-tree=%s' % dst,
                'checkout',
                self.git_committish
            ]
            return [clone_cmd, checkout_cmd]

    def pin(self):
        dotgitdir = os.path.join(self.localpath, ".git")

        if not os.path.exists(dotgitdir):
            raise exceptions.NoRepository

        # First, get the hash of the commit
        cmd = ["git", "--git-dir=%s" % dotgitdir,
               "rev-parse", "HEAD"]

        scmhash = run(cmd)['stdout'].strip()

        # Verified good hash.
        self.scmhash = scmhash

        # Now lets describe that hash.
        cmd = ["git", "--git-dir=%s" % dotgitdir,
               "describe", "--tags", scmhash]

        description = run(cmd, check=False)['stdout'].strip()

        # if there are no tags, get the number of commits, which should
        # always increase
        if description == "":
            cmd = ["git", "--git-dir=%s" % dotgitdir,
                   "log", scmhash, "--oneline"]
            commits = run(cmd)['stdout'].strip()
            description = str(len(commits.splitlines()))

        match = re.search("[^0-9]*", description)
        matchlen = len(match.group())
        self.version = description[matchlen:].replace('-', '+')

    def archive_commands(self, sources_dir=SOURCES_DIR):
        # If it already exists, we're done.
        dotgitdir = os.path.join(self.localpath, ".git")

        # archive name always ends in .gz - strip it off
        tarball_name = self.archivename[:-3]

        return [["git", "--git-dir=%s" % dotgitdir, "archive",
                 "--prefix=%s/" % self.tarballprefix, self.scmhash, "-o",
                 "%s/%s" % (sources_dir, tarball_name)],
                ["gzip", "--no-name", "-f", "%s/%s" %
                 (sources_dir, tarball_name)]]


class HgSource(SCM):
    def __init__(self, url, config):
        super(HgSource, self).__init__(url, config)
        if os.path.exists(self.localpath):
            # Don't pin if the repo doesn't currently exist
            self.pin()

    @staticmethod
    def handles(ty):
        return ty == "hg"

    @property
    def localpath(self):
        # Mercurial repos clone with the extension .hg
        return os.path.join(self.repos_path, "%s.hg" % self.repo_name)

    def clone_commands(self):
        dst = self.localpath

        if self.fragment:
            clone_url = self.repo_url + "#" + self.fragment
        else:
            clone_url = self.repo_url

        clone_url = re.sub('hg://', "http://", clone_url)

        return [[
            'hg',
            'clone',
            clone_url,
            dst
        ]]

    def pin(self):

        cmd = ["hg", "-R", self.localpath, "tip", "--template", "{node}"]
        scmhash = run(cmd)['stdout'].strip()
        self.scmhash = scmhash

        cmd = ["hg", "-R", self.localpath, "parents", "--template", "{rev}"]
        description = run(cmd)['stdout'].strip()

        self.version = str(description)

    def archive_commands(self, sources_dir=SOURCES_DIR):
        # If it already exists, we're done.
        if os.path.exists(os.path.join(sources_dir, self.archivename)):
            print "File's already here!"
            return []

        print "File's not here!"
        return [["hg", "-R", self.localpath, "archive", "-t", "tgz", "-p",
                 "%s/" % self.tarballprefix,
                 "%s/%s" % (sources_dir, self.archivename)]]


class FileSource(SCM):
    def __init__(self, url, config):
        super(FileSource, self).__init__(url, config)

    @property
    def archivename(self):
        return self.orig_url.split("/")[-1]

    @staticmethod
    def handles(ty):
        return ty in ["file", "http", "https", "ftp"]

    def clone_commands(self):
        return []

    def archive_commands(self, sources_dir=SOURCES_DIR):
        final_path = os.path.join(sources_dir, self.archivename)
        if os.path.exists(final_path):
            return []
        return [["curl", "-k", "-L", "-o", final_path, self.orig_url]]


class OtherSource(SCM):
    @staticmethod
    def handles(ty):
        return False

    def clone_commands(self):
        return []

    def archive(self, sources_dir=SOURCES_DIR):
        return


def Source(url, repomirror):
    ty = url.split(":")[0]
    for cls in SCM.__subclasses__():  # pylint: disable=E1101
        if cls.handles(ty):
            return cls(url, repomirror)
    return OtherSource(url, repomirror)
