"""Tests for repository URL parsers"""

import json
import unittest
import mock

import planex.repository


class BasicTests(unittest.TestCase):
    """Basic BitBucket URL parser tests"""

    def setUp(self):
        with open("tests/data/bitbucket-repo.json") as fileh:
            self.data = json.load(fileh)

    @mock.patch('planex.repository.requests.get')
    @mock.patch('planex.repository.git_ls_remote')
    def test_urls(self, mock_git_ls_remote, mock_requests_get):
        """Well-formed BitBucket URLs are parsed correctly"""
        for tcase in self.data:
            mock_git_ls_remote.return_value = tcase['git_ls_remote_out']
            requests_response = mock.Mock()
            requests_response.json.return_value = tcase['requests_get_out']
            mock_requests_get.return_value = requests_response
            repo = planex.repository.Repository(tcase['URL'])
            self.assertEqual(repo.clone_url, tcase['clone_URL'])
            self.assertEqual(repo.branch, tcase['branch'])
            self.assertEqual(repo.tag, tcase['tag'])
            self.assertEqual(repo.commitish, tcase['commitish'])
            self.assertEqual(repo.sha1, tcase['sha1'])


class GitHubTests(unittest.TestCase):
    """Basic GitHub URL parser tests"""

    def setUp(self):
        with open("tests/data/github-repo.json") as fileh:
            self.data = json.load(fileh)

    @mock.patch('planex.repository.git_ls_remote')
    def test_urls(self, mock_git_ls_remote):
        """Well-formed GitHub URLs are parsed correctly"""
        for tcase in self.data:
            mock_git_ls_remote.return_value = tcase['git_ls_remote_out']
            repo = planex.repository.Repository(tcase['URL'])
            self.assertEqual(repo.clone_url, tcase['clone_URL'])
            self.assertEqual(repo.branch, tcase['branch'])
            self.assertEqual(repo.tag, tcase['tag'])
            self.assertEqual(repo.sha1, tcase['sha1'])


class GitWebTests(unittest.TestCase):
    """Basic GitWeb URL parser tests"""

    def setUp(self):
        with open("tests/data/gitweb-repo.json") as fileh:
            self.data = json.load(fileh)

    @mock.patch('planex.repository.git_ls_remote')
    def test_urls(self, mock_git_ls_remote):
        """Well-formed GitWeb URLs are parsed correctly"""
        for tcase in self.data:
            mock_git_ls_remote.return_value = tcase['git_ls_remote_out']
            repo = planex.repository.Repository(tcase['URL'])
            self.assertEqual(repo.clone_url, tcase['clone_URL'])
            self.assertEqual(repo.branch, tcase['branch'])
            self.assertEqual(repo.tag, tcase['tag'])
            self.assertEqual(repo.sha1, tcase['sha1'])
