import unittest
import mock
from mock import patch
import tempfile
import os
import subprocess
import shutil

from planex import sources
from planex import exceptions
from planex import clone


class TestGitHubSource(unittest.TestCase):
    def setUp(self):
        # 'setUp' breaks Pylint's naming rules
        # pylint: disable=C0103
        self.working_dir = tempfile.mkdtemp()
        self.repos_mirror_path = os.path.join(self.working_dir,"repos_mirror")
        self.repos_path = os.path.join(self.working_dir,"repos")
        os.mkdir(self.repos_mirror_path)
        os.mkdir(self.repos_path)        
        self.config = clone.parse_args_or_exit(
            ['config_dir',
             '--repos_mirror_path',self.repos_mirror_path,
             '--repos_path',self.repos_path])


    def tearDown(self):
        # 'tearDown' breaks Pylint's naming rules
        # pylint: disable=C0103
        shutil.rmtree(self.working_dir)

        
    def test_single_url(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd',self.config)
        self.assertEquals(
            'git://github.com/xapi-project/xcp-networkd',
            source.repo_url)

    def test_repo_url_with_branch(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch',self.config)

        self.assertEquals(
            'git://github.com/xapi-project/xcp-networkd',
            source.repo_url)

    def test_branch(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd',self.config)

        self.assertEquals(
            'master',
            source.git_committish)

    def test_branch_if_branch_is_specified(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch',self.config)

        self.assertEquals(
            'somebranch',
            source.git_committish)

    def test_path_with_github_url(self):
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch',self.config)

        self.assertEquals(
            'xcp-networkd', source.repo_name)

    @patch('os.path.exists')
    def test_clone_command_nomirror(self, mock_os_path_exists):
        mock_os_path_exists.return_value = False
        source = sources.Source(
            'git://github.com/xapi-project/xcp-networkd#somebranch',self.config)

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

    @patch('os.path.exists')
    def test_clone_command_mirror(self, mock_os_path_exists):
        mock_os_path_exists.return_value = False
        repo_url = 'git://github.com/xapi-project/xcp-networkd'
        source = sources.Source('%s#somebranch' % repo_url,self.config)
        mock_os_path_exists.return_value = True
        self.assertEquals(
            [
                [
                    'git',
                    'clone',
                    '%s/github.com/xapi-project/xcp-networkd' % self.repos_mirror_path,
                    '%s/repos/xcp-networkd' % self.working_dir
                ],
                [ 
                    'git',
                    '--git-dir=%s/repos/xcp-networkd/.git' % self.working_dir,
                    'remote',
                    'set-url',
                    'origin',
                    repo_url
                ],
                [
                    'git',
                    '--git-dir=%s/repos/xcp-networkd/.git' % self.working_dir,
                    'remote',
                    'fetch',
                    '--all',
                    '-t'
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
        self.config_dir = os.path.join(self.working_dir,"config_dir")
        self.repos_dir = os.path.join(self.working_dir,"repos")
        self.sources_dir = os.path.join(self.working_dir, "SOURCES")
        self.config = clone.parse_args_or_exit(
            [self.config_dir,
             '--repos_path',self.repos_dir])
        os.mkdir(self.sources_dir)
        os.mkdir(self.config_dir)
        os.mkdir(self.repos_dir)
        subprocess.call(["tar", "zxf", "tests/data/test-git.tar.gz", 
                         "-C", self.repos_dir])
        subprocess.call(["tar", "zxf", "tests/data/test2-git.tar.gz", 
                         "-C", self.repos_dir])


    def tearDown(self):
        # 'tearDown' breaks Pylint's naming rules
        # pylint: disable=C0103
        shutil.rmtree(self.working_dir)
	

    def test_latest_tag(self):
        source = sources.Source("git://host.com/test.git",self.config)
        self.assertEqual(source.scmhash,'c48e124df2f82d910a8b60dfb54b666285debc04')
        self.assertEqual(source.version,"1.1.0")


    def test_latest_tag_notags(self):
        source = sources.Source("git://host.com/test2.git",self.config)
        self.assertEqual(source.scmhash,'a71b6ead4f09c98f2602a081dd09c6c7abfe835c')
        self.assertEqual(source.version,"2")


    def test_fetch_git_source(self):
        source = sources.Source("git://host.com/test.git#"
                                "1.1.0/test-1.1.0.tar.gz",self.config)
        source.archive(sources_dir=self.sources_dir)
        expected_tarball = os.path.join(self.sources_dir, "test-1.1.0.tar.gz")
        self.assertTrue(os.path.exists(expected_tarball))

    def test_fetch_git_source_fastpath(self):
        with patch('os.path.exists') as mock_os_path_exists:
            mock_os_path_exists.return_value = True
            source = sources.Source("git://host.com/test.git#"
                                    "1.1.0/test-1.1.0.tar.gz",self.config)
            expected_tarball = os.path.join(self.sources_dir, "test-1.1.0.tar.gz")
            try:
                os.remove(expected_tarball)
            except:
                pass
            source.archive(sources_dir=self.sources_dir)

        self.assertFalse(os.path.exists(expected_tarball))


    def test_extendedurl(self):
        source = sources.Source("git://host.com/test.git",self.config)
        self.assertEqual(source.extendedurl,"git://host.com/test.git#c48e124df2f82d910a8b60dfb54b666285debc04/test-1.1.0.tar.gz")

    def test_scmhash(self):
        source = sources.Source("git://host.com/test.git#7519f065cdf315522d9351dc9a87ea3926550e6f",self.config)
        self.assertEqual(source.git_committish,"7519f065cdf315522d9351dc9a87ea3926550e6f")


class HgTests(unittest.TestCase):
    def setUp(self):
        # pylint: disable=C0103
        self.working_dir = tempfile.mkdtemp()
        self.repos_dir = os.path.join(self.working_dir, "repos")        
        self.config_dir = os.path.join(self.working_dir, "config")
        self.sources_dir = os.path.join(self.working_dir, "SOURCES")
        os.mkdir(self.sources_dir)
        os.mkdir(self.repos_dir)
        os.mkdir(self.config_dir)
        self.config = clone.parse_args_or_exit(
            [self.config_dir,
             '--repos_path',self.repos_dir])
        subprocess.call(["tar", "zxf", "tests/data/test-hg.tar.gz",
                         "-C", self.repos_dir])


    def tearDown(self):
        # pylint: disable=C0103
        shutil.rmtree(self.working_dir)
        pass

    def test_latest_tag(self):
        source = sources.Source("hg://host.com/test.hg",self.config)
        self.assertEqual(source.scmhash,"077fd701b2ad197af8e16360c8f4a6fa6f98c28c")
        self.assertEqual(source.version,"0")


    def test_fetch_hg_source(self):
        source = sources.Source("hg://host.com/test.hg",self.config)
        source.archive(sources_dir=self.sources_dir)
        expected_tarball = os.path.join(self.sources_dir, "test-0.tar.gz")
        self.assertTrue(os.path.exists(expected_tarball))

    def test_fetch_hg_source_fastpath(self):
        with patch('os.path.exists') as mock_os_path_exists:
            mock_os_path_exists.return_value = True
            source = sources.Source("hg://host.com/test.hg",self.config)
            expected_tarball = os.path.join(self.sources_dir, "test-0.tar.gz")
            try:
                os.remove(expected_tarball)
            except:
                pass
                source.archive(sources_dir=self.sources_dir)

        self.assertFalse(os.path.exists(expected_tarball))

    def test_clone_command_nofrag(self):
        source = sources.Source(
            'hg://host.com/foo.hg',self.config)

        self.assertEquals(
            [
                [
                    'hg',
                    'clone',
                    'http://host.com/foo.hg',
                    '%s/repos/foo.hg' % self.working_dir
                ]
            ],
            source.clone_commands()
        )

    def test_clone_command_withfrag(self):
        source = sources.Source(
            'hg://host.com/foo.hg#bar',self.config)

        self.assertEquals(
            [
                [
                    'hg',
                    'clone',
                    'http://host.com/foo.hg#bar',
                    '%s/repos/foo.hg' % self.working_dir
                ]
            ],
            source.clone_commands()
        )


class FileTests(unittest.TestCase):
    def setUp(self):
        # pylint: disable=C0103
        self.working_dir = tempfile.mkdtemp()
        self.repos_dir = os.path.join(self.working_dir, "repos")        
        self.config_dir = os.path.join(self.working_dir, "config")
        self.sources_dir = os.path.join(self.working_dir, "SOURCES")
        os.mkdir(self.sources_dir)
        os.mkdir(self.repos_dir)
        os.mkdir(self.config_dir)
        self.config = clone.parse_args_or_exit(
            [self.config_dir,
             '--repos_path',self.repos_dir])
        subprocess.call(["tar", "zxf", "tests/data/test-hg.tar.gz",
                         "-C", self.repos_dir])

    def tearDown(self):
        # pylint: disable=C0103
        shutil.rmtree(self.working_dir)

        
    def test_archive(self):
        source = sources.Source(
            'file://%s/tests/data/test-hg.tar.gz' % os.getcwd(),self.config)
        source.archive(sources_dir=self.sources_dir)
        self.assertTrue(os.path.exists(os.path.join(self.sources_dir,"test-hg.tar.gz")))

    def test_archive_fastpath(self):
        with patch('os.path.exists') as mock_os_path_exists:
            mock_os_path_exists.return_value = True
            source = sources.Source(
                'file://%s/tests/data/test-hg.tar.gz' % os.getcwd(),self.config)
            expected_tarball = os.path.join(self.sources_dir, "test-hg.tar.gz")
            try:
                os.remove(expected_tarball)
            except:
                pass
            source.archive(sources_dir=self.sources_dir)

        self.assertFalse(os.path.exists(expected_tarball))

    def test_clone(self):
        source = sources.Source(
            'file://%s/tests/data/test-hg.tar.gz' % os.getcwd(),self.config)
        self.assertEqual(source.clone_commands(), [])

class OtherTests(unittest.TestCase):
    def setUp(self):
        self.config = clone.parse_args_or_exit(
            ["/tmp/",
             '--repos_path',""])

# We don't actually care about this, this is just to get our coverage report up!
    def test_other(self):
        source=sources.Source("foo://baz.com/bar", self.config)
        source.archive()
        self.assertEqual(source.clone_commands(), [])
