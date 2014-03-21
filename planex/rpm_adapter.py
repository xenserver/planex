import re


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
