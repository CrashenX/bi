# Copyright 2017-2019 Jesse J. Cook
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# analyzer.py: analyze bi data

from libi.matcher import RulesMatcher
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING
from re import sub


class Analyzer():
    def __init__(self, dbname):
        client = MongoClient()
        self.db = getattr(client, dbname)
        self.rules = []
        rules = self.db.rules.find({}, {"_id": 0})
        for rule in rules:
            self.rules.append(rule)
        self.nicks = {}
        nicks = self.db.accounts.find({}, {"name": 1, "nick": 1})
        for nick in nicks:
            self.nicks[nick["name"]] = nick["nick"]

    @staticmethod
    def _calc_budget(buckets):
        budget = 0.0
        for _, bucket in buckets.items():
            if bucket.get("budget"):
                budget += bucket.get("target", 0.0)
        return budget

    @staticmethod
    def _color(number):
        n = round(number, 2)
        if n == 0.00:
            return '\033[94m'
        elif n > 0.00:
            return '\033[92m'
        else:
            return '\033[91m'

    @staticmethod
    def _format_trans(transaction, trans_fmt, nicks):
        desc = transaction.get("description")
        if 'Check ' not in desc:
            desc = sub(r'\d+', '', desc)
        desc = sub(r'[^a-zA-Z0-9 .]', '', desc)
        desc = sub(r'^  *', '', desc)
        desc = sub(r'  *', ' ', desc)
        if len(transaction.get("buckets")) > 1:
            desc = "* " + desc
        desc = desc[0:28]
        day = transaction.get("date").day
        amount = transaction.get("amount")
        account = transaction.get("account")
        return trans_fmt % (day, desc, amount, nicks.get(account, ""))

    @classmethod
    def _pretty_print(cls, start, end, budgets, nicks):
        header_fmt = "%-48s%9s  %9s  %9s"
        budget_fmt = "%-48s%9.2f -%9.2f =%s%9.2f\033[0m"
        total_fmt = "%s%-48s%9.2f\033[0m -%s%9.2f\033[0m =%s%9.2f\033[0m"
        trans_fmt = "  %02d  %-28s%10.2f %s"
        print("%38s - %-38s\n" % (start, end))
        for bname, budget in sorted(budgets.items()):
            total_actual, total_target = 0.0, 0.0
            print(bname.center(79))
            print("=" * 79)
            print(header_fmt % ("Name", "Actual", "Target", "Delta"))
            print(header_fmt % ("-" * 4, "-" * 6, "-" * 6, "-" * 5))
            for _, bucket in sorted(budget.items(), key=lambda x: abs(
                                    x[1].get("actual", 0)-x[1].get("target"))):
                tname = bucket.get("name")
                target = bucket.get("target")
                actual = bucket.get("actual", 0)
                total_target += target
                total_actual += actual
                d = round(actual - target, 2)
                print(budget_fmt % (tname, actual, target, cls._color(d), d))
                transactions = bucket.get("transactions")
                if bname == 'Transfers':
                    transactions = sorted(transactions, key=lambda x:
                                          abs(x.get('amount')))
                for transaction in transactions:
                    print(cls._format_trans(transaction, trans_fmt, nicks))
            target = cls._calc_budget(budget)
            d = round(total_actual - total_target, 2)
            print("%s" % ("-" * 79))
            print(total_fmt % ("Total",
                               cls._color(total_actual), total_actual,
                               cls._color(total_target), total_target,
                               cls._color(d), d))
            print("%s\n" % ("=" * 79))

    @staticmethod
    def _add_to_bucket(transaction, bucket):
        transaction["buckets"] = (transaction.get("buckets", []) + [bucket])
        bucket.get("transactions").append(transaction)
        bucket["actual"] = (bucket.get("actual", 0) +
                            transaction.get("amount"))

    @classmethod
    def _bucket_transactions(cls, transactions, budgets, matcher):
        for transaction in transactions:
            rules = matcher.get_matching_rules(transaction)
            if not rules:
                bucket = budgets.get("Uncategorized").get("Uncategorized")
                cls._add_to_bucket(transaction, bucket)
                continue
            for rule in rules:
                budget = budgets.get(rule.get("bucket").get("budget"))
                bucket = budget.get(rule.get("bucket").get("name"))
                cls._add_to_bucket(transaction, bucket)

    @staticmethod
    def _get_budgets(rules):
        uncat = {"budget": "Uncategorized", "name": "Uncategorized",
                 "target": 0.00, "transactions": []}
        budgets = {"Uncategorized": {"Uncategorized": uncat}}
        for rule in rules:
            bucket = rule.get("bucket")
            bucket["transactions"] = []
            budget = budgets.get(bucket.get("budget"), {})
            budget[bucket.get("name")] = bucket
            budgets[bucket.get("budget")] = budget
        return budgets

    def _get_transactions(self, start, end):
        date_field = 'date'
        query_filter = {date_field: {'$gte': start, '$lt': end}}
        order = ASCENDING
        return self.db.transactions.find(query_filter).sort(date_field, order)

    def show_month(self, year, month):
        start = datetime(year, month, 1)
        end = datetime(year + int(month / 12), month % 12 + 1, 1)
        transactions = self._get_transactions(start, end)
        budgets = self._get_budgets(self.rules)
        matcher = RulesMatcher(self.rules)
        self._bucket_transactions(transactions, budgets, matcher)
        self._pretty_print(start.date(), end.date() - timedelta(days=1),
                           budgets, self.nicks)
