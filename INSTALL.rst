INSTALLATION
============


Install
-------

from tarball/git::

    $ tar -xzf swingtix-bookkeeper.tar.gz
    $ cd swingtix-bookkeeper
    $ python ./setup.py install

from pip::

    $ pip install swingtix-bookkeeper

Configure
---------

    1) in your project's ``settings.py``, add "swingtix.bookkeeper" to ``INSTALLED_APPS``
    2) run ``./manage.py syncdb``


