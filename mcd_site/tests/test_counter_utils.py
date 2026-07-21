from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from mcd_site.counter_utils import (
    contract_preview,
    counter_uses_prefix,
    describe_contract_counter_change,
    is_last_contract,
    validate_contract_counter_update,
    validate_prefix_value,
    validate_receipt_counter_update,
)
from mcd_site.models import Counters, Permiso, Projects


class CounterUtilsSimpleTests(SimpleTestCase):
    def test_counter_uses_prefix(self):
        counter = SimpleNamespace(prefix='M')
        self.assertTrue(counter_uses_prefix(counter))
        counter.prefix = 'CTR'
        self.assertFalse(counter_uses_prefix(counter))

    def test_contract_preview(self):
        self.assertEqual(contract_preview(True, 'M', 1), 'M-001')
        self.assertEqual(contract_preview(False, 'CTR', 351), '351')

    def test_validate_prefix_value(self):
        self.assertEqual(validate_prefix_value('m')[0], 'M')
        self.assertIsNotNone(validate_prefix_value('123')[1])
        self.assertIsNotNone(validate_prefix_value('TOOLONG')[1])

    def test_describe_contract_counter_change_restart(self):
        project = SimpleNamespace(name_to_show='Mangata')
        previous = {'use_prefix': False, 'prefix': '', 'next_value': 351}
        result = {
            'use_prefix': True,
            'active_prefix': 'M',
            'next_value': 1,
            'can_restart_at_one': True,
        }
        message = describe_contract_counter_change(project, previous, result)
        self.assertIn('activó prefijo', message)
        self.assertIn('reinicio en 1', message)
        self.assertIn('351→1', message)


class CounterUtilsValidationTests(TestCase):
    def setUp(self):
        self.project = Projects.objects.create(
            name='testproj',
            name_to_show='Test Project',
            formats_path='test',
        )
        Counters.objects.create(
            name='contratos',
            project=self.project,
            prefix='CTR',
            value=351,
        )
        Counters.objects.create(
            name='recibos',
            project=self.project,
            prefix='',
            value=100,
        )

    @patch('mcd_site.counter_utils.max_contract_number', return_value=350)
    @patch('mcd_site.counter_utils.prefix_is_locked', return_value=False)
    def test_validate_contract_rejects_low_value(self, *_mocks):
        errors = validate_contract_counter_update(
            self.project,
            use_prefix=False,
            prefix='',
            next_value=350,
        )
        self.assertIsInstance(errors, list)
        self.assertTrue(any('debe ser mayor' in err.lower() for err in errors))

    @patch('mcd_site.counter_utils.max_contract_number', return_value=0)
    @patch('mcd_site.counter_utils.prefix_is_locked', return_value=False)
    def test_validate_contract_allows_prefix_activation(self, *_mocks):
        result = validate_contract_counter_update(
            self.project,
            use_prefix=True,
            prefix='M',
            next_value=1,
        )
        self.assertNotIsInstance(result, list)
        self.assertEqual(result['storage_prefix'], 'M')
        self.assertEqual(result['next_value'], 1)

    @patch('mcd_site.counter_utils.max_contract_number', return_value=4)
    @patch('mcd_site.counter_utils.prefix_is_locked', return_value=True)
    def test_validate_contract_blocks_prefix_change_when_locked(self, *_mocks):
        counter = Counters.objects.get(name='contratos', project=self.project)
        counter.prefix = 'M'
        counter.save()

        errors = validate_contract_counter_update(
            self.project,
            use_prefix=True,
            prefix='X',
            next_value=5,
        )
        self.assertIsInstance(errors, list)
        self.assertTrue(any('prefijo' in err.lower() for err in errors))

    @patch('mcd_site.counter_utils.max_receipt_number', return_value=99)
    def test_validate_receipt_rejects_low_value(self, _mock):
        errors = validate_receipt_counter_update(self.project, next_value=99)
        self.assertIsInstance(errors, list)
        self.assertTrue(any('recibo' in err.lower() for err in errors))


class PermissionMigrationTests(TestCase):
    def test_configurar_consecutivos_permission_exists_after_migration(self):
        Permiso.objects.get_or_create(descripcion='configurar consecutivos')
        self.assertTrue(
            Permiso.objects.filter(descripcion='configurar consecutivos').exists()
        )

    def test_is_last_contract_with_mock_sale(self):
        sale = SimpleNamespace(project='p', contract_prefix='', contract_number=10)
        with patch('mcd_site.counter_utils.max_contract_number', return_value=10):
            self.assertTrue(is_last_contract(sale))
        with patch('mcd_site.counter_utils.max_contract_number', return_value=11):
            self.assertFalse(is_last_contract(sale))
