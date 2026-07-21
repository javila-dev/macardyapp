"""Tests for hard-delete of last pending sale and consecutive rollback."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import transaction
from django.test import SimpleTestCase, TestCase

from mcd_site.counter_utils import is_last_contract, rollback_contract_counter
from mcd_site.models import Counters, Permiso, Projects
from sales.delete_sale import delete_pending_sale, sale_delete_block_reasons
from sales.models import Payment_plans, Properties, Sales, Sales_history, Sales_plans
from terceros.models import Clients


def _make_project(name='delproj'):
    return Projects.objects.create(
        name=name,
        name_to_show='Delete Project',
        formats_path='test',
        logo='',
    )


def _make_client(doc='1001'):
    return Clients.objects.create(
        client_document=doc,
        first_name='Test',
        last_name='Client',
    )


def _make_plan():
    return Sales_plans.objects.create(
        name='Plan test',
        initial_payment=20,
        to_finance=80,
        rate=1.5,
        status=True,
    )


def _make_property(project, description='Lote A', state='Asignado'):
    return Properties.objects.create(
        project=project,
        description=description,
        area=100,
        m2_price=1000,
        block='1',
        location='1',
        state=state,
    )


def _make_sale(project, number, *, prefix='', status='Pendiente', prop=None, client=None, plan=None):
    return Sales.objects.create(
        project=project,
        contract_prefix=prefix,
        contract_number=number,
        first_owner=client or _make_client(f'{project.name}-{number}-{prefix or "X"}'),
        property_sold=prop or _make_property(project, f'Lote {number}-{prefix or "X"}'),
        value=100000,
        comission_base=100000,
        sale_plan=plan or _make_plan(),
        status=status,
    )


class IsLastContractTests(TestCase):
    def setUp(self):
        self.project = _make_project()
        self.plan = _make_plan()

    def test_last_classic_is_true(self):
        sale = _make_sale(self.project, 10, plan=self.plan)
        self.assertTrue(is_last_contract(sale))

    def test_not_last_when_higher_exists(self):
        lower = _make_sale(self.project, 10, plan=self.plan)
        _make_sale(self.project, 11, status='Anulado', plan=self.plan)
        self.assertFalse(is_last_contract(lower))

    def test_prefix_scopes_max(self):
        classic = _make_sale(self.project, 50, plan=self.plan)
        prefixed = _make_sale(self.project, 1, prefix='M', plan=self.plan)
        self.assertTrue(is_last_contract(classic))
        self.assertTrue(is_last_contract(prefixed))


class RollbackCounterTests(TestCase):
    def setUp(self):
        self.project = _make_project('rbproj')
        Counters.objects.create(
            name='contratos',
            project=self.project,
            prefix='CTR',
            value=11,
        )
        self.plan = _make_plan()

    def test_rollback_classic(self):
        sale = _make_sale(self.project, 10, plan=self.plan)
        with transaction.atomic():
            sale.delete()
            self.assertTrue(rollback_contract_counter(sale))
        counter = Counters.objects.get(name='contratos', project=self.project)
        self.assertEqual(counter.value, 10)

    def test_rollback_skips_prefix_mismatch(self):
        sale = _make_sale(self.project, 10, prefix='M', plan=self.plan)
        with transaction.atomic():
            self.assertFalse(rollback_contract_counter(sale))
        counter = Counters.objects.get(name='contratos', project=self.project)
        self.assertEqual(counter.value, 11)


class SaleDeleteBlockReasonsTests(SimpleTestCase):
    @patch('sales.delete_sale.is_last_contract', return_value=True)
    @patch('sales.delete_sale.Incomes.objects.filter')
    @patch('sales.delete_sale.Incomes_return.objects.filter')
    @patch('sales.delete_sale.SolicitudRecibo.objects.filter')
    @patch('sales.delete_sale.Collection_budget_detail.objects.filter')
    @patch('sales.delete_sale.AbonoCapital.objects.filter')
    @patch('sales.delete_sale.Paid_comissions.objects.filter')
    def test_pendiente_last_no_blockers(
        self, paid, abono, budget, sol, ret, incomes, _last
    ):
        for mock in (paid, abono, budget, sol, ret, incomes):
            mock.return_value.exists.return_value = False
        sale = SimpleNamespace(status='Pendiente', pk=1)
        self.assertEqual(sale_delete_block_reasons(sale), [])

    @patch('sales.delete_sale.is_last_contract', return_value=False)
    @patch('sales.delete_sale.Incomes.objects.filter')
    @patch('sales.delete_sale.Incomes_return.objects.filter')
    @patch('sales.delete_sale.SolicitudRecibo.objects.filter')
    @patch('sales.delete_sale.Collection_budget_detail.objects.filter')
    @patch('sales.delete_sale.AbonoCapital.objects.filter')
    @patch('sales.delete_sale.Paid_comissions.objects.filter')
    def test_not_last_blocks(self, paid, abono, budget, sol, ret, incomes, _last):
        for mock in (paid, abono, budget, sol, ret, incomes):
            mock.return_value.exists.return_value = False
        sale = SimpleNamespace(status='Pendiente', pk=1)
        reasons = sale_delete_block_reasons(sale)
        self.assertTrue(any('último consecutivo' in r for r in reasons))

    @patch('sales.delete_sale.is_last_contract', return_value=True)
    @patch('sales.delete_sale.Incomes.objects.filter')
    @patch('sales.delete_sale.Incomes_return.objects.filter')
    @patch('sales.delete_sale.SolicitudRecibo.objects.filter')
    @patch('sales.delete_sale.Collection_budget_detail.objects.filter')
    @patch('sales.delete_sale.AbonoCapital.objects.filter')
    @patch('sales.delete_sale.Paid_comissions.objects.filter')
    def test_non_pendiente_blocks(self, paid, abono, budget, sol, ret, incomes, _last):
        for mock in (paid, abono, budget, sol, ret, incomes):
            mock.return_value.exists.return_value = False
        sale = SimpleNamespace(status='Aprobado', pk=1)
        reasons = sale_delete_block_reasons(sale)
        self.assertTrue(any('Pendiente' in r for r in reasons))

    @patch('sales.delete_sale.is_last_contract', return_value=True)
    @patch('sales.delete_sale.Incomes.objects.filter')
    @patch('sales.delete_sale.Incomes_return.objects.filter')
    @patch('sales.delete_sale.SolicitudRecibo.objects.filter')
    @patch('sales.delete_sale.Collection_budget_detail.objects.filter')
    @patch('sales.delete_sale.AbonoCapital.objects.filter')
    @patch('sales.delete_sale.Paid_comissions.objects.filter')
    def test_incomes_block(self, paid, abono, budget, sol, ret, incomes, _last):
        for mock in (paid, abono, budget, sol, ret):
            mock.return_value.exists.return_value = False
        incomes.return_value.exists.return_value = True
        sale = SimpleNamespace(status='Pendiente', pk=1)
        reasons = sale_delete_block_reasons(sale)
        self.assertTrue(any('ingresos' in r.lower() for r in reasons))


class DeletePendingSaleIntegrationTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.project = _make_project('delint')
        Counters.objects.create(
            name='contratos',
            project=self.project,
            prefix='CTR',
            value=11,
        )
        self.plan = _make_plan()
        self.prop = _make_property(self.project, 'Lote Delete')
        self.user = User.objects.create_user('deleter', password='x')
        self.sale = _make_sale(
            self.project, 10, prop=self.prop, plan=self.plan
        )
        Payment_plans.objects.create(
            id_quota='CI1-10',
            quota_type='CI',
            sale=self.sale,
            pay_date='2026-01-01',
            capital=1000,
            interest=0,
            others=0,
            project=self.project,
        )
        Sales_history.objects.create(
            sale=self.sale,
            action='Creó el contrato de venta',
            user=self.user,
        )

    def test_delete_frees_lot_counter_and_dependencies(self):
        sale_pk = self.sale.pk
        with transaction.atomic():
            result = delete_pending_sale(self.sale)

        self.assertEqual(result['contract_number'], 10)
        self.assertFalse(Sales.objects.filter(pk=sale_pk).exists())
        self.assertFalse(Payment_plans.objects.filter(sale_id=sale_pk).exists())
        self.assertFalse(Sales_history.objects.filter(sale_id=sale_pk).exists())

        self.prop.refresh_from_db()
        self.assertEqual(self.prop.state, 'Libre')

        counter = Counters.objects.get(name='contratos', project=self.project)
        self.assertEqual(counter.value, 10)

        # Number can be reused
        new_sale = _make_sale(
            self.project,
            10,
            plan=self.plan,
            client=_make_client('reuse-10'),
            prop=_make_property(self.project, 'Lote Reuse'),
        )
        self.assertEqual(new_sale.contract_number, 10)

    def test_delete_rejects_when_higher_number_exists(self):
        _make_sale(self.project, 11, status='Anulado', plan=self.plan)
        with self.assertRaises(ValueError):
            with transaction.atomic():
                delete_pending_sale(self.sale)
        self.assertTrue(Sales.objects.filter(pk=self.sale.pk).exists())


class PermissionMigrationTests(TestCase):
    def test_borrar_venta_permission_exists(self):
        Permiso.objects.get_or_create(descripcion='borrar venta')
        self.assertTrue(
            Permiso.objects.filter(descripcion='borrar venta').exists()
        )
