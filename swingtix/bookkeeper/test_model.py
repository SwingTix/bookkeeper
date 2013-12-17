"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from __future__ import unicode_literals

from django.test import TestCase

from .models import BookSet, Account, ThirdParty, Project
from .account_api import LedgerEntry

from decimal import Decimal
from datetime import datetime

from collections import namedtuple
AccountEntryTuple = namedtuple('AccountEntryTuple', 'time description memo debit credit opening closing txid')

class SimpleTest(TestCase):
    def setUp(self):
        self.book = BookSet()
        self.book.description = "test book"
        self.book.save()

        self.revenue = Account()
        self.revenue.bookset = self.book
        self.revenue.name = "revenue"
        self.revenue.description = "Revenue"
        self.revenue.positive_credit = True
        self.revenue.save()
        
        self.bank = Account()
        self.bank.bookset = self.book
        self.bank.name = "bank"
        self.bank.description = "Bank Account"
        self.bank.positive_credit = False
        self.bank.save()
        
        self.expense = Account()
        self.expense.bookset = self.book
        self.expense.name = "expense"
        self.expense.description = "Expenses"
        self.expense.positive_credit = False
        self.expense.save()

        self.ar = Account()
        self.ar.bookset = self.book
        self.ar.name = "ar"
        self.ar.description = "Accounts Receivable"
        self.ar.positive_credit = False
        self.ar.save()

    def assertEqualLedgers(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        if len(actual) != len(expected): return

        txid_set = set()
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

            self.assertEqual(a.txid in txid_set, False)
            txid_set.add(a.txid)

            self.assertEqual(str(a) != None, True)
            #ignore txid since the implementation is allowed to change.

            #TODO: make test for txid uniqueness?

    def test_basic_entries(self):
        #excersize the str/unicode functions
        self.assertEqual(str(self.bank) != None, True)
        self.assertEqual(str(self.book) != None, True)

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
            AccountEntryTuple(time=d1, description="jawbreaker", memo="", txid=None,
                debit=None, credit=Decimal("0.35"),
                opening=Decimal("0.00"), closing=Decimal("-0.35")),
            AccountEntryTuple(time=d2, description="Membership purchased in cash", memo="", txid=None,
                debit=Decimal("12.00"), credit=None,
                opening=Decimal("-0.35"), closing=Decimal("11.65")),
            AccountEntryTuple(time=d3, description="soft drink for myself", memo="", txid=None,
                debit=None, credit=Decimal("1.75"),
                opening=Decimal("11.65"), closing=Decimal( "9.90")),
            ])

        self.assertEqualLedgers(list(self.expense.ledger()), [
            AccountEntryTuple(d1, "jawbreaker", "", Decimal("0.35"), None, Decimal("0.00"), Decimal("0.35"), None),
            AccountEntryTuple(d3, "soft drink for myself", "", Decimal("1.75"), None, Decimal("0.35"), Decimal("2.10"), None),
            ])
        self.assertEqualLedgers(list(self.revenue.ledger()), [
            AccountEntryTuple(d2, "Membership purchased in cash", "", None, Decimal("12.00"), Decimal("0.00"), Decimal("12.00"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d2)), [
            AccountEntryTuple(d2, "Membership purchased in cash", "", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            AccountEntryTuple(d3, "soft drink for myself", "", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d3)), [
            AccountEntryTuple(d3, "soft drink for myself", "", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d4)), [
            AccountEntryTuple(d1, "jawbreaker", "", None, Decimal("0.35"), Decimal("0.00"), Decimal("-0.35"), None),
            AccountEntryTuple(d2, "Membership purchased in cash", "", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            AccountEntryTuple(d3, "soft drink for myself", "", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d3)), [
            AccountEntryTuple(d1, "jawbreaker", "", None, Decimal("0.35"), Decimal("0.00"), Decimal("-0.35"), None),
            AccountEntryTuple(d2, "Membership purchased in cash", "", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d2)), [
            AccountEntryTuple(d1, "jawbreaker", "", None, Decimal("0.35"), Decimal("0.00"), Decimal("-0.35"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d1)), [
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d2,end=d3)), [
            AccountEntryTuple(d2, "Membership purchased in cash", "", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d3,end=d4)), [
            AccountEntryTuple(d3, "soft drink for myself", "", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])
        self.assertEqualLedgers(list(self.bank.ledger(start=d2,end=d4)), [
            AccountEntryTuple(d2, "Membership purchased in cash", "", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            AccountEntryTuple(d3, "soft drink for myself", "", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

        #check that "other leg" feature works
        l_entries = list(self.bank.ledger())
        le = l_entries[0]
        self.assertEqual(le.description, "jawbreaker") #we have the right one
        self.assertEqual(le.credit, Decimal("0.35"))   #definately, we have the right one
        other_leg = le.other_entry()
        self.assertEqual(other_leg, self.expense)

    def test_AR(self):
        self.assertEqual(self.bank.balance(), Decimal("0.00"))
        self.assertEqual(self.expense.balance(), Decimal("0.00"))
        self.assertEqual(self.revenue.balance(), Decimal("0.00"))
        self.assertEqual(self.ar.balance(), Decimal("0.00"))

        self.ar1_party = ThirdParty()
        self.ar1_party.account = self.ar
        self.ar1_party.description = "Joe"
        self.ar1_party.save()

        self.ar2_party = ThirdParty()
        self.ar2_party.account = self.ar
        self.ar2_party.description = "bob"
        self.ar2_party.save()

        self.ar1 = self.book.get_third_party(self.ar1_party)
        self.ar2 = self.book.get_third_party(self.ar2_party)

        self.assertEqual(self.ar1.get_bookset(), self.book)


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

        self.assertEqualLedgers(list(self.ar.ledger()), [
            AccountEntryTuple(time=d2, debit=None,            credit=Decimal("31.41"), opening=Decimal("0.00"), closing=Decimal("-31.41"),
                description="Membership paid in cash", memo="", txid=None),
            AccountEntryTuple(time=d3, debit=None,            credit=Decimal("12.97"), opening=Decimal("-31.41"), closing=Decimal("-44.38"),
                description="Membership paid in cash", memo="", txid=None),
            AccountEntryTuple(time=d4, debit=Decimal("0.05"), credit=None,             opening=Decimal("-44.38"), closing=Decimal("-44.33"),
                description="plastic bag", memo="", txid=None),
            ])

        self.assertEqualLedgers(list(self.ar1.ledger()), [
            AccountEntryTuple(time=d2, debit=None,            credit=Decimal("31.41"), opening=Decimal("0.00"), closing=Decimal("-31.41"),
                description="Membership paid in cash", memo="", txid=None),
            AccountEntryTuple(time=d4, debit=Decimal("0.05"), credit=None,             opening=Decimal("-31.41"), closing=Decimal("-31.36"),
                description="plastic bag", memo="", txid=None),
            ])

        self.assertEqualLedgers(list(self.ar2.ledger()), [
            AccountEntryTuple(time=d3, debit=None,            credit=Decimal("12.97"), opening=Decimal(  "0.00"), closing=Decimal("-12.97"),
                description="Membership paid in cash", memo="", txid=None),
            ])

    def test_book_set_basic(self):
        book = BookSet(description = "test book")
        book.save()

        revenue = Account.objects.create(
            bookset = book,
            name = "revenue",
            description = "Revenue",
            positive_credit = True,
            )
        revenue.save()
        
        bank = Account.objects.create(
            bookset = book,
            name = "bank",
            description = "Bank Account",
            positive_credit = False
            )
        bank.save()

        ar = Account.objects.create(
            bookset = book,
            name = "ar",
            description = "Accounts Receivable",
            positive_credit = False
            )
        ar.save()
        
        expense = Account.objects.create(
            bookset = book,
            name = "expense",
            description = "Expenses",
            positive_credit = False
            )
        expense.save()

        e2 = book.get_account("expense")
        self.assertEqual(e2, expense)
        b2 = book.get_account("bank")
        self.assertEqual(b2, bank)
        r2 = book.get_account("revenue")
        self.assertEqual(r2, revenue)

        accounts = book.accounts()
        l = [ a.name for a in accounts ]
        l.sort()
        self.assertEqual(l, ["ar", "bank", "expense", "revenue"])

        party1 = ThirdParty.objects.create(
            account = ar,
            name = "Joe")
        party1.save()

        ar1 = book.get_third_party(party1)
        self.assertEqual(str(ar1) != None, True)

    def test_project_book_basic(self):
        master_book = BookSet.objects.create(
            description = "test book")
        master_book.save()

        revenue = Account.objects.create(
            bookset = master_book,
            name = "revenue",
            description = "Revenue",
            positive_credit = True,
            )
        revenue.save()
        
        bank = Account.objects.create(
            bookset = master_book,
            name = "bank",
            description = "Bank Account",
            positive_credit = False
            )
        bank.save()

        ar = Account.objects.create(
            bookset = master_book,
            name = "ar",
            description = "Accounts Receivable",
            positive_credit = False
            )
        ar.save()
        
        expense = Account.objects.create(
            bookset = master_book,
            name = "expense",
            description = "Expenses",
            positive_credit = False
            )
        expense.save()

        project_db = Project.objects.create(
            name="project_jumbo",
            bookset=master_book
            )
        project_db.save()
        book = project_db

        #do these work the same way?
        e2 = book.get_account("expense")
        self.assertEqual(e2._parent, expense)
        b2 = book.get_account("bank")
        self.assertEqual(b2._parent, bank)
        r2 = book.get_account("revenue")
        self.assertEqual(r2._parent, revenue)

        accounts = book.accounts()
        l = [a.name for a in accounts]
        l.sort()
        self.assertEqual(l, ["ar", "bank", "expense", "revenue"])

        party1 = ThirdParty.objects.create(
            account = ar,
            name = "Joe"
            )
        party1.save()

        ar1 = book.get_third_party(party1)

    def test_project_book_usage(self):
        project_a = Project.objects.create(
            name="project_jumbo",
            bookset=self.book
            )
        project_a.save()
        project_b = Project.objects.create(
            name="project_mantis",
            bookset=self.book
            )
        project_b.save()

        self.assertEqual(str(project_a) != None, True)
        self.assertEqual(str(project_b) != None, True)

        bank  = self.book.get_account("bank")
        bankA = project_a.get_account("bank")
        bankB = project_b.get_account("bank")
        rev   = self.book.get_account("revenue")
        revA  = project_a.get_account("revenue")
        revB  = project_b.get_account("revenue")
        ar    = self.book.get_account("ar")
        arA   = project_a.get_account("ar")
        arB   = project_b.get_account("ar")

        #everything starts at zero
        self.assertEqual(bank.balance(),       Decimal("0.00"))
        self.assertEqual(bankA.balance(),      Decimal("0.00"))
        self.assertEqual(bankB.balance(),      Decimal("0.00"))
        self.assertEqual(rev.balance(),        Decimal("0.00"))
        self.assertEqual(revA.balance(),       Decimal("0.00"))
        self.assertEqual(revB.balance(),       Decimal("0.00"))
        self.assertEqual(ar.balance(),         Decimal("0.00"))
        self.assertEqual(arA.balance(),        Decimal("0.00"))
        self.assertEqual(arB.balance(),        Decimal("0.00"))

        #stuff in one project doesn't show up in other books (and vice-versa), but does in the master book.
        bankA.debit(Decimal("15.23"),revA,  "registration for something")
        self.assertEqual(bankA.balance(),      Decimal("15.23"))
        self.assertEqual(revA.balance(),       Decimal("15.23"))
        self.assertEqual(bank.balance(),       Decimal("15.23"))
        self.assertEqual(rev.balance(),        Decimal("15.23"))
        self.assertEqual(bankB.balance(),      Decimal("0.00"))
        self.assertEqual(revB.balance(),       Decimal("0.00"))

        bankB.credit(Decimal("2.00"),revA, "discount for awesomeness")
        self.assertEqual(bankB.balance(),      Decimal("-2.00"))
        self.assertEqual(revB.balance(),       Decimal("-2.00"))
        self.assertEqual(bank.balance(),       Decimal("13.23"))
        self.assertEqual(rev.balance(),        Decimal("13.23"))

        self.assertEqual(bankA.balance(),      Decimal("15.23"))
        self.assertEqual(revA.balance(),       Decimal("15.23"))
        
        #third party (ARs) also work with project
        party1 = ThirdParty(
            account = ar,
            name = "Joe")
        party1.save()
        arA_party1 = project_a.get_third_party(party1)
        arB_party1 = project_b.get_third_party(party1)

        self.assertEqual(str(party1)     != None, True)
        self.assertEqual(str(arA_party1) != None, True)
        self.assertEqual(str(arB_party1) != None, True)

        party2 = ThirdParty(
            account = ar,
            name = "Jordan")
        party2.save()
        arA_party2 = project_a.get_third_party(party2)
        arB_party2 = project_b.get_third_party(party2)

        #project-sub-accounts are idenpendant of other projects, and other sub-acccounts.
        self.assertEqual(ar.balance(),         Decimal("0.00"))
        self.assertEqual(arA.balance(),        Decimal("0.00"))
        self.assertEqual(arB.balance(),        Decimal("0.00"))
        self.assertEqual(arA_party1.balance(), Decimal("0.00"))
        self.assertEqual(arB_party1.balance(), Decimal("0.00"))
        self.assertEqual(arA_party2.balance(), Decimal("0.00"))
        self.assertEqual(arB_party2.balance(), Decimal("0.00"))
        self.assertEqual(rev.balance(),        Decimal("13.23"))
        self.assertEqual(revA.balance(),       Decimal("15.23"))
        self.assertEqual(revB.balance(),       Decimal("-2.00"))

        arA_party1.debit(Decimal("1.23"),revA,  "registration for something blue")
        self.assertEqual(ar.balance(),         Decimal("1.23"))
        self.assertEqual(arA.balance(),        Decimal("1.23"))
        self.assertEqual(arB.balance(),        Decimal("0.00"))
        self.assertEqual(arA_party1.balance(), Decimal("1.23"))
        self.assertEqual(arB_party1.balance(), Decimal("0.00"))
        self.assertEqual(arA_party2.balance(), Decimal("0.00"))
        self.assertEqual(arB_party2.balance(), Decimal("0.00"))
        self.assertEqual(rev.balance(),        Decimal("14.46"))
        self.assertEqual(revA.balance(),       Decimal("16.46"))
        self.assertEqual(revB.balance(),       Decimal("-2.00"))

        arB_party2.debit(Decimal("0.19"), revB, "registration for something red")
        self.assertEqual(ar.balance(),         Decimal("1.42"))
        self.assertEqual(arA.balance(),        Decimal("1.23"))
        self.assertEqual(arB.balance(),        Decimal("0.19"))
        self.assertEqual(arA_party1.balance(), Decimal("1.23"))
        self.assertEqual(arB_party1.balance(), Decimal("0.00"))
        self.assertEqual(arA_party2.balance(), Decimal("0.00"))
        self.assertEqual(arB_party2.balance(), Decimal("0.19"))
        self.assertEqual(rev.balance(),        Decimal("14.65"))
        self.assertEqual(revA.balance(),       Decimal("16.46"))
        self.assertEqual(revB.balance(),       Decimal("-1.81"))

        arA_party2.debit(Decimal("0.07"), revA, "registration for something purple")
        self.assertEqual(ar.balance(),         Decimal("1.49"))
        self.assertEqual(arA.balance(),        Decimal("1.30"))
        self.assertEqual(arB.balance(),        Decimal("0.19"))
        self.assertEqual(arA_party1.balance(), Decimal("1.23"))
        self.assertEqual(arB_party1.balance(), Decimal("0.00"))
        self.assertEqual(arA_party2.balance(), Decimal("0.07"))
        self.assertEqual(arB_party2.balance(), Decimal("0.19"))
        self.assertEqual(rev.balance(),        Decimal("14.72"))
        self.assertEqual(revA.balance(),       Decimal("16.53"))
        self.assertEqual(revB.balance(),       Decimal("-1.81"))

