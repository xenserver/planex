import unittest
import StringIO

from planex import install
from planex import filesystem


class SpecsDirMixIn(object):
    def setUp(self):
        self.fs = fs = filesystem.Fake()
        self.specs_dir = install.SpecsDir(
            filesystem=fs,
            path='somepath')


class TestSpecsDirValidation(SpecsDirMixIn, unittest.TestCase):
    def test_no_directory_validation_fails(self):
        result = self.specs_dir.validate()

        self.assertTrue(result.failed)

    def test_no_directory_validation_message(self):
        result = self.specs_dir.validate()

        self.assertEquals(
            'Invalid specs dir: [somepath] is not an existing directory',
            result.message)

    def test_no_config_file(self):
        self.fs.contents = {
            'somepath': 'DIRECTORY'
        }

        result = self.specs_dir.validate()

        self.assertFalse(result.failed, msg=result.message)

    def test_file_found(self):
        self.fs.contents = {
            'somepath': 'DIRECTORY',
            'somepath/install.json': StringIO.StringIO('[]'),
        }

        result = self.specs_dir.validate()

        self.assertFalse(result.failed)

    def test_invalid_format(self):
        self.fs.contents = {
            'somepath': 'DIRECTORY',
            'somepath/install.json': StringIO.StringIO('invalid_json'),
        }

        result = self.specs_dir.validate()

        self.assertTrue(result.failed)
        self.assertEquals(
            'Invalid specs dir: [somepath/install.json] is not a json file',
            result.message)


class TestSpecsDirHasConfig(SpecsDirMixIn, unittest.TestCase):
    def test_config_file_missing(self):
        self.fs.contents = {
            'somepath': 'DIRECTORY'
        }

        self.assertFalse(self.specs_dir.has_config)

    def test_config_file_exists(self):
        self.fs.contents = {
            'somepath': 'DIRECTORY',
            'somepath/install.json': StringIO.StringIO(),
        }

        self.assertTrue(self.specs_dir.has_config)


class TestGetPackages(SpecsDirMixIn, unittest.TestCase):
    def test_no_packages(self):
        self.fs.contents = {
            'somepath': 'DIRECTORY',
            'somepath/install.json': StringIO.StringIO('[]'),
        }

        self.assertEquals([], self.specs_dir.get_packages())

    def test_packages_specified(self):
        self.fs.contents = {
            'somepath': 'DIRECTORY',
            'somepath/install.json': StringIO.StringIO("""
            [
                { "package-name": "a" },
                { "package-name": "b" }
            ]
            """),
        }

        self.assertEquals(['a', 'b'], self.specs_dir.get_packages())


class TestArgParsing(unittest.TestCase):
    def test_correct_call(self):
        args = install.parse_args_or_exit(['cdir', 'ddir'])

        self.assertEquals('cdir', args.component_dir)
        self.assertEquals('ddir', args.dest_dir)

    def test_incorrect_call(self):
        with self.assertRaises(SystemExit) as ctx:
            args = install.parse_args_or_exit(['cdir'])

        self.assertEquals(2, ctx.exception.code)


class TestLocalFileSystemImplementsMethods(unittest.TestCase):
    def test_methods_exist(self):
        fake = filesystem.Fake()
        real = filesystem.LocalFileSystem()

        for field in dir(filesystem.Fake):
            if not field.startswith('_'):
                attr = getattr(fake, field)
                if callable(attr):
                    self.assertTrue(
                        hasattr(real, field),
                        msg="LocalFilesystem does not implement {0}".format(
                            field))
