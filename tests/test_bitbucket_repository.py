# Run these tests with 'nosetests':
#   install the 'python-nose' package (Fedora/CentOS or Ubuntu)
#   run 'nosetests' in the root of the repository

import json
import unittest

import planex.repository


class BasicTests(unittest.TestCase):
    # unittest.TestCase has more methods than Pylint permits
    # pylint: disable=R0904

    def setUp(self):
        with open("tests/data/bitbucket-repo.json") as fileh:
            self.data = json.load(fileh)

    def test_urls(self):
        for tcase in self.data:
            repo = planex.repository.Repository(tcase['URL'])
            self.assertEqual(repo.clone_url, tcase['clone_URL'])
            self.assertEqual(repo.branch, tcase['branch'])
            self.assertEqual(repo.tag, tcase['tag'])
