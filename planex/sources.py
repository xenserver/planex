import re
from planex import exceptions


class GitSource(object):
    def __init__(self, url):
        match = re.match(
            r'''
            ^
            (?P<repo_url>
                git://(?P<server>[^#^/]+)/
                (?P<remote_path>[^#]+)
            )
            (\#(?P<branch>.+))?
            $
            ''',
            url, re.VERBOSE)
        if not match:
            raise exceptions.InvalidURL(url)
        self.repo_url = match.group('repo_url')
        self.remote_path = match.group('remote_path')
        self.server = match.group('server')

    @property
    def path(self):
        if not self.remote_path.endswith('.git'):
            return self.remote_path + '.git'
        return self.remote_path

    def clone_commands(self, filesystem):
        return [
            'git',
            'clone',
            self.repo_url,
            filesystem.getsyspath(self.path)
        ]
