from distutils.core import setup

setup(name='planex',
      version='0.0.0',
      py_modules=['demjson', 'planex_globals'],
      scripts=['planex-configure', 'planex-build', 'planex-install',
               'spectool']
      )
