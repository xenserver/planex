import re
from planex import exceptions


class GitSource(object):
    def __init__(self, url):
        match = re.match(
            r'''
            ^
            (?P<repo_url>
                git://github.com/
                (?P<username>[^#^/]+)/
                (?P<reponame>[^#^/]+)
            )
            (\#(?P<branch>.+))?
            $
            ''',
            url, re.VERBOSE)
        if not match:
            raise exceptions.InvalidURL(url)
        self.repo_url = match.group('repo_url')
        self.branch = match.group('branch') or 'master'
        self.username = match.group('username')
        self.reponame = match.group('reponame')

    @property
    def path(self):
        return '/'.join([self.username, self.reponame + '.git'])

    def clone_commands(self, filesystem):
        return [
            'git',
            'clone',
            self.repo_url,
            '--branch',
            self.branch,
            filesystem.getsyspath(self.path)
        ]
