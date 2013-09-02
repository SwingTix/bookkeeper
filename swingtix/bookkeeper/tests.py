"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase

from swingtix.bookkeeper.models import BookSet, Account, ThirdParty
from swingtix.bookkeeper.account_api import AccountEntryTuple

from decimal import Decimal
from datetime import datetime


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

    def setUp(self):
        self.book = BookSet()
        self.book.description = "test book"
        self.book.save()

        self.revenue = Account()
        self.revenue.book = self.book
        self.revenue.name = "revenue"
        self.revenue.description = "Revenue"
        self.revenue.positive_credit = True
        self.revenue.save()
        
        self.bank = Account()
        self.bank.book = self.book
        self.bank.name = "bank"
        self.bank.description = "Bank Account"
        self.bank.positive_credit = False
        self.bank.save()
        
        self.expense = Account()
        self.expense.book = self.book
        self.expense.name = "expense"
        self.expense.description = "Expenses"
        self.expense.positive_credit = False
        self.expense.save()

        self.ar = Account()
        self.ar.book = self.book
        self.ar.name = "ar"
        self.ar.description = "Accounts Receivable"
        self.ar.positive_credit = False
        self.ar.save()


    def assertEqualLedgers(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        if len(actual) != len(expected): return

        for i in range(len(actual)):
            a = actual[i]
            b = expected[i]
            self.assertEqual(a.time, b.time)
            self.assertEqual(a.description, b.description)
            self.assertEqual(a.memo, b.memo)
            self.assertEqual(a.credit, b.credit)
            self.assertEqual(a.debit, b.debit)
            self.assertEqual(a.opening, b.opening)
            self.assertEqual(a.closing, b.closing)

    def test_basic_entries(self):
        self.assertEqual(self.bank.balance(), Decimal("0.00"))
        self.assertEqual(self.expense.balance(), Decimal("0.00"))
        self.assertEqual(self.revenue.balance(), Decimal("0.00"))

        d0 = datetime(2010,1,1,1,0,59)
        d1 = datetime(2010,1,1,1,1,0)
        d2 = datetime(2010,1,1,1,1,1)
        self.bank.debit(Decimal("12.00"), self.revenue, "Membership purchased in cash", datetime=d2)
        d3 = datetime(2010,1,1,1,1,2)
        self.bank.credit(Decimal("1.75"), self.expense, "soft drink for myself", datetime=d3)
        d4 = datetime(2010,1,1,1,1,3)
        self.bank.credit(Decimal("0.35"), self.expense, "jawbreaker", datetime=d1)

        self.assertEqual(self.bank.balance(), Decimal("9.90"))
        self.assertEqual(self.expense.balance(), Decimal("2.10"))
        self.assertEqual(self.revenue.balance(), Decimal("12.00"))

        self.assertEqual(self.bank.balance(d0), Decimal( "0.00"))
        self.assertEqual(self.bank.balance(d1), Decimal( "0.00"))
        self.assertEqual(self.bank.balance(d2), Decimal( "-0.35"))
        self.assertEqual(self.bank.balance(d3), Decimal("11.65"))
        self.assertEqual(self.bank.balance(d4), Decimal("9.90"))

        self.assertEqual(self.expense.balance(d0), Decimal("0.00"))
        self.assertEqual(self.expense.balance(d1), Decimal("0.00"))
        self.assertEqual(self.expense.balance(d2), Decimal("0.35"))
        self.assertEqual(self.expense.balance(d3), Decimal("0.35"))
        self.assertEqual(self.expense.balance(d4), Decimal("2.10"))

        self.assertEqual(self.revenue.balance(d0), Decimal( "0.00"))
        self.assertEqual(self.revenue.balance(d1), Decimal( "0.00"))
        self.assertEqual(self.revenue.balance(d2), Decimal( "0.00"))
        self.assertEqual(self.revenue.balance(d3), Decimal("12.00"))
        self.assertEqual(self.revenue.balance(d4), Decimal("12.00"))

        self.assertEqualLedgers(list(self.bank.ledger()), [
            AccountEntryTuple(time=d1, description=u"jawbreaker", memo=u"", txid=None,
                debit=None, credit=Decimal("0.35"),
                opening=Decimal("0.00"), closing=Decimal("-0.35")),
            AccountEntryTuple(time=d2, description=u"Membership purchased in cash", memo=u"", txid=None,
                debit=Decimal("12.00"), credit=None,
                opening=Decimal("-0.35"), closing=Decimal("11.65")),
            AccountEntryTuple(time=d3, description=u"soft drink for myself", memo=u"", txid=None,
                debit=None, credit=Decimal("1.75"),
                opening=Decimal("11.65"), closing=Decimal( "9.90")),
            ])

        self.assertEqualLedgers(list(self.expense.ledger()), [
            AccountEntryTuple(d1, u"jawbreaker", u"", Decimal("0.35"), None, Decimal("0.00"), Decimal("0.35"), None),
            AccountEntryTuple(d3, u"soft drink for myself", u"", Decimal("1.75"), None, Decimal("0.35"), Decimal("2.10"), None),
            ])
        self.assertEqualLedgers(list(self.revenue.ledger()), [
            AccountEntryTuple(d2, u"Membership purchased in cash", u"", None, Decimal("12.00"), Decimal("0.00"), Decimal("12.00"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d2)), [
            AccountEntryTuple(d2, u"Membership purchased in cash", u"", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            AccountEntryTuple(d3, u"soft drink for myself", u"", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d3)), [
            AccountEntryTuple(d3, u"soft drink for myself", u"", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d4)), [
            AccountEntryTuple(d1, u"jawbreaker", u"", None, Decimal("0.35"), Decimal("0.00"), Decimal("-0.35"), None),
            AccountEntryTuple(d2, u"Membership purchased in cash", u"", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            AccountEntryTuple(d3, u"soft drink for myself", u"", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d3)), [
            AccountEntryTuple(d1, u"jawbreaker", u"", None, Decimal("0.35"), Decimal("0.00"), Decimal("-0.35"), None),
            AccountEntryTuple(d2, u"Membership purchased in cash", u"", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d2)), [
            AccountEntryTuple(d1, u"jawbreaker", u"", None, Decimal("0.35"), Decimal("0.00"), Decimal("-0.35"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d1)), [
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d2,end=d3)), [
            AccountEntryTuple(d2, u"Membership purchased in cash", u"", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d3,end=d4)), [
            AccountEntryTuple(d3, u"soft drink for myself", u"", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])
        self.assertEqualLedgers(list(self.bank.ledger(start=d2,end=d4)), [
            AccountEntryTuple(d2, u"Membership purchased in cash", u"", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            AccountEntryTuple(d3, u"soft drink for myself", u"", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

    def test_AR(self):
        self.assertEqual(self.bank.balance(), Decimal("0.00"))
        self.assertEqual(self.expense.balance(), Decimal("0.00"))
        self.assertEqual(self.revenue.balance(), Decimal("0.00"))
        self.assertEqual(self.ar.balance(), Decimal("0.00"))

        self.ar1 = ThirdParty()
        self.ar1.account = self.ar
        self.ar1.description = "Joe"
        self.ar1.save()

        self.ar2 = ThirdParty()
        self.ar2.account = self.ar
        self.ar2.description = "bob"
        self.ar2.save()

        self.assertEqual(self.ar.balance(), Decimal("0.00"))
        self.assertEqual(self.ar1.balance(), Decimal("0.00"))
        self.assertEqual(self.ar2.balance(), Decimal("0.00"))
  
        d0 = datetime(2010,1,1,1,0,59)
        d1 = datetime(2010,1,1,1,1,0)
        d2 = datetime(2010,1,1,1,1,1)
        self.bank.debit(Decimal("31.41"), self.ar1, "Membership paid in cash", datetime=d2)
        d3 = datetime(2010,1,1,1,1,2)
        self.bank.debit(Decimal("12.97"), self.ar2, "Membership paid in cash", datetime=d3)
        d4 = datetime(2010,1,1,1,1,3)
        self.ar1.debit(Decimal("0.05"), self.revenue, "plastic bag", datetime=d4)
        d5 = datetime(2010,1,1,1,1,4)

        self.assertEqual(self.ar.balance(d1),      Decimal("0.00"))
        self.assertEqual(self.ar1.balance(d1),     Decimal("0.00"))
        self.assertEqual(self.ar2.balance(d1),     Decimal("0.00"))
        self.assertEqual(self.revenue.balance(d1), Decimal("0.00"))
        self.assertEqual(self.bank.balance(d1),    Decimal("0.00"))

        self.assertEqual(self.ar.balance(d2),      Decimal("0.00"))
        self.assertEqual(self.ar1.balance(d2),     Decimal("0.00"))
        self.assertEqual(self.ar2.balance(d2),     Decimal("0.00"))
        self.assertEqual(self.revenue.balance(d2), Decimal("0.00"))
        self.assertEqual(self.bank.balance(d2),    Decimal("0.00"))

        self.assertEqual(self.ar.balance(d3),      Decimal("-31.41"))
        self.assertEqual(self.ar1.balance(d3),     Decimal("-31.41"))
        self.assertEqual(self.ar2.balance(d3),     Decimal("0.00"))
        self.assertEqual(self.revenue.balance(d3), Decimal("0.00"))
        self.assertEqual(self.bank.balance(d3),    Decimal("31.41"))

        self.assertEqual(self.ar.balance(d4),      Decimal("-44.38"))
        self.assertEqual(self.ar1.balance(d4),     Decimal("-31.41"))
        self.assertEqual(self.ar2.balance(d4),     Decimal("-12.97"))
        self.assertEqual(self.revenue.balance(d4), Decimal("0.00"))
        self.assertEqual(self.bank.balance(d4),    Decimal("44.38"))

        self.assertEqual(self.ar.balance(d5),      Decimal("-44.33"))
        self.assertEqual(self.ar1.balance(d5),     Decimal("-31.36"))
        self.assertEqual(self.ar2.balance(d5),     Decimal("-12.97"))
        self.assertEqual(self.revenue.balance(d5), Decimal("0.05"))
        self.assertEqual(self.bank.balance(d5),    Decimal("44.38"))

    def test_create_load_accounts(self):
        book = BookSet()
        book.description = "test book"
        book.save()

        revenue = Account()
        revenue.book = book
        revenue.name = "revenue"
        revenue.description = "Revenue"
        revenue.positive_credit = True
        revenue.save()
        
        bank = Account()
        bank.book = book
        bank.name = "bank"
        bank.description = "Bank Account"
        bank.positive_credit = False
        bank.save()
        
        expense = Account()
        expense.book = book
        expense.name = "expense"
        expense.description = "Expenses"
        expense.positive_credit = False
        expense.save()

        e2 = book.load_account("expense")
        self.assertEqual(e2, expense)
        b2 = book.load_account("bank")
        self.assertEqual(b2, bank)
        r2 = book.load_account("revenue")
        self.assertEqual(r2, revenue)

 
