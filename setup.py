# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

__author__ = 'Eric Pascual - CSTB (eric.pascual@cstb.fr)'

setup(
    name="cstbox-devtools",
    description='CSTBox development tools',
    author='Eric Pascual (CSTB)',
    author_email='eric.pascual@cstb.fr',
    use_scm_version={
        'version_scheme': 'post-release'
    },
    setup_requires=['setuptools_scm'],
    packages=find_packages('src'),
    package_dir={'': 'src'},
)
