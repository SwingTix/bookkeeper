SwingTix Bookkeeper
===================

A `double-entry bookkeeping <http://en.wikipedia.org/wiki/Double-entry_bookkeeping_system>`_ system originally developed for `SwingTix <https://swingtix.ca>`_.

Hello, World
------------

You'll need a django project.  If you don't have one handy, you can make an empty one following
the first steps of the `django tutorial <https://docs.djangoproject.com/en/1.6/>`_.  Afterwards,
edit <yourproject>/settings.py to add "swingtix.bookkeeper" to INSTALLED_APPS and run:: 

    $ python manage.py syncdb 

Then you're ready to start exploring using the shell::

    $ python manage.py shell

First, let's create a couple of accounts:: 

    >>> from swingtix.bookkeeper.models import BookSet, Account

    >>> book = BookSet(description="my book")
    >>> book.save()

    >>> revenue  = Account(bookset=book, name="revenue", positive_credit=True)
    >>> revenue.save()
    >>> bank     = Account(bookset=book, name="bank",    positive_credit=False)
    >>> bank.save()
    >>> expense  = Account(bookset=book, name="expense", positive_credit=False)
    >>> expense.save()

Then you can use them::

    >>> book = BookSet.objects.get(description="my book")
    >>> revenue = book.get_account("revenue")
    >>> bank    = book.get_account("bank")
    >>> expense = book.get_account("expense")

    #Someone pays you can advance.  Yay!
    >>> bank.debit(120.00, revenue, "our first sale")
    (<AccountEntry: 120 >, <AccountEntry: -120 >)

    #but now you have to do some work.  The local coffee shop has free wifi..
    >>> bank.credit(2.20, expense, "coffee")
    (<AccountEntry: -2 >, <AccountEntry: 2 >)

    >>> bank.balance()
    Decimal('117.80')
    >>> expense.balance()
    Decimal('2.20')
    >>> revenue.balance()
    Decimal('120.00')


