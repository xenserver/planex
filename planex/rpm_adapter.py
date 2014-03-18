class SimpleRPM(object):
    def get_name(self, path, filesystem):
        for line in filesystem.getcontents(path).split('\n'):
            if line.startswith('Name:'):
                return line.split(':')[1].strip()

    def get_main_source(self, path, filesystem):
        for line in filesystem.getcontents(path).split('\n'):
            if line.startswith('Source0:'):
                return line.split('Source0:')[1].strip()
