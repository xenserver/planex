import os.path

BUILD_ROOT_DIR = "planex-build-root"

[SPECS_DIR, SOURCES_DIR, SRPMS_DIR, RPMS_DIR, BUILD_DIR, MOCK_DIR] = [
    os.path.join(BUILD_ROOT_DIR, dir_name) for dir_name in
    ['SPECS', 'SOURCES', 'SRPMS', 'RPMS', 'BUILD', 'mock']]

SPECS_GLOB = os.path.join(SPECS_DIR, "*.spec")

HASHFN = "md5"
