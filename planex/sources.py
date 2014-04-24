import os
import os.path
import re
import urlparse
from planex import exceptions
from planex.globals import MIRROR_PATH

class SCM(object):
    def __init__(self, url):
        (scheme, host, path, _, _, fragment) = urlparse.urlparse(url)
        urlparts = url.split('#')
        repo_url = "%s://%s%s" % (scheme, host, path) # Strip of fragment
        repo_name = path.split('/')[-1]

        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        print "ty=%s repo_url=%s repo_name=%s fragment=%s" % (scheme, repo_url, repo_name, fragment)

        self.ty        = scheme
        self.repo_url  = repo_url
        self.repo_name = repo_name
        self.fragment  = fragment
 
    def clone_commands(self, path):
        raise Exception

class GitSource(SCM):
    def __init__(self, url):
        super(GitSource, self).__init__(url)
        self.git_branch = self.fragment or "master"

    @staticmethod
    def handles(ty):
        return ty=="git"

    def clone_commands(self, path):
        dst = os.path.join(path, self.repo_name)
        dst_dotgit = os.path.join(dst, ".git")

        # For a repo e.g. git://github.com/foo/bar.git
        # Check for a mirror of the form mirrorpath/github.com/foo/bar.git
        (_, host, localpath, _, _, _) = urlparse.urlparse(self.repo_url)
        mirrorpath=os.path.expanduser(os.path.join(MIRROR_PATH, host, localpath.strip("/")))
        print "mirrorpath=", mirrorpath
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
                'fetch',
                '--all',
                '-t'
            ]
            checkout_cmd = [
                'git',
                '--git-dir=%s' % dst_dotgit,
                '--work-tree=%s' % dst,
                'checkout',
                self.git_branch
            ]
            return [clone_cmd, reset_urls_cmd, fetch_cmd, checkout_cmd]
        else:
            cmd = [
                'git',
                'clone',
                self.repo_url,
                "--branch",
                self.git_branch,
                dst
            ]

            return [cmd]

class HgSource(SCM):
    def __init__(self, url):
        super(HgSource, self).__init__(url)

    @staticmethod
    def handles(ty):
        return ty=="hg"

    def clone_commands(self, path):
        if self.fragment:
            clone_url = self.repo_url + "#" + self.fragment
        else:
            clone_url = self.repo_url

        clone_url = re.sub('hg://', "http://", clone_url)

        return [[
            'hg',
            'clone',
            clone_url,
            os.path.join(path,self.repo_name)
        ]]

class FileSource(SCM):
    def __init__(self, url):
        super(FileSource, self).__init__(url)

    @staticmethod
    def handles(ty):
        return ty in ["file", "http", "https"]

    def clone_commands(self, path):
        return []

class OtherSource(SCM):
    @staticmethod
    def handles(ty):
        return False

    def clone_commands(self, path):
        return []

def Source(url):
    ty = url.split(":")[0]
    for cls in SCM.__subclasses__():
        if cls.handles(ty):
            return cls(url)
    return OtherSource(url)
