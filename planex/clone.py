import argparse
import sys
import logging
import glob
import planex.spec
import os

from planex import sources
from planex import executors
from planex import util


log = logging.getLogger(__name__)


def parse_args_or_exit(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_dir', help='Configuration directory',
	default=".")
    parser.add_argument(
        '--print-only', help='Only print sources, do not clone them',
        action='store_true')
    parser.add_argument(
        '--dry-run', help='Do not execute commands, just print them',
        action='store_true')
    parser.add_argument(
        '--quiet', help='Do not print warnings',
        action='store_true')
    parser.add_argument(
        '--repos_mirror_path', help='Path to a local repository mirror directory. '
        'This should be a file path where for a git url '
        '"git://host.com/some/path.git" the mirror '
        'should contain <mirror_path>/host.com/some/path.git', 
        default="")
    parser.add_argument(
        '--repos_path', help='Local path under which the repositories should be '
        'checked out',
        default="repos")
    parser.add_argument(
        '--specs_path', help='Path (relative to config_dir) to the SPECS directory containing spec '
        'files to be preprocessed as well as those simply to be built.',
        default="SPECS")
    return parser.parse_args(argv)


def main():
    config = parse_args_or_exit()

    logging.basicConfig(level=logging.ERROR if config.quiet else logging.DEBUG)

    templates = [planex.spec.Spec(path) 
                 for path in glob.glob(os.path.join(config.config_dir, config.specs_path, "*.spec.in"))]

    if config.print_only:
        for template in templates:
            print template.source_urls()
        sys.exit(0)

    if config.dry_run:
        executor = executors.PrintExecutor(sys.stdout)
    else:
        executor = executors.RealExecutor()

    for template in templates:
        srcs = [sources.Source(url,config) for url in template.source_urls()]

        commands_list = [src.clone_commands() for src in srcs]

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
