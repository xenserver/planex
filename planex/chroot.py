"""
planex-chroot: Start a docker container for developer builds of
packages.
"""

import argparse
import sys

import argcomplete

import planex
import planex.spec
import planex.util


def start_container(args):
    """
    Start the docker container with the source directories availble.
    """
    path_maps = []

    for package in args.package:
        # Assuming an unpinned .spec file for now.
        spec = planex.spec.Spec("SPECS/%s.spec" % (package))
        path_maps.append(("myrepos/%s" % (spec.name()),
                          "/build/rpmbuild/BUILD/%s-%s"
                          % (spec.name(), spec.version())))

    planex.util.start_container(path_maps, ("bash",))


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description="""
    Start a docker container for developer builds of packages.
    """)
    planex.util.add_common_parser_options(parser)
    parser.add_argument("package", nargs="+",
                        help="source to include in container")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv):
    """
    Entry point
    """
    planex.util.setup_sigint_handler()
    args = parse_args_or_exit(argv)
    start_container(args)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
