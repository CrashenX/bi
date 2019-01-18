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

# printer.py: print bi data


class Printer():
    end = '\033[0m'
    yus = '\033[92m'
    bah = '\033[91m'

    @classmethod
    def color(cls, s, yus=True):
        if yus:
            print(cls.yus + s + cls.end)
        else:
            print(cls.bah + s + cls.end)
