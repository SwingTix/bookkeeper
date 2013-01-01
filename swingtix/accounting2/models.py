from django.db import models

import datetime


class BookSet(models.Model):
    id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=80)

    def __unicode__(self):
        return self.description

class ThirdParty(models.Model):
    id = models.AutoField(primary_key=True)

    name = models.TextField()
    def __unicode__(self):
        return '<ThirdParty orm %s %s>' % (self.name, self.id)
 
class AccountManager(models.Manager):
    def get_by_natural_key(self, name, *organization_key):
        organization = Organization.objects.get_by_natural_key(*organization_key)
        return self.get(name=name, organization=organization)

class Account(models.Model):
    class Meta:
        unique_together = (('name', 'organization'),)
    def natural_key(self):
        return (self.name,) + self.organization.natural_key()
    #natural_key.dependencies = ['organizations.organization']
    objects = AccountManager()

    accid = models.AutoField(primary_key=True)
    book = models.ForeignKey(BookSet, db_column='org', related_name='accounts')
    creditordebit = models.BooleanField("""False for Asset & Expense accounts, True for Liability, Revenue and Equity accounts.
        Accounts with 'creditordebit' set to True which increase with credit and decrease with debit.""")

    name = models.TextField() #slugish?
    description = models.TextField(blank=True)

    #parent account?
    #annotations for registration: receivables, revenue.. etc

    def __unicode__(self):
        return '%s %s' % (self.organization.name, self.name)

class Transaction(models.Model):

    tid = models.AutoField(primary_key=True)

    t_stamp = models.DateTimeField(default=datetime.datetime.now)
    description = models.TextField()

    #what is this used for again?
    #application-dependant.  For registration, this would map to event.id.
    #a m-n relationship might be more appropriate
    project = models.IntegerField()

    #annotations for registration: event/projectcode?

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


