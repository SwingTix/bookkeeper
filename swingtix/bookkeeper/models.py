from __future__ import unicode_literals
from django.utils import timezone
from django.db import models
from .account_api import AccountBase, BookSetBase, ProjectBase

class _AccountApi(AccountBase):
    def _new_transaction(self):
        return Transaction()

class BookSet(models.Model, BookSetBase):
    """A set of accounts for an organization.  On desktop accounting software,
    one BookSet row would typically represent one saved file.  For example, you
    might have one BookSet for each country a corportation operates in; or, a
    single row for a small company.

    Limitations: only single currencies are supported and balances are only
    recorded to 2 decimal places.

    Future: the prefered timezone (for reporting and reconcilliation)
    """

    id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=80)

    def accounts(self):
        #sorting?
        return self.account_objects.all()

    def get_account(self, name):
        return self.account_objects.get(name=name)

    def __unicode__(self):
        return self.description

class Project(models.Model, ProjectBase):
    """A sub-set of a BookSet.

    This is useful for tracking different activites, projects, major products,
    or sub-divisions of an organization.  A project should behave like a
    "BookSet", except that its transactions will show up both in this Project and its BookSet.

    It's not necessary to use Projects: transactions can be entered in the
    BookSet directly without putting them in a project.
    """

    id = models.AutoField(primary_key=True)

    name = models.TextField("name memo", help_text="project name")

    bookset = models.ForeignKey(BookSet, related_name="projects",
        help_text="""The bookset for this project.""")


    def accounts(self):
        return self.bookset.accounts()

    def get_bookset(self):
        return self.bookset

    def _associate_transaction(self, tx):
        tx.project = self

    def _filter_project_qs(self, qs):
        return qs.filter(transaction__project=self)

    def __unicode__(self):
        return '<Project {0}>'.format(self.name)
 
class Account(models.Model, _AccountApi):
    """ A financial account in a double-entry bookkeeping bookset.  For example
    a chequing account, or bank-fee expense account.


    Limitations: no currency information is stored; all entries are assumed to
    be in the same currency at the rest of the book.
    """

    #Future considerations:
    #
    #    timezone: when an account is with a bank that uses a different time zone then the one
    #    the server uses, it would be useful to note that timezone in the database.  This way,
    #    reports could be made to help reconcilliation against the bank's statements.
    #
    #    organizing accounts into a tree: generally accepted practice groups accounts into
    #    the categories "Assets", "Liabilities", "Expenses", "Income" and "Capital/equity";
    #    and bookkeepers like to further sub-divide their accounts.  It would be nice to 
    #    support this kind of organization.

    accid = models.AutoField(primary_key=True)
    bookset = models.ForeignKey(BookSet, db_column='org', related_name='account_objects')

    def get_bookset(self):
        return self.bookset

    positive_credit = models.BooleanField(
        """credit entries increase the value of this account.  Set to False for
        Asset & Expense accounts, True for Liability, Revenue and Equity accounts.""")

    name = models.TextField() #slugish?  Unique?
    description = models.TextField(blank=True)

    #functions needed by _AccountApi
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
        return '{0} {1}'.format(self.bookset.description, self.name)

class ThirdParty(models.Model):
    """Represents a third party (eg. Account Receivable or Account Payable).

    (Question: using only the ORM, how do I get a third party's balance?
    account.entries.filter(third_party=self).sum()? )
    
    Each third party is associated with a bookkeeping account (traditionally
    either the AR or AP account).  A third party's account can be accessed by
    calling "get_third_party(thid_party)" on the asscoiated account.  This also
    works in combination with Projects: call get_third_party from the project's
    AR and AP accounts instead of the global ones. 

    This is a simplified accounting model for client and vendor accounts: a
    simple sub-account of "Accounts Receivable" or "Accounts Payable", that
    completely ignore invoices (for now).  Future versions may embrace a more
    complex model, including:

        invoices:
            invoices are sent to client or received from the vendor.
            each is a collection of AccountEntries to revenue, which only posted to ARs when the invoice is "posted". (Ie, delivered to the client)
            each has a post date, due date.. etc.
            when payments come in, they are added as credit AccountEntries for the the invoice (and client) and debits to a bank account
            completely paid invoices are marked as PAID.
        Jobs:
            a long-term project for a client is called a "job" and can invole multiple invoices.  (Eg. if it lasts longer than a month, you'll have related bills to pay.)
    """
    id = models.AutoField(primary_key=True)

    name = models.TextField("name memo",
        help_text="""this field is only used for displaying information during
            debugging.  It's best to use a OneToOne relationship with another
            tabel to hold all the information you actually need.""")

    account = models.ForeignKey(Account, related_name="third_parties", 
        help_text= """The parent account: typically an 'AR' or 'AP' account.""")

    def get_account(self):
        return self.account

    def _associate_entry(self, entry):
        """ Transitional function: abstracts the database's representation of third parties."""
        entry.third_party = self

    def _filter_third_party(self, qs):
        """ Transitional function: abstracts the database's representation of third parties."""
        return qs.filter(third_party=self)

    def __unicode__(self):
        return '<ThirdParty {0} {1}>'.format(self.name, self.id)
 
class Transaction(models.Model):
    """ A transaction is a collection of AccountEntry rows (for different
    accounts) that sum to zero.

    The most common transaction is a Debit (positive change) from one account
    and a Credit (negative change) in another account.  Transactions involving
    more than two accounts are called "split transactions" and are also
    supported, so long as they add up to zero.  Note that split transactions
    are best avoided because it's more difficult to import those transactions
    into other financial software.

    Invarients: 
        1. All entries for each transaction transaction must add up to zero.
        (This invarient may be enforced in the future.)

        2. All entries must be between accounts of the same BookSet.
    """

    tid = models.AutoField(primary_key=True)

    t_stamp = models.DateTimeField(default=timezone.now)
    description = models.TextField()

    project = models.ForeignKey(Project, related_name="transactions",
        help_text="""The project for this transaction (if any).""", null=True)

    def __unicode__(self):
        return "<Transaction {0}: {1}/>".format(self.tid, self.description)

#questionable use of natural_keys?
class AccountEntryManager(models.Manager):
    def get_by_natural_key(self, account,transaction):
        return self.get(account=account, transaction=transaction)

class AccountEntry(models.Model):
    """A line entry changing the balance of an account.

    Some examples of account entries:

        Debit  $100 to the Bank account
        Credit $130 to a   Revenue account
        Credit  $80 to an  expense account
        Debit   $50 to Accounts Receivable for John Smith

    Debits are recorded as positive 'amount' values while Credits are negative
    'amount' values. (This is follows the industry convention.)
    """

    class Meta:
        unique_together= (('account', 'transaction'),)
    def natural_key(self):
        return (self.transaction.pk,) + self.account.natural_key()

    objects = AccountEntryManager()

    aeid = models.AutoField(primary_key=True)

    transaction = models.ForeignKey(Transaction, db_column='tid',related_name='entries')

    account = models.ForeignKey(Account, db_column='accid', related_name='entries')

    amount = models.DecimalField(max_digits=8,decimal_places=2,
        help_text="""Debits: positive; Credits: negative.""")

    description = models.TextField(
        help_text="""An optional "memo" field for this leg of the transaction.""")

    third_party = models.ForeignKey(ThirdParty, related_name='account_entries', null=True)

    def __unicode__(self):
        base =  "%d %s" % (self.amount, self.description)

        return base

