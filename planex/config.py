"""Classes for reading configuration values from INI-style files."""


import os.path

from ConfigParser import RawConfigParser


class Configuration(object):
    """Represents a set of configuration options"""
    # pylint: disable=R0903
    searchPath = ('/etc/planexrc',
                  os.path.expanduser('~/.planexrc'),
                  '.planexrc')

    @classmethod
    def get(cls, section, option, default=None):
        """Return the value for an option within a section"""
        config = cls._config()
        if config.has_section(section) and config.has_option(section, option):
            return config.get(section, option)
        return default

    @classmethod
    def _config(cls):
        """Return a ConfigParser object"""
        config = RawConfigParser()
        config.read(cls.searchPath)
        return config
