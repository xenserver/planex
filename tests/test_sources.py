import unittest
import mock
from mock import patch

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
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd')

        self.assertEquals(
            'git://github.com/xapi-project/xcp-networkd',
            source.repo_url)

    def test_repo_url_with_branch(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch')

        self.assertEquals(
            'git://github.com/xapi-project/xcp-networkd',
            source.repo_url)

    def test_branch(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd')

        self.assertEquals(
            'master',
            source.git_branch)

    def test_branch_if_branch_is_specified(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch')

        self.assertEquals(
            'somebranch',
            source.git_branch)

    def test_path_with_github_url(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch')

        self.assertEquals(
            'xcp-networkd', source.repo_name)

    @patch('os.path.exists')
    def test_clone_command_nomirror(self, mock_os_path_exists):
        mock_os_path_exists.return_value = False
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch')

        self.assertEquals(
            [[
                'git',
                'clone',
                'git://github.com/xapi-project/xcp-networkd',
                '--branch',
                'somebranch',
                'devel/xcp-networkd',
            ]],
            source.clone_commands("devel")
        )
