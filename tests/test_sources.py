import unittest
import mock

from fs.opener import fsopendir

from planex import sources
from planex import exceptions


def make_ramfs():
    def getsyspath(fname):
        return 'SYSPATH:' + fname

    fs = fsopendir('ram:///')
    fs.getsyspath = mock.Mock(side_effect=getsyspath)
    return fs


class TestGitSource(unittest.TestCase):
    def test_single_url(self):
        source = sources.GitSource(
            'git://github.com/xapi-project/xcp-networkd')

        self.assertEquals(
            'git://github.com/xapi-project/xcp-networkd',
            source.repo_url)

    def test_repo_url_with_branch(self):
        source = sources.GitSource(
            'git://github.com/xapi-project/xcp-networkd#somebranch')

        self.assertEquals(
            'git://github.com/xapi-project/xcp-networkd',
            source.repo_url)

    def test_construction_fails_with_bad_protocol(self):
        self.assertRaises(exceptions.InvalidURL, sources.GitSource, 'll')

    def test_long_remote_path(self):
        source = sources.GitSource(
            'git://github.com/a/b/c/d/e/f/g')

        self.assertEquals(
            'a/b/c/d/e/f/g.git',
            source.path)

    def test_path_with_github_url(self):
        source = sources.GitSource(
            'git://github.com/xapi-project/xcp-networkd#somebranch')

        self.assertEquals(
            'xapi-project/xcp-networkd.git', source.path)

    def test_clone_command(self):
        filesystem = make_ramfs()

        source = sources.GitSource(
            'git://github.com/xapi-project/xcp-networkd#somebranch')

        self.assertEquals(
            [
                'git',
                'clone',
                'git://github.com/xapi-project/xcp-networkd',
                'SYSPATH:xapi-project/xcp-networkd.git',
            ],
            source.clone_commands(filesystem)
        )
