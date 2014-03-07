class Fake(object):
    def __init__(self):
        self.contents = {}

    def join(self, *path_elements):
        return '/'.join(path_elements)

    def directory_exists(self, path):
        return path in self.contents and self.contents[path] == 'DIRECTORY'

    def file_exists(self, *path_elements):
        path = self.join(*path_elements)
        return path in self.contents and self.contents[path] != 'DIRECTORY'

    def contents_of(self, *path_elements):
        assert self.file_exists(*path_elements)
        return self.contents[self.join(*path_elements)].read()
