from django.test import SimpleTestCase
from types import SimpleNamespace

from sales.contract_utils import (
    build_id_quota,
    formatted_contract_label,
    formatted_contract_number,
    normalize_counter_prefix,
    parse_contract_identifier,
    parse_quota_id,
    quota_contract_suffix,
    quota_display_sequence,
)


def _sale(prefix='', number=350):
    return SimpleNamespace(contract_prefix=prefix, contract_number=number)


class ContractUtilsTests(SimpleTestCase):
    def test_normalize_counter_prefix(self):
        self.assertEqual(normalize_counter_prefix(''), '')
        self.assertEqual(normalize_counter_prefix('CTR'), '')
        self.assertEqual(normalize_counter_prefix('ctr'), '')
        self.assertEqual(normalize_counter_prefix('M'), 'M')

    def test_formatted_contract_number_legacy(self):
        self.assertEqual(formatted_contract_number(_sale('', 350)), '350')

    def test_formatted_contract_number_prefixed(self):
        self.assertEqual(formatted_contract_number(_sale('M', 1)), 'M-001')
        self.assertEqual(formatted_contract_number('M-001'), 'M-001')
        self.assertEqual(formatted_contract_number('350'), '350')

    def test_formatted_contract_label(self):
        self.assertEqual(formatted_contract_label(_sale('', 350)), 'CTR350')
        self.assertEqual(formatted_contract_label(_sale('M', 1)), 'M-001')
        self.assertEqual(formatted_contract_label('CTR350'), 'CTR350')
        self.assertEqual(formatted_contract_label('350'), 'CTR350')

    def test_formatted_contract_number_none_and_raw_string(self):
        self.assertEqual(formatted_contract_number(None), '')
        self.assertEqual(formatted_contract_number('unknown'), 'unknown')

    def test_quota_contract_suffix(self):
        self.assertEqual(quota_contract_suffix(_sale('', 350)), '350')
        self.assertEqual(quota_contract_suffix(_sale('M', 1)), 'M001')

    def test_build_id_quota(self):
        self.assertEqual(build_id_quota('CI', 1, _sale('', 350)), 'CI1CTR350')
        self.assertEqual(build_id_quota('CI', 1, _sale('M', 1)), 'CI1CTRM001')

    def test_parse_quota_id(self):
        self.assertEqual(parse_quota_id('SCR10CTRM001'), {
            'prefix': 'SCR',
            'sequence': 10,
            'contract_suffix': 'CTRM001',
        })
        self.assertEqual(parse_quota_id('CI1CTR350'), {
            'prefix': 'CI',
            'sequence': 1,
            'contract_suffix': 'CTR350',
        })
        self.assertIsNone(parse_quota_id('invalid'))

    def test_quota_display_sequence(self):
        self.assertEqual(quota_display_sequence('SCR10CTRM001'), '10')
        self.assertEqual(quota_display_sequence('CI1CTRM001'), '1')
        self.assertEqual(quota_display_sequence('legacy'), 'legacy')

    def test_parse_contract_identifier(self):
        self.assertEqual(parse_contract_identifier('M-001'), ('M', 1))
        self.assertEqual(parse_contract_identifier('350'), ('', 350))
        self.assertEqual(parse_contract_identifier('CTR350'), ('', 350))
        self.assertIsNone(parse_contract_identifier(''))
        self.assertIsNone(parse_contract_identifier(None))
