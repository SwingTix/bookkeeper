import datetime
from django.db import models
from swingtix.bookkeeper.account_api import AccountBase

class _AccountApi(AccountBase):
    def _new_transaction(self):
        return Transaction()

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

class Account(models.Model, _AccountApi):
    """ A financial account in a double-entry bookkeeping bookset.

    for example:
        Assets::chequing
        Expensses::bankfees
    """
    accid = models.AutoField(primary_key=True)
    book = models.ForeignKey(BookSet, db_column='org', related_name='accounts')

    positive_credit = models.BooleanField("""credit entries increase the value of this account.  Set to False for Asset & Expense accounts, True for Liability, Revenue and Equity accounts.""")

    name = models.TextField() #slugish?  Unique?
    description = models.TextField(blank=True)

    #parent account?
    #annotations for registration: receivables, revenue.. etc

    #needed by _AccountApi
    def _make_ae(self, amount, memo, tx):
        ae = AccountEntry()
        ae.account = self
        ae.transaction = tx
        ae.amount = amount
        ae.description = memo
        return ae
    def _entries(self): return self.entries
    def _positive_credit(self): return self.positive_credit

    def __unicode__(self):
        return '%s %s' % (self.organization.name, self.name)

class ThirdParty(models.Model, _AccountApi):
    """Represents an account with another party.  (eg. Account Receivable, or Account Payable.) """
    id = models.AutoField(primary_key=True)

    name = models.TextField("name memo", help_text="this field is only used for displaying information during debugging.  It's best to use a OneToOne relationship with another tabel to hold all the information you actually need.")

    account = models.ForeignKey(Account, related_name="third_parties")

    #needed by _AccountApi
    def _make_ae(self, amount, memo, tx):
        """ Makes an AccountEntry for this account with the given amount, memo and tx set.  Does not save it. """

        ae = AccountEntry()
        ae.account = self.account
        ae.third_party = self
        ae.transaction = tx
        ae.amount = amount
        ae.description = memo
        return ae

    def _entries(self): return AccountEntry.objects.filter(third_party=self)
    def _positive_credit(self): return self.account.positive_credit

    def __unicode__(self):
        return '<ThirdParty %s %s>' % (self.name, self.id)
 
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

