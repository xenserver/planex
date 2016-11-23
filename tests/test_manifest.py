import json
import unittest
import mock

import planex.spec
import planex.cmd.manifest


class BasicTests(unittest.TestCase):
    # unittest.TestCase has more methods than Pylint permits
    # pylint: disable=R0904
    def setUp(self):
        path = 'tests/data/manifest/{}.{}'
        self.name_1 = 'branding-xenserver'
        self.name_2 = 'vhostmd'
        self.name_3 = 'blktap'

        self.spec = {}
        self.spec[self.name_1] = planex.spec.Spec(
            path.format(self.name_1, 'spec')
        )
        self.spec[self.name_2] = planex.spec.Spec(
            path.format(self.name_2, 'spec')
        )
        self.spec[self.name_3] = planex.spec.Spec(
            path.format(self.name_3, 'spec')
        )

        self.link = {}
        self.link[self.name_1] = None
        with open(path.format(self.name_2, 'lnk')) as fileh:
            self.link[self.name_2] = json.load(fileh)
        with open(path.format(self.name_3, 'lnk')) as fileh:
            self.link[self.name_3] = json.load(fileh)

        self.expected_manifest = {}
        with open(path.format(self.name_1, 'json')) as fileh:
            self.expected_manifest[self.name_1] = json.load(fileh)
        with open(path.format(self.name_2, 'json')) as fileh:
            self.expected_manifest[self.name_2] = json.load(fileh)
        with open(path.format(self.name_3, 'json')) as fileh:
            self.expected_manifest[self.name_3] = json.load(fileh)

        with open(path.format('git_ls_remote_out', 'json')) as fileh:
            self.git_ls_remote_out = json.load(fileh)

    @mock.patch('planex.repository.git_ls_remote')
    def test_generate_manifest_1(self, mock_git_ls_remote):
        # Standard repo (specfile only)

        mock_git_ls_remote.return_value = self.git_ls_remote_out[self.name_1]

        manifest = planex.cmd.manifest.generate_manifest(
            self.spec[self.name_1],
            self.link[self.name_1]
        )

        self.assertEqual(manifest, self.expected_manifest[self.name_1])

    @mock.patch('planex.repository.git_ls_remote')
    def test_generate_manifest_2(self, mock_git_ls_remote):
        # Source tarball and patchqueue (specfile and lnkfile)

        mock_git_ls_remote.return_value = self.git_ls_remote_out[self.name_2]

        manifest = planex.cmd.manifest.generate_manifest(
            self.spec[self.name_2],
            self.link[self.name_2]
        )

        self.assertEqual(manifest, self.expected_manifest[self.name_2])

    @mock.patch('planex.repository.git_ls_remote')
    def test_generate_manifest_3(self, mock_git_ls_remote):
        # Repo and patchqueue (specfile and lnkfile)

        mock_git_ls_remote.side_effect = self.git_ls_remote_out[self.name_3]

        manifest = planex.cmd.manifest.generate_manifest(
            self.spec[self.name_3],
            self.link[self.name_3]
        )

        self.assertEqual(manifest, self.expected_manifest[self.name_3])
