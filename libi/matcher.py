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

# matcher.py: match transactions against rules

from re import compile, IGNORECASE


class CompareInterface():
    def __init__(self, value):
        raise NotImplementedError('CompareInterface::__init__ '
                                  + 'must be implemented')

    def compare(self, value):
        raise NotImplementedError('CompareInterface::compare '
                                  + 'must be implemented')


class LessThanCompare(CompareInterface):
    def __init__(self, value):
        self.value = value

    def compare(self, value):
        return value < self.value


class LessThanEqualsCompare(CompareInterface):
    def __init__(self, value):
        self.value = value

    def compare(self, value):
        return value <= self.value


class GreaterThanCompare(CompareInterface):
    def __init__(self, value):
        self.value = value

    def compare(self, value):
        return value > self.value


class GreaterThanEqualsCompare(CompareInterface):
    def __init__(self, value):
        self.value = value

    def compare(self, value):
        return value >= self.value


class EqualsCompare(CompareInterface):
    def __init__(self, value):
        self.value = value

    def compare(self, value):
        return value == self.value


class NotEqualsCompare(CompareInterface):
    def __init__(self, value):
        self.value = value

    def compare(self, value):
        return value != self.value


class MatchesCompare(CompareInterface):
    def __init__(self, value):
        self.pattern = compile(value, IGNORECASE)

    def compare(self, value):
        if not value:
            return False
        m = self.pattern.search(value)
        if m and m.group(0):
            return True
        return False


class NotMatchesCompare(CompareInterface):
    def __init__(self, value):
        self.pattern = compile(value, IGNORECASE)

    def compare(self, value):
        if not value:
            return False
        m = self.pattern.search(value)
        if m and m.group(0):
            return False
        return True


class ContainsAnyCompare(CompareInterface):
    def __init__(self, value):
        self.value = value

    def compare(self, value):
        if not value:
            return False
        for v in self.value:
            if v in value:
                return True
        return False


class ContainsAllCompare(CompareInterface):
    def __init__(self, value):
        self.value = value

    def compare(self, value):
        if not value:
            return False
        for v in self.value:
            if v not in value:
                return False
        return True


class ContainsNoneCompare(CompareInterface):
    def __init__(self, value):
        self.value = value

    def compare(self, value):
        if not value:
            return False
        for v in self.value:
            if v in value:
                return False
        return True


class RulesMatcher():
    op_map = {'<':  LessThanCompare,
              '<=': LessThanEqualsCompare,
              '>':  GreaterThanCompare,
              '>=': GreaterThanEqualsCompare,
              '=': EqualsCompare,
              '!=': NotEqualsCompare,
              '~':  MatchesCompare,
              '!~': NotMatchesCompare,
              'in':  ContainsAnyCompare,
              '?':  ContainsAllCompare,
              '!?': ContainsNoneCompare,
              }

    def __init__(self, rules):
        self.rules = rules
        for rule in self.rules:
            methods = []
            for condition in rule.get("match-criteria"):
                m = self._get_match_methods(condition)
                methods.append(m)
            rule["match-method"] = self._compose_methods(methods)

    @classmethod
    def _supported_mapper_types(cls):
        return ("Supported operators: %s." % ', '.join(cls.compare_map.keys()))

    @staticmethod
    def _compose_methods(methods):
        def rule(transaction):
            # (A and B and ..) or (x and y and ..) or ..
            for group in methods:
                match = False
                for method in group:
                    match = method(transaction)
                    if not match:
                        break
                if match:
                    return match
            return False
        return rule

    @classmethod
    def _bind_args(cls, key, op, value):
        def method(transaction):
            return cls.op_map.get(op)(value).compare(transaction.get(key))
        return method

    def _get_match_methods(self, match_criteria):
        methods = []
        for c in match_criteria:
            op = c.get("op")
            if not op:
                raise KeyError("Invalid operator '%s'. %s" %
                               (op, self._supported_mapper_types()))
            methods.append(self._bind_args(c.get("key"), op, c.get("value")))
        return methods

    def get_first_matching_rule(self, transaction):
        for rule in self.rules:
            if rule.get("match-method")(transaction):
                return rule
        return None

    def get_matching_rules(self, transaction):
        rules = []
        for rule in self.rules:
            if rule.get("match-method")(transaction):
                rules.append(rule)
        return rules
