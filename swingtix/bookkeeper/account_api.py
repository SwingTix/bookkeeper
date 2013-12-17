"""

Provides logic for the backend model's functionality.

Models..

  * AccountBase -- see docstrings
  * BookSetBase
  * ProjectBase

ThirdParty must implement:

    get_account(self):
        " Return the parent 'account' (typically an AR or AP account, possibly tied to a project) that the third party is part of.  "

"""

from __future__ import unicode_literals
from collections import namedtuple
from decimal import Decimal
from django.db.models import Sum
from django.db import transaction

class LedgerEntry(object):
    """ A read-only AccountEntry representation.

    (replaces namedtuple('AccountEntryTuple', 'time description memo debit credit opening closing txid') )
     """

    def __init__(self, normalized_amount, ae, opening, closing):
        self._e = ae
        self._opening = opening
        self._closing = closing
        self._amount = normalized_amount

    def __str__(self):
        if self._amount > 0:
            return u"<ledger entry {0}Dr {1} {2}>".format(self.debit, self.time, self.description)
        else:
            return u"<ledger entry {0}Cr {1} {2}>".format(self.credit, self.time, self.description)

    @property
    def time(self):
        return self._e.transaction.t_stamp

    @property
    def description(self):
        return self._e.transaction.description

    @property
    def memo(self):
        return self._e.description

    @property
    def debit(self):
        if self._amount >= 0:
            return self._amount
        else:
            return None

    @property
    def credit(self): 
        if self._amount < 0:
            return -self._amount
        else:
            return None

    @property
    def opening(self):
        return self._opening

    @property
    def closing(self):
        return self._closing

    @property
    def txid(self):
        d = self._e.transaction.t_stamp.date()
        return "{:04d}{:02d}{:02d}{:08d}".format(d.year, d.month, d.day, self._e.aeid)

    def other_entry(self):
        """ Returns the account of the other leg of this transaction.  Asserts if there's more than two legs. """
        l = self.other_entries()
        assert len(l) == 1
        return l[0][1]

    def other_entries(self):
        """ Returns a list of tuples of the other entries for this transaction.

        Most transactions have only two pieces: a debit and a credit, so this function will
        return the "other half" in those cases with a single tuple in the list.  However, it's
        possible to have more, so long as the debits and credit sum to be equal.

        Each tuple has two values: the amount and the account.
        """

        l = []
        t = self._e.transaction
        for ae in t.entries.all():
            if ae != self._e:
                amount = ae.amount * ae.account._DEBIT_IN_DB()
                l.append( (amount, ae.account) )

        return l

class AccountBase(object):
    """ Implements a high-level account interface.

    Children must implement: _make_ae, _new_transaction, _entries,
    _positive_credit.  They may also wish to override _DEBIT_IN_DB.
    """

    def _make_ae(self, amount, memo, tx): # pragma: no coverage
        "Create an AccountEntry with the given data."
        raise NotImplementedError()

    def _new_transaction(self): # pragma: no coverage
        "Create a new transaction"
        raise NotImplementedError()

    def _entries(self): # pragma: no coverage
        "Return a queryset of the relevant AccountEntries."
        raise NotImplementedError()

    def _positive_credit(self): # pragma: no coverage
        "Does this account consider credit positive?  (Return False for Asset & Expense accounts, True for Liability, Revenue and Equity accounts.) "
        raise NotImplementedError()

    def get_bookset(self): # pragma: no coverage
        raise NotImplementedError()

    #If, by historical accident, debits are negative and credits are positive in the database, set this to -1.  By default
    #otherwise leave it as 1 as standard partice is to have debits positive.
    #(this variable is multipled against data before storage and after retrieval.)
    def _DEBIT_IN_DB(self):
        return 1

    def debit(self, amount, credit_account, description, debit_memo="", credit_memo="", datetime=None):
        """ Post a debit of 'amount' and a credit of -amount against this account and credit_account respectively.

        note amount must be non-negative.
        """

        assert amount >= 0
        return self.post(amount, credit_account, description, self_memo=debit_memo, other_memo=credit_memo, datetime=datetime)
    def credit(self, amount, debit_account, description, debit_memo="", credit_memo="", datetime=None):
        """ Post a credit of 'amount' and a debit of -amount against this account and credit_account respectively.

        note amount must be non-negative.
        """
        assert amount >= 0
        return self.post(-amount, debit_account, description, self_memo=credit_memo, other_memo=debit_memo, datetime=datetime)

    @transaction.commit_on_success
    def post(self, amount, other_account, description, self_memo="", other_memo="", datetime=None):
        """ Post a transaction of 'amount' against this account and the negative amount against 'other_account'.

        This will show as a debit or credit against this account when amount > 0 or amount < 0 respectively.
        """

        #Note: debits are always positive, credits are always negative.  They should be negated before displaying
        #(expense and liability?) accounts
        tx = self._new_transaction()

        if datetime:
            tx.t_stamp = datetime
        #else now()

        tx.description = description
        tx.save()

        a1 = self._make_ae(self._DEBIT_IN_DB()*amount, self_memo, tx)
        a1.save()
        a2 = other_account._make_ae(-self._DEBIT_IN_DB()*amount, other_memo, tx)
        a2.save()

        return (a1,a2)

    def balance(self, date=None):
        """ returns the account balance as of 'date' (datetime stamp) or now().  """

        qs = self._entries()
        if date:
            qs = qs.filter(transaction__t_stamp__lt=date)
        r = qs.aggregate(b=Sum('amount'))
        b = r['b']

        flip = self._DEBIT_IN_DB()
        if self._positive_credit():
            flip *= -1

        if b == None:
            b = Decimal("0.00")
        b *= flip

        #print "returning balance %s for %s" % (b, self)
        return b

    def ledger(self, start=None, end=None):
        """Returns a list of entries for this account.

        Ledger returns a sequence of LedgerEntry's matching the criteria
        in chronological order. The returned sequence can be boolean-tested
        (ie. test that nothing was returned).

        If 'start' is given, only entries on or after that datetime are
        returned.  'start' must be given with a timezone.

        If 'end' is given, only entries before that datetime are
        returned.  'end' must be given with a timezone.
        """

        DEBIT_IN_DB = self._DEBIT_IN_DB()

        flip = 1
        if self._positive_credit():
            flip *= -1

        qs = self._entries()
        balance = Decimal("0.00")
        if start:
            balance = self.balance(start)
            qs = qs.filter(transaction__t_stamp__gte=start)
        if end:
            qs = qs.filter(transaction__t_stamp__lt=end)
        qs = qs.order_by("transaction__t_stamp", "transaction__tid")

        if not qs:
            return []

        #helper is a hack so the caller can test for no entries.
        def helper(balance_in):
            balance = balance_in
            for e in qs.all():
                amount = e.amount*DEBIT_IN_DB
                o_balance = balance
                balance += flip*amount

                yield LedgerEntry(amount, e, o_balance, balance)

        return helper(balance)

class ThirdPartySubAccount(AccountBase):
    """ A proxy account that behaves like a third party account. It passes most
    of its responsibilities to a parent account.
    """

    def __init__(self, parent, third_party):
        self._third_party = third_party
        self._parent = parent

    def get_bookset(self):
        return self._parent.get_bookset()

    def _make_ae(self, amount, memo, tx):
        ae = self._parent._make_ae(amount, memo, tx)
        if self._third_party:
            self._third_party._associate_entry(ae)
        return ae

    def _new_transaction(self):
        tx = self._parent._new_transaction()
        return tx

    def _entries(self):
        qs = self._parent._entries()
        if self._third_party:
            qs = self._third_party._filter_third_party(qs)

        return qs

    def _positive_credit(self):
        return self._parent._positive_credit()

    def _DEBIT_IN_DB(self): 
        return self._parent._DEBIT_IN_DB()

    def __str__(self):
        return """<ThirdPartySubAccount for tp {0}>""".format(self._third_party)

class ProjectAccount(ThirdPartySubAccount):
    """ A proxy account that behaves like its parent account except isolates transactions for
    to a project.  It passes most of its responsibilities to a parent account.
    """

    def __init__(self, parent, project, third_party=None):
        super(ProjectAccount, self).__init__(parent, third_party)
        self._project = project

    def get_bookset(self):
        return self._project.get_bookset()

    def _new_transaction(self):
        tx = super(ProjectAccount, self)._new_transaction()
        if self._project:
            self._project._associate_transaction(tx)
        return tx

    def _entries(self):
        qs = super(ProjectAccount, self)._entries()
        if self._project:
            qs=self._project._filter_project_qs(qs)

        return qs

    def __str__(self):
        return """<ProjectAccount for bookset {0} tp {1}>""".format(self.get_bookset(), self._third_party)

class BookSetBase(object):
    """ Base account for BookSet-like-things, such as BookSets and Projects.

    children must implement accounts()
    """

    def accounts(self): # pragma: no coverage
        """Returns a sequence of account objects belonging to this bookset."""
        raise NotImplementedError()

    def get_third_party(self, third_party):
        """Return the account for the given third-party.  Raise <something> if the third party doesn't belong to this bookset."""
        actual_account = third_party.get_account()
        assert actual_account.get_bookset() == self
        return ThirdPartySubAccount(actual_account, third_party=third_party)

class ProjectBase(BookSetBase):
    """ Base account for Projects.

    Children must implement: get_bookset() and accounts()
    """

    def get_bookset(self): # pragma: no coverage
        """Returns the the parent (main) bookset """
        raise NotImplementedError()


    def get_account(self, name):
        actual_account = self.get_bookset().get_account(name)
        return ProjectAccount(actual_account, project=self)

    def get_third_party(self, third_party):
        """Return the account for the given third-party.  Raise <something> if the third party doesn't belong to this bookset."""
        actual_account = third_party.get_account()

        assert actual_account.get_bookset() == self.get_bookset()
        return ProjectAccount(actual_account, project=self, third_party=third_party)

