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

# collector.py: collect bi data

from libi.crypto import Crypto
from libi.parser import OFXParser
from libi.printer import Printer
from ofxclient import BankAccount, CreditCardAccount, Institution
from pymongo import MongoClient
from sys import stdout
from time import sleep


class OFXLoader():
    def __init__(self, dbname):
        self.crypto = Crypto(dbname)

    def _dec(self, s):
        return self.crypto.decrypt(s).decode()

    def load(self, institution, account, days=90):
        args = {'id': institution.get('fid'),
                'org': institution.get('org'),
                'url': institution.get('url'),
                'username': self._dec(institution.get('username')),
                'password': self._dec(institution.get('password')),
                'client_args': {'ofx_version': institution.get('version')},
                }
        if institution.get('cid'):
            args['client_args']['id'] = institution.get('cid')
        if institution.get('app'):
            args['client_args']['app_id'] = institution.get('app')
        if institution.get('app_version'):
            args['client_args']['app_version'] = institution.get('app_version')
        if account.get("type") == "CREDIT":
            acct = CreditCardAccount(institution=Institution(**args),
                                     number=self._dec(account.get('number')))
        else:
            acct = BankAccount(routing_number=institution.get("routing"),
                               account_type=account.get("type"),
                               institution=Institution(**args),
                               number=self._dec(account.get('number')))
        return acct.transactions(days=days)


class Collector():
    @classmethod
    def load_transactions(cls, dbname):
        client = MongoClient()
        ofx = OFXLoader(dbname)
        with client:
            db = getattr(client, dbname)
            for account in db.accounts.find({}, {"_id": 0}):
                print("Loading %s transactions .." % account["name"], end='')
                stdout.flush()
                nm = db.institutions.find_one({'name': account['institution']})
                for i in range(1, 6):
                    if i > 1:
                        print("  🡒 Retrying (attempt %s of 5) .." % i, end='')
                        stdout.flush()
                        sleep(3)
                    try:
                        cnt = cls._load_transactions(db, ofx, nm, account)
                    except Exception as e:
                        print(". %s; " % e, end='')
                        Printer.color("0 loaded", False)
                    else:
                        print(". ", end='')
                        Printer.color("%d loaded" % cnt, True)
                        break

    @staticmethod
    def _load_transactions(db, ofx, institution, account):
        source = institution.get("url")
        acname = account.get("name")
        db.transactions.delete_many({'source': source, 'account': acname})
        transactions = ofx.load(institution, account)
        transactions = OFXParser.parse(transactions)
        for transaction in transactions:
            transaction['source'] = source
            transaction['account'] = acname
            db.transactions.insert_one(transaction)
        return len(transactions)
