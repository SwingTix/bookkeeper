from collections import namedtuple
from decimal import Decimal
from django.db.models import Sum
from django.db import transaction

AccountEntryTuple = namedtuple('AccountEntryTuple', 'time description memo credit debit opening closing txid')

class AccountBase(object):
    """ Implements a high-level account interface.

    Children must implement:
        def _make_ae(self, amount, memo, tx):
            "Create an AccountEntry with the given data."

        def _entries(self):
            "Return a queryset of the relevant AccountEntries."

        def _positive_credit(self):
            "Does this account consider credit positive?  (Return False for Asset & Expense accounts, True for Liability, Revenue and Equity accounts.) "

        def _DEBIT_IN_DB(self):
            return 1
    """

    #If, by historical accident, debits are negative and credits are positive in the database, set this to -1.  By default
    #otherwise leave it as 1 as standard partice is to have debits positive.
    #(this variable is multipled against data before storage and after retrieval.)
    def _DEBIT_IN_DB(self):
        return 1

    def debit(self, amount, credit_account, description, debit_memo="", credit_memo="", project=None,datetime=None):
        """ Post a debit of 'amount' and a credit of -amount against this account and credit_account respectively.

        note amount must be non-negative.
        """

        assert amount >= 0
        return self.post(amount, credit_account, description, self_memo=debit_memo, other_memo=credit_memo, project=project, datetime=datetime)
    def credit(self, amount, debit_account, description, debit_memo="", credit_memo="", project=None, datetime=None):
        """ Post a credit of 'amount' and a debit of -amount against this account and credit_account respectively.

        note amount must be non-negative.
        """
        assert amount >= 0
        return self.post(-amount, debit_account, description, self_memo=credit_memo, other_memo=debit_memo, project=project, datetime=datetime)

    def _new_transaction():
        assert False, "not implemented"

    @transaction.commit_on_success
    def post(self, amount, other_account, description, self_memo="", other_memo="", project=None, datetime=None):
        """ Post a transaction of 'amount' against this account and the negative amount against 'other_account'.

        This will show as a debit or credit against this account when amount > 0 or amount < 0 respectively.
        """

        #Note: debits are always positive, credits are always negative.  They should be negated before displaying
        #(expense and liability?) accounts
        tx = self._new_transaction()
        if project:
            tx.project = project
        else:
            tx.project = 0

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
        flip = self._DEBIT_IN_DB()
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
                if e.amount < 0:
                    debit = None
                    credit = -e.amount
                else:
                    debit = e.amount
                    credit = None

                o_balance = balance
                balance += flip*e.amount

                d = e.transaction.t_stamp.date()
                txid = "{:04d}{:02d}{:02d}{:08d}".format(d.year, d.month, d.day, e.aeid)
                    
                yield AccountEntryTuple(e.transaction.t_stamp, e.transaction.description, e.description,
                    debit, credit, o_balance, balance, txid)
        return helper(balance)

