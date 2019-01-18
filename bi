#!venv/bin/python
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

# bi.py

from argcomplete import autocomplete
from argparse import ArgumentParser, ArgumentTypeError
from bson.json_util import dumps
from datetime import date
from libi.analyzer import Analyzer
from libi.collector import Collector
from libi.crypto import Crypto
from libi.porter import Porter
from libi.printer import Printer
from pymongo import MongoClient
from sys import stdout

ALL_TARGETS = 'everything'
DATA_TABLES = ['accounts', 'institutions', 'rules', 'transactions']
DB_NAME = 'bi'

def get_handler(client, args):
    db = getattr(client, DB_NAME)
    table = getattr(db, args.target)
    for i in table.find():
        print(i)


def delete_handler(client, args):
    print("Deleting %s .." % args.target, end='')
    stdout.flush()
    if args.target == ALL_TARGETS:
        client.drop_database(DB_NAME)
    else:
        db = getattr(client, DB_NAME)
        getattr(db, args.target).drop()
    print('. ', end='')
    Printer.color("done", True)


def export_handler(client, args):
    Porter.export_json(args.path, DB_NAME)


def import_handler(client, args):
    Porter.import_json(args.path, DB_NAME)

def load_handler(client, ags):
    Collector.load_transactions(DB_NAME)


def report_handler(client, args):
    analyzer = Analyzer(DB_NAME)
    analyzer.show_month(args.year, args.month)


if __name__ == '__main__':
    def pint(v):
        i = int(v)
        if i <= 0:
            raise ArgumentTypeError("%s is not a positive integer" % v)
        return i

    def month(v):
        i = int(v)
        if i < 1 or i > 12:
            raise ArgumentTypeError("%s is not a valid month" % v)
        return i

    today = date.today()
    cmds = [{'action': 'get', 'targets': DATA_TABLES,
             'opts': [{'name': '--limit', 'default': 10, 'type': pint,
                       'help': 'max results returned'},
                      {'name': '--filter', 'default': None, 'type': str,
                       'help': 'mongodb filter'},
                      ]},
            {'action': 'delete', 'targets': DATA_TABLES + [ALL_TARGETS],
             'opts': [{'name': '--filter', 'default': None, 'type': str,
                       'help': 'mongodb filter'},
                      ]},
            {'action': 'import', 'targets':  None,
             'opts': [{'name': 'path', 'default': 'bi-data.json', 'type': str,
                       'help': 'file path to import from'},
                      ]},
            {'action': 'load', 'targets':  ['transactions'], 'opts': []},
            {'action': 'export', 'targets':  None,
             'opts': [{'name': '--decrypt', 'default': False, 'type': bool,
                       'help': 'export sensitive data in plain text'},
                      {'name': 'path', 'default': 'bi-data.json', 'type': str,
                       'help': 'file path to export to'},
                      ]},
            {'action': 'report', 'targets':  None,
             'opts': [{'name': 'year', 'default': today.year, 'type': pint,
                       'help': 'year of report (e.g. %d)' % today.year},
                      {'name': 'month', 'default': today.month, 'type': month,
                       'help': 'month of report (e.g. %d)' % today.month},
                      ]},
            ]
    parser = ArgumentParser(description='Budget Insight')
    subparsers = parser.add_subparsers(metavar='CMD')
    for cmd in cmds:
        p = subparsers.add_parser(cmd['action'], help='%s bi data' % cmd['action'])
        if cmd.get('targets'):
            p.add_argument('target', metavar='DATA', type=str,
                           choices=cmd['targets'],
                           help="{%s}" % '|'.join(cmd['targets']))
        p.set_defaults(func=locals()[cmd['action'] + '_handler'])
        for o in cmd['opts']:
            p.add_argument(o['name'], default=o['default'], type=o['type'],
                           nargs='?', help=o['help'])
    subparsers.required = True
    autocomplete(parser)
    args = parser.parse_args()
    client = MongoClient()
    args.func(client, args)
