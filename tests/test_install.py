import unittest
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
        self.assertFalse(self.specs_dir.has_config)

    def test_config_file_exists(self):
        self.specs_dir.root.setcontents('install.json', '')

        self.assertTrue(self.specs_dir.has_config)


class TestGetPackages(SpecsDirMixIn, unittest.TestCase):
    def test_no_packages(self):
        self.specs_dir.root.setcontents('install.json', '[]')
        self.assertEquals([], self.specs_dir.get_package_names())

    def test_packages_specified(self):
        self.specs_dir.root.setcontents(
            'install.json', StringIO.StringIO("""
            [
                { "package-name": "a" },
                { "package-name": "b" }
            ]
            """))

        self.assertEquals(['a', 'b'], self.specs_dir.get_package_names())


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
        package = install.RPMPackage('filepath', executor=executor)
        executor.results[(
            'rpm', '-qp', 'filepath', '--qf', '%{name}'
        )] = install.ExecutionResult(
            return_code=0,
            stdout='  somename  \n',
            stderr='ignored')

        self.assertEquals('somename', package.name)

