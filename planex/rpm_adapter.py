import re
import StringIO
import tempfile
import logging

from planex import spec


log = logging.getLogger(__name__)


SOURCE_RE = re.compile(r'''
    ^
    Source(?P<source_number>\d*)
    :
    (?P<source>.*)
    $
''', re.VERBOSE)


class SimpleRPM(object):
    def get_sources(self, path, filesystem):
        results = []
        for line in filesystem.getcontents(path).split('\n'):
            match = SOURCE_RE.match(line)
            if match:
                results.append(
                    (
                        int(match.group('source_number') or '0'),
                        match.group('source').strip()
                    )
                )
        return [source for (_, source) in sorted(results)]


class RPMLibraryAdapter(object):
    def get_sources(self, path, filesystem):
        contents = filesystem.getcontents(path)
        REPLACEMENTS = [
            ('@VERSION@', 'UNRELEASED'),
            ('BuildRequires(pre)', 'BuildRequires'),
        ]

        for src, tgt in REPLACEMENTS:
            contents = contents.replace(src, tgt)

        log.info('Getting sources for %s', filesystem.getsyspath(path))
        with tempfile.NamedTemporaryFile() as temporary_specfile:
            temporary_specfile.write(contents)
            temporary_specfile.flush()
            spec_ = spec.Spec(temporary_specfile.name, check_filename=False)

        return spec_.source_urls()
