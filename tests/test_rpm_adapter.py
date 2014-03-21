import unittest
from fs.opener import fsopendir

from planex import rpm_adapter


class TestSimpleRPM(unittest.TestCase):
    def test_get_sources(self):
        ramfs = fsopendir('ram:///')
        ramfs.setcontents('somefile', 'Source: somesource')

        rpm = rpm_adapter.SimpleRPM()
        sources = rpm.get_sources('somefile', ramfs)
        self.assertEquals(['somesource'], sources)
