from django.db import models
from django.db.models import Sum

from decimal import Decimal
import datetime

from collections import namedtuple

AccountEntryTuple = namedtuple('AccountEntryTuple', 'time description memo credit debit opening closing')

class BookSet(models.Model):
    """A set of accounts for an organization.  On desktop accounting software, one BookSet row would typically represent one saved file.
    For example, you might have one BookSet for each country a corportation operates in.
    """

    id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=80)

    def load_account(self, name):
        return self.accounts.get(name=name)

    def __unicode__(self):
        return self.description

class ThirdParty(models.Model):
    """Not yet complete.. """
    id = models.AutoField(primary_key=True)

    name = models.TextField()
    def __unicode__(self):
        return '<ThirdParty orm %s %s>' % (self.name, self.id)
 
class Account(models.Model):
    """ A financial account in a double-entry bookkeeping bookset.

    for example:
        Assets::chequing
        Expensses::bankfees
    """
    accid = models.AutoField(primary_key=True)
    book = models.ForeignKey(BookSet, db_column='org', related_name='accounts')
    creditordebit = models.BooleanField("""False for Asset & Expense accounts, True for Liability, Revenue and Equity accounts.
        Accounts with 'creditordebit' set to True which increase with credit and decrease with debit.""")

    name = models.TextField() #slugish?  Unique?
    description = models.TextField(blank=True)

    #parent account?
    #annotations for registration: receivables, revenue.. etc

    def __unicode__(self):
        return '%s %s' % (self.organization.name, self.name)

    #If, by historical accident, debits are negative and credits are positive in the database, set this to -1.  By default
    #otherwise leave it as 1 as standard partice is to have debits positive.
    #(this variable is multipled against data before storage and after retrieval.)
    _DEBIT_IN_DB = 1

    @staticmethod
    def _db_to_debit_and_credit(amount):
        amount *= Account._DEBIT_IN_DB
        if amount < 0:
            #credit
            return (None, -amount)
        elif amount > 0:
            #debit
            return (amount, None)
        else:
            return (None, None)


    #TODO: check how debit and credit affects positive and negative values of account entries, or if it's just displaying
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

    def post(self, amount, other_account, description, self_memo="", other_memo="", project=None, datetime=None):
        """ Post a transaction of 'amount' against this account and the negative amount against 'other_account'.

        This will show as a debit or credit against this account when amount > 0 or amount < 0 respectively.
        """

        #Note: debits are always positive, credits are always negative.  They should be negated before displaying
        #(expense and liability?) accounts
        tx = Transaction()
        if project:
            tx.project = project
        else:
            tx.project = 0

        if datetime:
            tx.t_stamp = datetime
        #else now()

        tx.description = description
        tx.save()

        a1 = self._make_ae(Account._DEBIT_IN_DB*amount, self_memo, tx)
        a1.save()
        a2 = other_account._make_ae(-Account._DEBIT_IN_DB*amount, other_memo, tx)
        a2.save()

        return (a1,a2)

    def _make_ae(self, amount, memo, tx):
        """ Makes an AccountEntry for this account with the given amount, memo and tx set.  Does not save it. """

        ae = AccountEntry()
        ae.account = self
        #ae.third_party = third_party
        ae.transaction = tx
        ae.amount = amount
        ae.description = memo
        return ae

    def balance(self, date=None):
        """ returns the account balance as of 'date' (datetime stamp) or now().  """

        qs = self.entries
        if date:
            qs = qs.filter(transaction__t_stamp__lt=date)
        r = qs.aggregate(b=Sum('amount'))
        b = r['b']

        flip = Account._DEBIT_IN_DB 
        if self.creditordebit:
            flip *= -1

        if b == None:
            b = Decimal("0.00")
        b *= flip

        #print "returning balance %s for %s" % (b, self)
        return b

    def ledger(self, start=None, end=None):
        flip = Account._DEBIT_IN_DB 
        if self.creditordebit:
            flip *= -1

        qs = self.entries
        balance = Decimal("0.00")
        if start:
            balance = self.balance(start)
            qs = qs.filter(transaction__t_stamp__gte=start)
        if end:
            qs = qs.filter(transaction__t_stamp__lt=end)

        for e in qs.order_by("transaction__t_stamp", "transaction__tid").all():
            if e.amount < 0:
                debit = None
                credit = -e.amount
            else:
                debit = e.amount
                credit = None

            o_balance = balance
            balance += flip*e.amount
                
            yield AccountEntryTuple(e.transaction.t_stamp, e.transaction.description, e.description,
                debit, credit, o_balance, balance)

class Transaction(models.Model):
    """ A transaction is a collection of AccountEntry rows (for different accounts) that sum to zero.

    The most common transaction is a Debit (positive change) from one account and a Credit (negative change)
    in another account.  Transactions involving more than two accounts are called "split transactions".
    """

    tid = models.AutoField(primary_key=True)

    t_stamp = models.DateTimeField(default=datetime.datetime.now)
    description = models.TextField()

    #TODO: add projectcodes and other annotations

    #Invarients:
    #   all entries involve accounts from the same organization
    #   sum (entires.amount) = 0, for each transaction

    def __unicode__(self):
        return self.description

#questionable use of natural_keys?
class AccountEntryManager(models.Manager):
    def get_by_natural_key(self, account,transaction):
        return self.get(account=account, transaction=transaction)

class AccountEntry(models.Model):
    """A change in an account.

    By convention, positive changes are known as "debits" while negative changes are "credits".
    """

    class Meta:
        unique_together= (('account', 'transaction'),)
    def natural_key(self):
        return (self.transaction.pk,) + self.account.natural_key()
    objects = AccountEntryManager()

    aeid = models.AutoField(primary_key=True)

    transaction = models.ForeignKey(Transaction, db_column='tid',related_name='entries')
    account = models.ForeignKey(Account, db_column='accid', related_name='entries')

    amount = models.DecimalField(max_digits=8,decimal_places=2) #numeric(8,2)
    description = models.TextField()

    third_party = models.ForeignKey(ThirdParty, related_name='account_entries', null=True)

    def __unicode__(self):
        base =  "%d %s" % (self.amount, self.description)

        return base


