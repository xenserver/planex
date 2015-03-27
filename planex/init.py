#!/usr/bin/env python

"""
Creates or regenerates a Makefile with special planex-init comments
"""

import os
import logging
from planex.util import setup_sigint_handler

MAKEFILE_PATH = "/usr/share/planex"


def create_makefile():
    """ Checks if a Makefile exists with special planex-init comments in it.
    If not, it creates or regenerates the Makefile while preserving its
    existing contents.
    """
    name = "Makefile"

    defaults = [".PHONY: default\n",
                "default: rpms\n",
                "DIST=.fc21\n",
                "# FETCH_EXTRA_FLAGS=--no-package-name-check\n",
                "# DEPEND_EXTRA_FLAGS=--no-package-name-check\n"]
    firstline = "# Start generated by planex-init\n"
    autogen = "include %s/Makefile.rules\n" % (MAKEFILE_PATH)
    endline = "# End generated by planex-init\n"

    if not os.path.exists(name):
        logging.debug("Creating Makefile")
        with open(name, 'w') as makefile:
            for line in defaults:
                makefile.write(line)
            makefile.write(firstline)
            makefile.write(autogen)
            makefile.write(endline)
        return

    with open(name, 'r') as makefile:
        lines = makefile.readlines()

    try:
        start = lines.index(firstline)
        end = lines.index(endline)
        lines = lines[:start + 1] + [autogen] + lines[end:]

    except ValueError:
        logging.error("Couldn't find planex-init stanza in Makefile")

    with open(name, 'w') as makefile:
        makefile.writelines(lines)


def main():
    """
    Main entry point
    """
    setup_sigint_handler()
    logging.basicConfig(format='%(message)s', level=logging.ERROR)
    create_makefile()

if __name__ == "__main__":
    main()
