from __future__ import unicode_literals
from collections import namedtuple
from decimal import Decimal
from django.db.models import Sum
from django.db import transaction

AccountEntryTuple = namedtuple('AccountEntryTuple', 'time description memo debit credit opening closing txid')

class AccountBase(object):
    """ Implements a high-level account interface.

    Children must implement: _make_ae, _new_transaction, _entries,
    _positive_credit.  They may also wish to override _DEBIT_IN_DB.
    """

    def _make_ae(self, amount, memo, tx):
        "Create an AccountEntry with the given data."
        raise NotImplementedError()

    def _new_transaction(self):
        "Create a new transaction"
        raise NotImplementedError()

    def _entries(self):
        "Return a queryset of the relevant AccountEntries."
        raise NotImplementedError()

    def _positive_credit(self):
        "Does this account consider credit positive?  (Return False for Asset & Expense accounts, True for Liability, Revenue and Equity accounts.) "
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

        Ledger returns a sequence of AccountEntryTuple's matching the criteria
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
                if amount < 0:
                    debit = None
                    credit = -amount
                else:
                    debit = amount
                    credit = None

                o_balance = balance
                balance += flip*amount

                d = e.transaction.t_stamp.date()
                txid = "{:04d}{:02d}{:02d}{:08d}".format(d.year, d.month, d.day, e.aeid)
                    
                yield AccountEntryTuple(
                    time=e.transaction.t_stamp,
                    description=e.transaction.description,
                    memo=e.description,
                    debit=debit,
                    credit=credit,
                    opening=o_balance,
                    closing=balance,
                    txid=txid
                    )
        return helper(balance)

class ThirdPartySubAccount(AccountBase):
    """ A proxy account that behaves like a third party account. It passes most
    of its responsibilities to a parent account.
    """

    def __init__(self, parent, third_party):
        self._third_party = third_party
        self._parent = parent

    def _make_ae(self, amount, memo, tx):
        ae = self._parent._make_ae(amount, memo, tx)
        if self._third_party:
            ae.third_party = self._third_party
        return ae

    def _new_transaction(self):
        tx = self._parent._new_transaction()
        return tx

    def _entries(self):
        qs = self._parent._entries()
        if self._third_party:
            qs = qs.filter(third_party=self._third_party)

        return qs

    def _positive_credit(self):
        return self._parent._positive_credit()

    def _DEBIT_IN_DB(self): 
        return self._parent._DEBIT_IN_DB()


class ProjectAccount(ThirdPartySubAccount):
    """ A proxy account that behaves like its parent account except isolates transactions for
    to a project.  It passes most of its responsibilities to a parent account.
    """

    def __init__(self, parent, project, third_party=None):
        super(ProjectAccount, self).__init__(parent, third_party)
        self._project = project


    def _new_transaction(self):
        tx = super(ProjectAccount, self)._new_transaction()
        tx.project = self._project
        return tx

    def _entries(self):
        qs = super(ProjectAccount, self)._entries()
        qs = qs.filter(transaction__project=self._project)

        return qs

class BookSetBase(object):
    """ Base account for BookSet-like-things, such as BookSets and Projects. """

    def accounts(self):
        """Returns a sequence of account objects belonging to this bookset."""
        raise NotImplementedError()
        #return self.accounts.get(name=name)

    def get_third_party(self, third_party):
        """Return the account for the given third-party.  Raise <something> if the third party doesn't belong to this bookset."""
        actual_account = third_party.account
        assert actual_account.bookset == self
        return ThirdPartySubAccount(actual_account, third_party=third_party)

class ProjectBase(BookSetBase):
    """ Base account for Projects.

        Required: self.bookset -- the parent (main) bookset
    """

    def get_account(self, name):
        actual_account = self.bookset.get_account(name)
        return ProjectAccount(actual_account, project=self)

    def get_third_party(self, third_party):
        """Return the account for the given third-party.  Raise <something> if the third party doesn't belong to this bookset."""
        actual_account = third_party.account
        assert actual_account.bookset == self.bookset
        return ProjectAccount(actual_account, project=self, third_party=third_party)

