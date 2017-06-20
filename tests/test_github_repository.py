"""Tests for BitBucket URL parser"""

import json
import unittest
import mock

import planex.repository


class BasicTests(unittest.TestCase):
    """Basic GitHub URL parser tests"""
    # unittest.TestCase has more methods than Pylint permits
    # pylint: disable=R0904

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
