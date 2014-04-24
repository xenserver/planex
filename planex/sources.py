import os
import re
from planex import exceptions

class SCM(object):
    def __init__(self, url):
        ty = url.split(":")[0]
        urlparts = url.split('#')
        repo_url = urlparts[0]
        repo_name = urlparts[0].split('/')[-1]

        branch= None
        if len(urlparts)>1:
            branch = urlparts[1]
        
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        self.ty        = ty
        self.repo_url  = repo_url
        self.repo_name = repo_name
        self.branch    = branch
 
    def clone_commands(self, path):
        raise Exception

class GitSource(SCM):
    def __init__(self, url):
        super(GitSource, self).__init__(url)

    @staticmethod
    def handles(ty):
        return ty=="git"

    def clone_commands(self, path):
        if self.branch:
            branchcmd = ["--branch",self.branch]
        else:
            branchcmd = []

        cmd = [
            'git',
            'clone',
            self.repo_url,
            os.path.join(path,self.repo_name)
        ] + branchcmd

        return cmd

class HgSource(SCM):
    def __init__(self, url):
        super(HgSource, self).__init__(url)

    @staticmethod
    def handles(ty):
        return ty=="hg"

    def clone_commands(self, path):
        if self.branch:
            clone_url = self.repo_url + "#" + self.branch
        else:
            clone_url = self.repo_url

        clone_url = re.sub('hg://', "http://", clone_url)

        return [
            'hg',
            'clone',
            clone_url,
            os.path.join(path,self.repo_name)
        ]

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
