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

# crypto.py: encrypt / decrypt sensitive bi fields

from cryptography.fernet import Fernet, InvalidToken
from getpass import getpass
from hashlib import sha512
from pymongo import MongoClient


class Crypto():
    _key = "sha"

    def __init__(self, dbname):
        self.fernet = None
        client = MongoClient()
        with client:
            db = getattr(client, dbname)
            esha = None
            try:
                esha = db.crypto.find_one().get(self._key)
            except Exception as e:
                pass
            if esha:
                self.fernet = self._get_password(self._key, esha)
            else:
                self.fernet = self._gen_password(self._key, db.crypto)

    def decrypt(self, s):
        return(self.fernet.decrypt(s))

    def encrypt(self, s):
        return(self.fernet.encrypt(s))

    @staticmethod
    def _get_password(k, esha):
        f = None
        count = 0
        while True:
            key = getpass("Enter your secret key: ")
            m = sha512()
            m.update(key.encode())
            try:
                f = Fernet(key.encode())
                if f.decrypt(esha) == m.digest():
                    break
            except (InvalidToken, ValueError) as e:
                pass
            count += 1
            print("Incorrect key entered (attempt %d of 3). " % count, end='')
            if count < 3:
                print("Please try again.")
            else:
                print("Aborting.")
                exit(1)
        return f

    @staticmethod
    def _gen_password(k, table):
        msg = """
The following key will be required to perform certain operations (i.e.
exporting or retrieving sensitive data, downloading transactions, etc.).
Please store the key somewhere safe (e.g. 1Password vault):

    %s
"""
        key = Fernet.generate_key()
        print(msg % key.decode())
        m = sha512()
        m.update(key)
        f = Fernet(key)
        table.insert_one({k: f.encrypt(m.digest())})
        return f
