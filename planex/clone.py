import argparse
import sys
import logging
import glob
import planex.spec
import os

from planex import sources
from planex import executors


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

    templates = [planex.spec.Spec(path) 
                 for path in glob.glob(os.path.join(args.config_dir, "*.spec.in"))]

    if args.print_only:
        for template in templates:
            print template.source_urls()
        sys.exit(0)

    if args.dry_run:
        executor = executors.PrintExecutor(sys.stdout)
    else:
        executor = executors.RealExecutor()

    for template in templates:
        srcs = [sources.Source(url) for url in template.source_urls()]

        commands_list = [src.clone_commands(args.target_dir) for src in srcs]

        log.info(commands_list)
        results_list = [[executor.run(command) for command in commands] for commands in commands_list]

        for results in results_list:
            for result in results:
                if result.return_code != 0:
                    log.warning("FAILED: %s", commands)
                if result.stdout:
                    log.warning("STDOUT: %s", result.stdout)
                if result.stderr:
                    log.warning("STDERR: %s", result.stderr)
