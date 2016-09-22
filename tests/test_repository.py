# Run these tests with 'nosetests':
#   install the 'python-nose' package (Fedora/CentOS or Ubuntu)
#   run 'nosetests' in the root of the repository

import glob
import os
import os.path
import shutil
import sys
import tempfile
import unittest

import planex.repository


class BasicTests(unittest.TestCase):
    # unittest.TestCase has more methods than Pylint permits
    # pylint: disable=R0904

    def test_github(self):
        url = "https://github.com/xapi-project/xen-api/archive/v1.10.1/xen-api-1.10.1.tar.gz"
        repo = planex.repository.Repository(url)
        self.assertEqual(repo.clone_url, "ssh://git@github.com/xapi-project/xen-api.git")
        self.assertEqual(repo.tag, "v1.10.1")

    def test_bitbucket(self):
        url = "https://code.citrite.net/rest/archive/latest/projects/~SIMONR/repos/brocade-bna/archive?format=tgz#/Brocade-bna-3.2.1.1.tar.gz"
        repo = planex.repository.Repository(url)
        self.assertEqual(repo.clone_url, "ssh://git@code.citrite.net/~SIMONR/brocade-bna.git")
        self.assertEqual(repo.branch, "master")
        self.assertEqual(repo.tag, None)
        url = "https://code.citrite.net/rest/archive/latest/projects/XS/repos/linux-firmware/archive?at=refs%2Ftags%2F20160622&format=tar.gz#/linux-firmware.tar.gz"
        repo = planex.repository.Repository(url)
        self.assertEqual(repo.clone_url, "ssh://git@code.citrite.net/XS/linux-firmware.git")
        self.assertEqual(repo.branch, None)
        self.assertEqual(repo.tag, "20160622")
        url = "https://code.citrite.net/rest/archive/latest/projects/XS/repos/lvm2/archive?at=refs%2Fheads%2Fxenserver_patches&format=tar#/lvm2.patches.tar"
        repo = planex.repository.Repository(url)
        self.assertEqual(repo.clone_url, "ssh://git@code.citrite.net/XS/lvm2.git")
        self.assertEqual(repo.branch, "xenserver_patches")
        self.assertEqual(repo.tag, None)

    def test_hg(self):
        url = "http://hg.uk.xensource.com/git/carbon/trunk/xsconsole.git/snapshot/refs/heads/master#/xsconsole.tar.bz2"
        repo = planex.repository.Repository(url)
        self.assertEqual(repo.clone_url,
                         "git://hg.uk.xensource.com/carbon/trunk/xsconsole.git")
        self.assertEqual(repo.branch, "master")
        self.assertEqual(repo.tag, None)
        url = "http://hg.uk.xensource.com/git/carbon/trunk-ring0/driver-emulex-be2net.git/snapshot/refs/tags/11.0.235.4.tar.gz#/emulex-be2net-11.0.235.4.tar.gz"
        repo = planex.repository.Repository(url)
        self.assertEqual(repo.clone_url,
                         "git://hg.uk.xensource.com/carbon/trunk-ring0/driver-emulex-be2net.git")
        self.assertEqual(repo.branch, None)
        self.assertEqual(repo.tag, "11.0.235.4")
