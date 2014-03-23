import argparse
import sys
import logging

from fs.opener import fsopendir
from planex import spec_template
from planex import rpm_adapter
from planex import sources
from planex import executors
from planex import exceptions


log = logging.getLogger(__name__)


def parse_args_or_exit(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('config_dir', help='Configuration directory')
    parser.add_argument('target_dir', help='Target directory')
    parser.add_argument(
        '--print-only', help='Only print sources, do not clone them',
        action='store_true')
    parser.add_argument(
        '--dry-run', help='Do not execute commands, just print them',
        action='store_true')
    parser.add_argument(
        '--quiet', help='Do not print warnings',
        action='store_true')
    return parser.parse_args(argv)


def main():
    args = parse_args_or_exit()

    logging.basicConfig(level=logging.ERROR if args.quiet else logging.DEBUG)

    rpm_lib = rpm_adapter.RPMLibraryAdapter()

    templates = spec_template.templates_from_dir(
        fsopendir(args.config_dir),
        rpm_lib,
        '*.spec.in')

    srcs = []

    for template in templates:
        for source_url in template.sources:
            try:
                source = sources.GitSource(source_url)
                srcs.append(source)
            except exceptions.InvalidURL:
                log.info('%s not recognised', source_url)

    if args.print_only:
        for source in srcs:
            print source.repo_url
        sys.exit(0)

    target_dir = fsopendir(args.target_dir)

    if args.dry_run:
        executor = executors.PrintExecutor(sys.stdout)
    else:
        executor = executors.RealExecutor()

    for source in srcs:
        commands = source.clone_commands(target_dir)
        log.info(commands)
        result = executor.run(commands)

        if result.return_code != 0:
            log.warning("FAILED: %s", commands)
        if result.stdout:
            log.warning("STDOUT: %s", result.stdout)
        if result.stderr:
            log.warning("STDERR: %s", result.stderr)
