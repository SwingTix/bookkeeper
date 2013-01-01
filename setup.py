# -*- coding: utf-8 -*-
from distutils.core import setup
from setuptools import find_packages

setup(
    name='swingtix/bookkeeper',
    version='0.0.0',
    author=u'Geoff Oakham',
    author_email=u'geoff.oakham@swingtix.ca',
    packages=find_packages(),
    url='https://github.com/swingtix',
    license='GNU Affero General Public License, version 1, see LICENSE',
    description='A double-entry bookkeeping module for django',
    long_description=open('README').read(),
    zip_safe=False,
    include_package_data=True,
)




