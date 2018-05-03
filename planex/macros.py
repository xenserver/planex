"""Classes for dealing with rpm macros."""
from __future__ import print_function

import contextlib

import rpm


@contextlib.contextmanager
def rpm_macros(*macros):
    """
    Context manager to add and remove stacked RPM macro 'environments'.
    Macro definitions which occur later in 'macros' override definitions
    made earlier.
    """
    for macro in macros:
        for key, value in macro.items():
            rpm.addMacro(key, value)
    yield
    for macro in reversed(macros):
        for key in macro.keys():
            rpm.delMacro(key)


def nevra(package):
    """
    Returns a dictionary of macro definitions for the Name, Epoch, Version,
    Release and Architecture of package.   This dictionary can be passed to
    rpm_macros() to set up an appropriate environment for macro expansion.
    """
    return {
        'name':    package['name'],
        'epoch':   str(package['epoch'] or 1),
        'version': package['version'],
        'release': package['release'],
        'arch':    package['arch']
    }


def expandmacros(func):
    """Decorator to expand RPM macros in strings"""

    def func_wrapper(self):
        """Decorator wrapper"""
        with rpm_macros(self.spec.macros, nevra(self.spec.spec.sourceHeader)):
            value = func(self)
            return rpm.expandMacro(value) if value is not None \
                else None
    return func_wrapper
