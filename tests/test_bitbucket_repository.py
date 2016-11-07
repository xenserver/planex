# Run these tests with 'nosetests':
#   install the 'python-nose' package (Fedora/CentOS or Ubuntu)
#   run 'nosetests' in the root of the repository

import json
import unittest
import mock

import planex.repository


class BasicTests(unittest.TestCase):
    # unittest.TestCase has more methods than Pylint permits
    # pylint: disable=R0904

    def setUp(self):
        with open("tests/data/bitbucket-repo.json") as fileh:
            self.data = json.load(fileh)

    @mock.patch('planex.repository.requests.get')
    @mock.patch('planex.repository.git_ls_remote')
    def test_urls(self, mock_git_ls_remote, mock_requests_get):
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
