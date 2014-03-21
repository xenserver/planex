import re


SOURCE_RE = re.compile(r'''
    ^
    Source(?P<source_number>\d+)
    :
    (?P<source>.*)
    $
''', re.VERBOSE)


class SimpleRPM(object):
    def get_name(self, path, filesystem):
        for line in filesystem.getcontents(path).split('\n'):
            if line.startswith('Name:'):
                return line.split(':')[1].strip()

    def get_main_source(self, path, filesystem):
        for line in filesystem.getcontents(path).split('\n'):
            if line.startswith('Source0:'):
                return line.split('Source0:')[1].strip()

    def get_sources(self, path, filesystem):
        results = []
        for line in filesystem.getcontents(path).split('\n'):
            match = SOURCE_RE.match(line)
            if match:
                results.append(
                    (
                        int(match.group('source_number')),
                        match.group('source').strip()
                    )
                )
        return [source for (_, source) in sorted(results)]
