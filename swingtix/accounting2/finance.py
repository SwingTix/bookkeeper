from dj_explore.twoflower import models
from dj_explore import settings
from django.db.models import Sum
from decimal import Decimal


class AccountLoadingError(Exception):
    def __init__(self, value):
        self.value = value

class AccountEntry:
    def __init__(self, date, opening_balance, closing_balance, description, debit=None, credit=None, memo=None):
        self.date = date
        self.opening_balance = opening_balance
        self.closing_balance = closing_balance
        self.description = description
        self.memo = memo
        self.debit = debit
        self.credit = credit

    @property
    def balance(self): return self.closing_balance

class Account(object):
    """A financial account.

    Transactions have to be posted between 2 or more accounts.  For maximum compatability with external accounting software,
    it's best to keep it between two accounts (in other words, don't use "split transactions").  With that in mind, the methods
    here are focused creation of 2 account transactions: debit, credit and post.

    Note that internally, entries are stored so that transaction amounts always sum to zero.  When calculating account balances,
    the values are negated (if necessary) so credits are positive for liability, revenue, and equity accounts, while debits are
    positive for asset and expense accounts.
    
    For quick reference, this is how debits and credits affect the standard account types:

    Account Type debit credit
     asset         +     -     (bank account, AR, creditcard sales)
     liability     -     +     (AP, creditcard purchases)
     revenue       -     +
     expense       +     -
     equity        -     +

    """
    def __init__(self, db):
        self._db = db

    def __str__(self):
        return "<Account '%s' for %s>" % (self._db.name, self._db.organization.name)

    #By historical accident, debits are negative and credits are positive in the database.  Apparently this is against
    #standard pratice.  So data doesn't have to be migrated, this variable is multipled against data before storage
    #and after retrieval.
    _DEBIT_IN_DB = -1

    @static
    def _db_to_debit_and_credit(amount):
        amount *= _DEBIT_IN_DB
        if amount < 0:
            #credit
            return (None, -amount)
        elif amount > 0:
            #debit
            return (amount, None)
        else:
            return (None, None)


    #TODO: check how debit and credit affects positive and negative values of account entries, or if it's just displaying
    def debit(self, amount, credit_account, description, debit_memo="", credit_memo="", project=None,time=None):
        """ Post a debit of 'amount' and a credit of -amount against this account and credit_account respectively.

        note amount must be non-negative.
        """

        assert amount >= 0
        return self.post(amount, credit_account, description, self_memo=debit_memo, other_memo=credit_memo, project=project, time=time)
    def credit(self, amount, debit_account, description, debit_memo="", credit_memo="", project=None, time=None):
        """ Post a credit of 'amount' and a debit of -amount against this account and credit_account respectively.

        note amount must be non-negative.
        """
        assert amount >= 0
        return self.post(-amount, debit_account, description, self_memo=credit_memo, other_memo=debit_memo, project=project, time=time)

    def post(self, amount, other_account, description, self_memo="", other_memo="", project=None, time=None):
        """ Post a transaction of 'amount' against this account and the negative amount against 'other_account'.

        This will show as a debit or credit against this account when amount > 0 or amount < 0 respectively.
        """

        #Note: debits are always positive, credits are always negative.  They should be negated before displaying
        #(expense and liability?) accounts
        tx = models.Transaction()
        if project:
            tx.project = project
        else:
            tx.project = 0

        if time:
            tx.t_stamp = time
        tx.description = description
        tx.save()

        a1 = self._make_ae(Account._DEBIT_IN_DB*amount, self_memo, tx)
        a1.save()
        a2 = other_account._make_ae(-Account._DEBIT_IN_DB*amount, other_memo, tx)
        a2.save()

        return (a1,a2)

    def _make_ae(self, amount, memo, tx):
        """ Makes an AccountEntry for this account with the given amount, memo and tx set.  Does not save it. """

        ae = models.AccountEntry()
        ae.account = self._db
        #ae.third_party = third_party
        ae.transaction = tx
        ae.amount = amount
        ae.description = memo
        return ae

    def _query_set(self):
        """ Makes a query set that will return all entries for this account. """
        return self._db.entries

    def balance(self, date=None):
        """ returns the account balance as of 'date' (datetime stamp) or now().  """

        assert date == None, "date-balance not implemented"

        r= self._query_set().aggregate(b=Sum('amount'))
        b = r['b']

        flip = Account._DEBIT_IN_DB 
        if self._db.creditordebit:
            flip *= -1

        if b == None:
            b = Decimal("0.00")
        b *= flip

        #print "returning balance %s for %s" % (b, self)
        return b

    def entries(self, from_date=None, to_date=None):
        if from_date:
            balance = self.balance(date=from_date)
        else:
            balance = Decimal("0.00")

        qs = self._query_set()
        if from_date:
            qs = qs.filter(from_date__gte=from_date)
        if to_date:
            qs = qs.filter(to_date__lt=to_date)
        qs = qs.order_by("transaction__t_stamp")
        
        flip = Account._DEBIT_IN_DB 
        if self._db.creditordebit:
            flip = -flip

        for ae in qs:
            r = {
                "description": ae.transaction.description,
                "memo": ae.description,
                "datetime": ae.transaction.t_stamp,
            }

            r['opening_balance'] = balance

            balance += flip*ae.amount
            r['closing_balance'] = balance
            r['balance'] = balance

            (r['debit'], r['credit']) = Account._db_to_debit_and_credit(ae.amount)

            yield r

    #def daily_summary(self, from_date=None, to_date=None, timezone=None):
    #    assert False, "not implemented"

    @staticmethod
    def house(type):
        return Account.by_name(_HOUSE_ORG, type)

    @staticmethod
    def by_name(org, name):
        try:
            a = org.accounts.get(name=name)
        except models.FinancialAccount.DoesNotExist:
            raise AccountLoadingError("couldn't load account for %s with name %s." % (org.name, name))
        return Account(a)

class Books(object):
    def __init__(self, db):
        self._db = db

    @staticmethod
    def by_id(id):
        try:
            b = models.Book.objects.get(pk=id)
        except models.Book.DoesNotExist:
            raise BooksLoadingError("couldn't load books with id {0}.".format(id))
        return Books(b)

    def account(self, name):
        try:
            a = self._db.accounts.get(name=name)
        except models.FinancialAccount.DoesNotExist:
            raise AccountLoadingError("couldn't load account for %s with name %s." % (org.name, name))
        return Account(a)

        

class ThirdParty(Account):
    def __init__(self, db, tp):
        assert db != None
        assert tp != None
        if isinstance(db, Account):
            self._db = db._db
        elif isinstance(db, models.FinancialAccount):
            self._db = db
        else:
            assert False, "db is an unrecognized account object: %s" % (db.__class__)

        self._tp = tp

    def __str__(self):
        return "<ThirdParty account '%s' %s  for %s>" % (self._db.name, self._tp, self._db.organization.name)

    #constructor idea: AR that takes (org,tp) or just tp

    def _make_ae(self, amount, memo, tx):
        ae = super(ThirdParty, self)._make_ae(amount,memo,tx)
        ae.third_party = self._tp

        return ae

    def _query_set(self):
        return self._db.entries.filter(third_party=self._tp)


def _load_account_by_name_old(org, name, msg=""):
    try:
        a = org.accounts.get(name=name)
    except models.FinancialAccount.DoesNotExist:
        raise AccountLoadingError("couldn't load account for %s with name %s.  %s" % (org.name, name, msg))
    return a

class AccountLoadingError(Exception):
    def __init__(self, value):
        self.value = value

#still used by test_beanstream.
def _getHouseAR():
    return _load_account_by_name_old(_HOUSE_ORG, 'AR', "house accounts receivable");

def _make_registration_entry(org, third_party):
    ae = models.AccountEntry()
    ae.account = _getAccountAR(org)
    ae.third_party = third_party
    return ae

def isArRevenue(org, account_entry):
    """ return (revenue in  account_entry.transaction.entries.account) """
    #naive approach
    revenue = _getAccountRevenue(org)
    t = account_entry.transaction
    for ae in t.entries.all():
        if ae.account == revenue:
            return True
    return False

def isOnlyArRevenue(org, r):
    """ return (revenue in  account_entry.transaction.entries.account) """

    revenue = _getAccountRevenue(org)
    ar = _getAccountAR(org)
    for ae in r.third_party.account_entries.all():
        t = ae.transaction
        for ae2 in t.entries.all():
            if ae2.account != revenue and ae2.account != ar:

                return False
    return True

#Can I make this generic?
#def record_new_reg_option(cs,org,event,rc, eoc):
# org = event.organization
# project_code = event_db.id
def record_new_reg_option(org,third_party, project_code, ii):
    """ record what's owed for a new registration """
    """ Make accounting entries for the given new registration option """

    #event_db = reg.event._db
    #org_db = event_db.organization

    #cs: not used
    #org: account objects
    #event: "project" account field
    #rc: rc.registration.  So 
    #eoc.cost: ii.price
    #eoc.name: ii.name

    tx = models.Transaction()
    tx.project = project_code
    tx.description = 'registration option charge for %s' % (ii.name)
    tx.save()

    entry_ar = _make_registration_entry(org, third_party)
    entry_ar.third_party = third_party
    entry_ar.transaction = tx
    entry_ar.amount = -ii.price
    entry_ar.description = 'charge for %s' % (ii.name)
    entry_ar.save()

    entry_rv = models.AccountEntry()
    entry_rv.account = _getAccountRevenue(org)
    entry_rv.transaction = tx
    entry_rv.amount = ii.price
    entry_rv.description = 'revenue for %s' % (ii.name)
    entry_rv.save()

def record_cash_payment(org, reg, amount, method, place):
    """ record a (cash) payment for the given registration

    This records: CR the registration account, an DB the 'bank' account. """

    tx = models.Transaction()
    tx.project = reg.event.id
    tx.description = 'payment from %s %s' % (reg.fname, reg.lname)
    tx.save()

    entry_ar = _make_registration_entry(org, reg.third_party)
    entry_ar.transaction = tx
    entry_ar.amount = amount
    entry_ar.description = 'payment received: %s %s' % (method, place)
    entry_ar.save()

    entry_rv = models.AccountEntry()
    entry_rv.account = _getAccountBank(org)
    entry_rv.transaction = tx
    entry_rv.amount = -amount
    entry_rv.description = 'payment for %s' % (reg.event.name)
    entry_rv.save()


class DuplicateTransactionException(Exception):
    def __init__(self, value):
        self.value = value


from django.db import transaction
#@transaction.commit_on_success
#def record_house_online_payment(org, amount, fee,  memo, extern_party=None, extern_id=None, extern_tx=None):

def record_ar_change_keyword(org, reg, target,  amount, memo, time=None):
    """ records a payment/refund or charge/discount (if target is 'bank' or 'revenue' respectively for the given registration.

    Here, amount > 0 will apply a credit to the given registration.
    """

    r = {}
    ar = Account.by_name(org, "AR")
    if target == 'bank':
        target = Account.by_name(org, "bank")
    elif target == 'revenue':
        target = Account.by_name(org, "revenue")
    else:
        assert False
    target 
    expense = Account.by_name(_HOUSE_ORG, "bank")

    description = 'adjustment for %s %s' % (reg.fname, reg.lname)

    if amount > 0:
        ar.debit(amount, target, description, debit_memo=memo, credit_memo=memo, time=time, project=reg.event.id)
    else:
        ar.credit(-amount, target, description, debit_memo=memo, credit_memo=memo, time=time, project=reg.event.id)

class InvoiceItem(object):
    """A line item on an invoice.  Typically description, price, and quanitity
    (not yet supported). """

    def __init__(self, price, name, description=None, related=None):
        self._price = price
        self._name = name
        self._description = description
        self._related = related

    @property
    def description(self):
        return self._description

    @property
    def price(self):
        """ The price billed for this item.  Negative indicates a discount. """
        return self._price

    @property
    def name(self):
        return self._name


