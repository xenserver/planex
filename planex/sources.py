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
        urlparts = url.split('#')
        repo_url = "%s://%s%s" % (scheme, host, path) # Strip of fragment
        self.repo_name = path.split('/')[-1]

        def absolutize(path):
            if os.path.isabs(path):
                return path
            else:
                return os.path.join(os.getcwd(),path)

        self.repos_mirror_path = absolutize(config.repos_mirror_path)
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
        assert(self.version != None)
        return "%s-%s" % (self.repo_name, self.version)

    @property
    def archivename(self):
        assert(self.version != None)
        return "%s.tar.gz" % (self.tarballprefix)

    @property
    def extendedurl(self):
        return "%s#%s/%s" % (self.repo_url, self.scmhash, self.archivename)
        

class GitSource(SCM):
    def __init__(self, url, config):
        super(GitSource, self).__init__(url, config)
        if self.fragment:
            self.git_committish = self.fragment.split('/')[0]
        else:
            self.git_committish = "master"

        if os.path.exists(self.localpath):
            # Don't pin if the repo doesn't currently exist
            self.pin()

    @staticmethod
    def handles(ty):
        return ty=="git"

    def clone_commands(self):
        
        dst = self.localpath
        dst_dotgit = os.path.join(dst, ".git")

        # For a repo e.g. git://github.com/foo/bar.git
        # Check for a mirror of the form mirrorpath/github.com/foo/bar.git
        (_, host, urlpath, _, _, _) = urlparse.urlparse(self.repo_url)
        
        mirrorpath = os.path.join(self.repos_mirror_path, host, urlpath.strip("/"))

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

        # First, get the hash of the commit
        cmd = ["git", "--git-dir=%s" % dotgitdir,
               "rev-parse", "HEAD"]

        scmhash = run(cmd)['stdout'].strip()

        # Verified good hash.
        self.scmhash = scmhash

        # Now lets describe that hash.
        cmd = ["git", "--git-dir=%s" % dotgitdir,
               "describe", "--tags", scmhash]

        description = run(cmd,check=False)['stdout'].strip()

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

    def archive(self, sources_dir=SOURCES_DIR):    
        # If it already exists, we're done.
        dotgitdir = os.path.join(self.localpath, ".git")

        if os.path.exists(os.path.join(sources_dir, self.archivename)):
            return
        
        # archive name always ends in .gz - strip it off
        tarball_name = self.archivename[:-3]

        cmd = ["git", "--git-dir=%s" % dotgitdir, "archive",
               "--prefix=%s/" % self.tarballprefix, self.scmhash, "-o",
               "%s/%s" % (sources_dir, tarball_name)]
        run(cmd)

        cmd = ["gzip", "--no-name", "-f", "%s/%s" % (sources_dir, tarball_name)]
        run(cmd)

class HgSource(SCM):
    def __init__(self, url, config):
        super(HgSource, self).__init__(url, config)
        if os.path.exists(self.localpath):
            # Don't pin if the repo doesn't currently exist
            self.pin()

    @staticmethod
    def handles(ty):
        return ty=="hg"

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

    def archive(self, sources_dir=SOURCES_DIR):    
        # If it already exists, we're done.
        if os.path.exists(os.path.join(sources_dir, self.archivename)):
            print "File's already here!"
            return
        
        print "File's not here!"
        cmd = ["hg", "-R", self.localpath, "archive", "-t", "tgz", "-p", 
               "%s/" % self.tarballprefix, 
               "%s/%s" % (sources_dir, self.archivename)]

        run(cmd)


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

    def archive(self, sources_dir=SOURCES_DIR):
        final_path = os.path.join(sources_dir, self.archivename)
        if os.path.exists(final_path):
            return
        run(["curl", "-k", "-L", "-o", final_path, self.orig_url])

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
    for cls in SCM.__subclasses__(): #pylint: disable-msg=E1101
        if cls.handles(ty):
            return cls(url, repomirror)
    return OtherSource(url, repomirror)
