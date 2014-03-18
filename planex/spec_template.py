from planex import exceptions


class SpecTemplate(object):
    def __init__(self, path, filesystem, rpm_adapter):
        self.rpm_adapter = rpm_adapter
        self.filesystem = filesystem
        self.path = path

    @property
    def name(self):
        return self.rpm_adapter.get_name(self.path, self.filesystem)

    @property
    def main_source(self):
        return self.rpm_adapter.get_main_source(self.path, self.filesystem)


def template_from_file(path, filesystem, rpm_adapter):
    if not filesystem.isfile(path):
        raise exceptions.NoSuchFile()

    return SpecTemplate(path, filesystem, rpm_adapter)


def templates_from_dir(filesystem, rpm_adapter):
    templates = []
    for fname in filesystem.listdir(wildcard="*.spec.in"):
        templates.append(template_from_file(fname, filesystem, rpm_adapter))
    return templates
