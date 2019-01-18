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

# porter.py: import and export bi data

from bson.json_util import default, loads
from json import dump
from libi.crypto import Crypto
from libi.printer import Printer
from pymongo import MongoClient
from semver import VersionInfo


class UnsupportedVersion(Exception):
    def __init__(self, provided, supported):
        self.message = (("Unsupported verion: %s. " % provided) +
                        ("Supported versions include: %s" % supported))


class InvalidSchema(Exception):
    def __init__(self, message):
        self.message = "Invalid Schema: %s" % message


class Schema():
    @staticmethod
    def correct(s):
        raise NotImplementedError("Implement me: bring into conformity")

    @staticmethod
    def decrypt(s, c):
        raise NotImplementedError("Implement me: decrypt sensitive info")

    @staticmethod
    def encrypt(s, c):
        raise NotImplementedError("Implement me: encrypt sensitive info")

    @staticmethod
    def tables():
        raise NotImplementedError("Implement me: return list(ofTables)")

    @staticmethod
    def version():
        raise NotImplementedError("Implement me: return '#.#.#'")


class V1(Schema):
    @staticmethod
    def correct(s):
        for a in s.get('accounts', []):
            a['type'] = a['type'].upper()
        return s

    @staticmethod
    def decrypt(s, c):
        for i in s.get('institutions', []):
            i['username'] = c.decrypt(i['username']).decode()
            i['password'] = c.decrypt(i['password']).decode()
        for a in s.get('accounts', []):
            a['number'] = c.decrypt(a['number']).decode()
        return s

    @staticmethod
    def encrypt(s, c):
        for i in s.get('institutions', []):
            i['username'] = c.encrypt(i['username'].encode())
            i['password'] = c.encrypt(i['password'].encode())
        for a in s.get('accounts', []):
            a['number'] = c.encrypt(a['number'].encode())
        return s

    @staticmethod
    def tables():
        return ['accounts', 'institutions', 'rules', 'transactions']

    @staticmethod
    def version():
        return '1.0.0'


class Porter():
    current = V1
    supported = [V1]

    @classmethod
    def import_json(cls, path, dbname):
        data = None
        print("Importing %s .." % path, end='')
        try:
            f = open(path)
            with f:
                data = loads(f.read())
                version = VersionInfo.parse(data.get('version', ""))
                for v in cls.supported:
                    if version <= VersionInfo.parse(v.version()):
                        data = v.correct(data)
                data['version'] = cls.current.version()
                data = cls.current.encrypt(data, Crypto(dbname))
        except Exception as e:
            print(". %s; " % e, end='')
            Printer.color("nothing imported", False)
            return
        print(".")
        client = MongoClient()
        with client:
            db = getattr(client, dbname)
            for name in cls.current.tables():
                table = getattr(db, name)
                print("  ... deleting old %s .." % name, end='')
                table.drop()
                print(". importing new %s .." % name, end='')
                records = data.get(name, [])
                for r in records:
                    table.insert_one(r)
                print('. ', end='')
                Printer.color('%d %s imported' % (len(records), name), True)

    @classmethod
    def export_json(cls, path, dbname):
        print("Exporting to %s .." % path, end='')
        data = {'version': cls.current.version()}
        try:
            client = MongoClient()
            db = getattr(client, dbname)
            with client:
                for table in cls.current.tables():
                    data[table] = []
                    for row in getattr(db, table).find({}, {'_id': 0}):
                        data[table].append(row)
            f = open(path, 'w')
            data = cls.current.decrypt(data, Crypto(dbname))
            dump(data, f, sort_keys=True, indent=2, separators=(',', ': '),
                 default=default)
        except Exception as e:
            print(". %s; " % e, end='')
            Printer.color("export failed", False)
        else:
            print(". ", end='')
            Printer.color("done", True)
