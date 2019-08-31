from setuptools import setup

setup(name='edl2aaf',
      version='0.1',
      packages=['edl2aaf'],
      entry_points={
          'console_scripts': [
              'edl2aaf = edl2aaf.command:do_command'
          ]
      }
      )