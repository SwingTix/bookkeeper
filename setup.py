# -*- coding: utf-8 -*-
from distutils.core import setup
from setuptools import find_packages

from swingtix import bookkeeper

setup(
    name='swingtix-bookkeeper',
    version=bookkeeper.__VERSION__,
    author=u'Geoff Oakham',
    author_email=u'geoff.oakham@swingtix.ca',
    packages=find_packages(),
    url='https://github.com/swingtix/bookkeeper',
    license='GNU Affero General Public License, version 3, see LICENSE',
    description='A double-entry bookkeeping module for django',
    long_description=open('README.rst').read(),
    zip_safe=False,
    include_package_data=True,
    tests_require=[
        'django>=1.5,<1.7',
    ],
   classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Framework :: Django',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Office/Business :: Financial :: Accounting',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)




