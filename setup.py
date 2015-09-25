__author__ = 'Konstantin Weddige'
from setuptools import setup, find_packages


setup(
    name='k-center',
    version='0.1',
    author='Konstantin Weddige',
    packages=find_packages('src'),
    package_dir={'': 'src'}
)