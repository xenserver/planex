"""
General execeptions used in planex
"""


class NoSuchFile(Exception):
    """File does not exist"""
    pass


class InvalidURL(Exception):
    """URL is invalid"""
    pass


class NoRepository(Exception):
    """No repository exists at path"""
    pass
