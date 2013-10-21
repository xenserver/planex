import os.path

BUILD_ROOT_DIR = "planex-build-root"

[SPECS_DIR, SOURCES_DIR, SRPMS_DIR, RPMS_DIR, BUILD_DIR] = map(
    lambda x: os.path.join(BUILD_ROOT_DIR, x),
    ['SPECS', 'SOURCES', 'SRPMS', 'RPMS', 'BUILD'])

SPECS_GLOB = os.path.join(SPECS_DIR, "*.spec")
