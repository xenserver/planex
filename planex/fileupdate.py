"""
The FileUpdate context manager helps the caller to avoid updating a
file on disk if its contents would not be changed.   In particular,
the file's modification timestamp will not be changed, so make will
not rebuild any files which depend on it.
"""

import errno
import hashlib
import logging
import os
import shutil
import tempfile


def same_size(infile, outfile):
    """
    Returns true if infile and outfile are the same size
    """
    infile.flush()

    insize = os.fstat(infile.fileno()).st_size
    outsize = os.fstat(outfile.fileno()).st_size

    logging.debug("infile size:  %d bytes", insize)
    logging.debug("outfile size: %d bytes", outsize)

    return insize == outsize


def same_hash(infile, outfile):
    """
    Returns true if the contents of infile and outfile have the same hash
    """
    infile.seek(0)
    outfile.seek(0)

    inhash = hashlib.md5()
    inhash.update(infile.read())
    outhash = hashlib.md5()
    outhash.update(outfile.read())

    logging.debug("infile hash:  %s", inhash.hexdigest())
    logging.debug("outfile hash: %s", outhash.hexdigest())

    return inhash.digest() == outhash.digest()


class FileUpdate(object):
    """
    FileUpdate takes a target filename as its only argument and returns
    a temporary file object.   When the caller exits the context manager,
    it compares the contents of the temporary file to those of the target
    file.  If the contents are the same, the disk file is not updated and
    retains its original contents and modification time; if the contents
    are different, the contents of the temporary file are copied over
    the disk file and its last modification timestamp is updated.
    """

    # Some versions of pylint report the too-few-public-methods warning for
    # context managers

    # pylint: disable=R0903
    def __init__(self, filename):
        self.infile = tempfile.TemporaryFile()
        self.filename = filename

    def __enter__(self):
        return self.infile

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            with open(self.filename, 'rb') as outfile:
                if (same_size(self.infile, outfile) and
                        same_hash(self.infile, outfile)):
                    logging.debug("No changes")
                    return

        except IOError as ioe:
            if ioe.errno != errno.ENOENT:
                raise

        logging.debug("Copying infile to outfile")
        self.infile.seek(0)
        with open(self.filename, 'wb') as outfile:
            shutil.copyfileobj(self.infile, outfile)
