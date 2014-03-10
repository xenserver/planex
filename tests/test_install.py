import unittest
import mock
import StringIO
from fs.opener import fsopendir

from planex import install


class SpecsDirMixIn(object):
    def setUp(self):
        self.specs_dir = install.SpecsDir(
            root=fsopendir('ram:///'))


class TestSpecsDirValidation(SpecsDirMixIn, unittest.TestCase):
    def test_no_config_file(self):
        result = self.specs_dir.validate()

        self.assertFalse(result.failed, msg=result.message)

    def test_file_found(self):
        self.specs_dir.root.setcontents('install.json', '[]')

        result = self.specs_dir.validate()

        self.assertFalse(result.failed)

    def test_invalid_format(self):
        self.specs_dir.root.setcontents('install.json', 'invalid_json')

        result = self.specs_dir.validate()

        self.assertTrue(result.failed)
        self.assertEquals(
            'Invalid specs dir: [install.json] is not a json file',
            result.message)


class TestSpecsDirHasConfig(SpecsDirMixIn, unittest.TestCase):
    def test_config_file_missing(self):
        self.assertFalse(self.specs_dir.has_install_config)

    def test_config_file_exists(self):
        self.specs_dir.root.setcontents('install.json', '')

        self.assertTrue(self.specs_dir.has_install_config)


class TestGetPackages(SpecsDirMixIn, unittest.TestCase):
    def test_no_packages(self):
        self.specs_dir.root.setcontents('install.json', '[]')
        self.assertEquals([], self.specs_dir.get_package_names_to_install())

    def test_packages_specified(self):
        self.specs_dir.root.setcontents(
            'install.json', StringIO.StringIO("""
            [
                { "package-name": "a" },
                { "package-name": "b" }
            ]
            """))

        self.assertEquals(
            ['a', 'b'], self.specs_dir.get_package_names_to_install())


class TestArgParsing(unittest.TestCase):
    def test_correct_call(self):
        args = install.parse_args_or_exit(['cdir', 'ddir'])

        self.assertEquals('cdir', args.component_dir)
        self.assertEquals('ddir', args.dest_dir)

    def test_incorrect_call(self):
        with self.assertRaises(SystemExit) as ctx:
            args = install.parse_args_or_exit(['cdir'])

        self.assertEquals(2, ctx.exception.code)


class TestRPM(unittest.TestCase):
    def test_get_name(self):
        executor = install.FakeExecutor()
        filesystem = fsopendir('ram:///')
        rpmsdir = install.RPMSDir(filesystem, executor)
        package = install.RPMPackage(rpmsdir, 'filepath')
        executor.results[(
            'rpm', '-qp', '/some/filepath', '--qf', '%{name}'
        )] = install.ExecutionResult(
            return_code=0,
            stdout='  somename  \n',
            stderr='ignored')

        # As in-memory filesystem does not implement getsyspath,
        # it needs to be replaced with a stub
        with mock.patch.object(filesystem, 'getsyspath') as getsyspath:
            getsyspath.return_value = '/some/filepath'
            self.assertEquals('somename', package.name)
            getsyspath.assert_called_once_with('filepath')


class TestRPMSDir(unittest.TestCase):
    def test_init(self):
        rpmsdir = install.RPMSDir('root', 'executor')

        self.assertEquals('root', rpmsdir.root)
        self.assertEquals('executor', rpmsdir.executor)

    def test_get_rpms(self):
        fs = fsopendir('ram:///')
        rpmsdir = install.RPMSDir(fs, None)
        fs.createfile('fname1.rpm')

        self.assertEquals(1, len(rpmsdir.rpms))

    def test_rpms_are_objects_with_names(self):
        fs = fsopendir('ram:///')
        rpmsdir = install.RPMSDir(fs, 'executor')
        fs.createfile('fname1.rpm')

        rpm, = rpmsdir.rpms

        self.assertEquals(rpmsdir, rpm.rpmsdir)
        self.assertEquals('fname1.rpm', rpm.path)
