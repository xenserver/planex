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


class TestGitHubSource(unittest.TestCase):
    def test_single_url(self):
        source = sources.GitHubSource(
            'git://github.com/xapi-project/xcp-networkd')

        self.assertEquals(
            'git://github.com/xapi-project/xcp-networkd',
            source.repo_url)

    def test_repo_url_with_branch(self):
        source = sources.GitHubSource(
            'git://github.com/xapi-project/xcp-networkd#somebranch')

        self.assertEquals(
            'git://github.com/xapi-project/xcp-networkd',
            source.repo_url)

    def test_branch(self):
        source = sources.GitHubSource(
            'git://github.com/xapi-project/xcp-networkd')

        self.assertEquals(
            'master',
            source.branch)

    def test_branch_if_branch_is_specified(self):
        source = sources.GitHubSource(
            'git://github.com/xapi-project/xcp-networkd#somebranch')

        self.assertEquals(
            'somebranch',
            source.branch)

    def test_construction_fails_with_bad_protocol(self):
        self.assertRaises(exceptions.InvalidURL, sources.GitHubSource, 'll')

    def test_construction_fails_if_path_is_too_ling(self):
        self.assertRaises(
            exceptions.InvalidURL,
            sources.GitHubSource, 'git://github.com/a/b/c/d')

    def test_path_with_github_url(self):
        source = sources.GitHubSource(
            'git://github.com/xapi-project/xcp-networkd#somebranch')

        self.assertEquals(
            'xapi-project/xcp-networkd.git', source.path)

    def test_clone_command(self):
        filesystem = make_ramfs()

        source = sources.GitHubSource(
            'git://github.com/xapi-project/xcp-networkd#somebranch')

        self.assertEquals(
            [
                'git',
                'clone',
                'git://github.com/xapi-project/xcp-networkd',
                '--branch',
                'somebranch',
                'SYSPATH:xapi-project/xcp-networkd.git',
            ],
            source.clone_commands(filesystem)
        )
