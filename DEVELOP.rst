Developing Bookkeeper
=====================

Recommended development environment
-----------------------------------

The minimal virtualenv needed::

    $ cd <DEV HOME>
    $ virtualenv --no-site-packages py_env
    $ . py_env/bin/activate
    $ pip install -U django==1.6.1 pytz coverage

(replace the django version with the one of your choice.)

At least one DB module will be needed::

    $ pip install psycopg2 db-sqlite3

clone and run the unittests
---------------------------

from gitthub::

    $ git clone https://github.com/SwingTix/bookkeeper.git 
    $ cd bookkeeper
    $ ./manage.py test swingtix.bookkeeper
    $ coverage run --source="swingtix" ./manage.py test swingtix.bookkeeper
    $ coverage report

make changes, and repeat the tests

(Note: with django 1.5 and earlier, replace ``./manage.py test swingtix.bookkeeper`` with ``./manage.py test bookkeeper``)


