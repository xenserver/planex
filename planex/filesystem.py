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


class LocalFileSystem(object):
    def __init__(self):
        import os
        self.os = os
        self.join = os.path.join

    def contents_of(self, *path_elements):
        with open(self.join(*path_elements), 'rb') as fhandle:
            return fhandle.read()

    def directory_exists(self, path):
        return self.os.path.exists(path) and self.os.path.isdir(path)

    def file_exists(self, *path_elements):
        return self.os.path.exists(self.join(*path_elements))
