# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import swingtix.bookkeeper.account_api
import django.utils.timezone
import swingtix.bookkeeper.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('accid', models.AutoField(serialize=False, primary_key=True)),
                ('positive_credit', models.BooleanField(verbose_name='credit entries increase the value of this account.  Set to False for\n        Asset & Expense accounts, True for Liability, Revenue and Equity accounts.', default=False)),
                ('name', models.TextField()),
                ('description', models.TextField(blank=True)),
            ],
            bases=(models.Model, swingtix.bookkeeper.models._AccountApi),
        ),
        migrations.CreateModel(
            name='AccountEntry',
            fields=[
                ('aeid', models.AutoField(serialize=False, primary_key=True)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Debits: positive; Credits: negative.', max_digits=8)),
                ('description', models.TextField(help_text='An optional "memo" field for this leg of the transaction.')),
                ('account', models.ForeignKey(related_name='entries', to='bookkeeper.Account', db_column='accid')),
            ],
        ),
        migrations.CreateModel(
            name='BookSet',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('description', models.CharField(max_length=80)),
            ],
            bases=(models.Model, swingtix.bookkeeper.account_api.BookSetBase),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('name', models.TextField(help_text='project name', verbose_name='name memo')),
                ('bookset', models.ForeignKey(help_text='The bookset for this project.', related_name='projects', to='bookkeeper.BookSet')),
            ],
            bases=(models.Model, swingtix.bookkeeper.account_api.ProjectBase),
        ),
        migrations.CreateModel(
            name='ThirdParty',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('name', models.TextField(help_text="this field is only used for displaying information during\n            debugging.  It's best to use a OneToOne relationship with another\n            tabel to hold all the information you actually need.", verbose_name='name memo')),
                ('account', models.ForeignKey(help_text="The parent account: typically an 'AR' or 'AP' account.", related_name='third_parties', to='bookkeeper.Account')),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('tid', models.AutoField(serialize=False, primary_key=True)),
                ('t_stamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('description', models.TextField()),
                ('project', models.ForeignKey(help_text='The project for this transaction (if any).', related_name='transactions', null=True, to='bookkeeper.Project')),
            ],
        ),
        migrations.AddField(
            model_name='accountentry',
            name='third_party',
            field=models.ForeignKey(related_name='account_entries', null=True, to='bookkeeper.ThirdParty'),
        ),
        migrations.AddField(
            model_name='accountentry',
            name='transaction',
            field=models.ForeignKey(related_name='entries', to='bookkeeper.Transaction', db_column='tid'),
        ),
        migrations.AddField(
            model_name='account',
            name='bookset',
            field=models.ForeignKey(related_name='account_objects', to='bookkeeper.BookSet', db_column='org'),
        ),
        migrations.AlterUniqueTogether(
            name='accountentry',
            unique_together=set([('account', 'transaction')]),
        ),
    ]
