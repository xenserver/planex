import unittest
import mock
from mock import patch
import tempfile
import os
import subprocess
import shutil

from planex import sources
from planex import exceptions


class TestGitHubSource(unittest.TestCase):
    def setUp(self):
        # 'setUp' breaks Pylint's naming rules
        # pylint: disable=C0103
        self.working_dir = tempfile.mkdtemp()
        self.repos_dir = os.path.join(self.working_dir, "repos")

    def test_single_url(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd',self.repos_dir)

        self.assertEquals(
            'git://github.com/xapi-project/xcp-networkd',
            source.repo_url)

    def test_repo_url_with_branch(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch',self.repos_dir)

        self.assertEquals(
            'git://github.com/xapi-project/xcp-networkd',
            source.repo_url)

    def test_branch(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd',self.repos_dir)

        self.assertEquals(
            'master',
            source.git_committish)

    def test_branch_if_branch_is_specified(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch',self.repos_dir)

        self.assertEquals(
            'somebranch',
            source.git_committish)

    def test_path_with_github_url(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch',self.repos_dir)

        self.assertEquals(
            'xcp-networkd', source.repo_name)

    @patch('os.path.exists')
    def test_clone_command_nomirror(self, mock_os_path_exists):
        mock_os_path_exists.return_value = False
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch',self.repos_dir)

        self.assertEquals(
            [
                [
                    'git',
                    'clone',
                    'git://github.com/xapi-project/xcp-networkd',
                    '%s/repos/xcp-networkd' % self.working_dir
                ],
                [ 
                    'git',
                    '--git-dir=%s/repos/xcp-networkd/.git' % self.working_dir,
                    '--work-tree=%s/repos/xcp-networkd' % self.working_dir,
                    'checkout',
                    'somebranch'
                ]
            ],
            source.clone_commands()
        )

class GitTests(unittest.TestCase):
    def setUp(self):
        # 'setUp' breaks Pylint's naming rules
        # pylint: disable=C0103
        self.working_dir = tempfile.mkdtemp()
        self.repos_dir = os.path.join(self.working_dir, "repos")
        self.sources_dir = os.path.join(self.working_dir, "SOURCES")
        os.mkdir(self.sources_dir)
        os.mkdir(self.repos_dir)
        subprocess.call(["tar", "zxf", "tests/data/test-git.tar.gz", 
                         "-C", self.repos_dir])


    def tearDown(self):
        # 'tearDown' breaks Pylint's naming rules
        # pylint: disable=C0103
        shutil.rmtree(self.working_dir)
	

    def test_latest_tag(self):
        source = sources.Source("git://host.com/test.git",self.repos_dir)
        self.assertEqual(source.scmhash,'c48e124df2f82d910a8b60dfb54b666285debc04')
        self.assertEqual(source.version,"1.1.0")


    def test_fetch_git_source(self):
        source = sources.Source("git://host.com/test.git#"
                                "1.1.0/test-1.1.0.tar.gz",self.repos_dir)
        source.archive(sources_dir=self.sources_dir)
        expected_tarball = os.path.join(self.sources_dir, "test-1.1.0.tar.gz")
        self.assertTrue(os.path.exists(expected_tarball))


class HgTests(unittest.TestCase):
    def setUp(self):
        # pylint: disable=C0103
        self.working_dir = tempfile.mkdtemp()
        self.repos_dir = os.path.join(self.working_dir, "repos")
        self.sources_dir = os.path.join(self.working_dir, "SOURCES")
        os.mkdir(self.sources_dir)
        os.mkdir(self.repos_dir)
        subprocess.call(["tar", "zxf", "tests/data/test-hg.tar.gz",
                         "-C", self.repos_dir])


    def tearDown(self):
        # pylint: disable=C0103
        #shutil.rmtree(self.working_dir)
        pass

    def test_latest_tag(self):
        source = sources.Source("hg://host.com/test.hg",self.repos_dir)
        self.assertEqual(source.scmhash,"077fd701b2ad197af8e16360c8f4a6fa6f98c28c")
        self.assertEqual(source.version,"0")


    def test_fetch_hg_source(self):
        source = sources.Source("hg://host.com/test.hg",self.repos_dir)
        source.archive(sources_dir=self.sources_dir)
        expected_tarball = os.path.join(self.sources_dir, "test-0.tar.gz")
        self.assertTrue(os.path.exists(expected_tarball))
