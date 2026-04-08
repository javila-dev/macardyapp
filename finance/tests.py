from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from finance.views import apply_income


class FakeCreditQuerySet:
    def __init__(self, quotas):
        self._quotas = list(quotas)

    def order_by(self, *args, **kwargs):
        return self

    def filter(self, **kwargs):
        filtered = self._quotas

        pay_date_gt = kwargs.get('pay_date__gt')
        if pay_date_gt is not None:
            filtered = [quota for quota in filtered if quota.pay_date > pay_date_gt]

        return FakeCreditQuerySet(filtered)

    def count(self):
        return len(self._quotas)

    def first(self):
        return self._quotas[0] if self._quotas else None

    def __iter__(self):
        return iter(self._quotas)


class ApplyIncomeDefaultCuotasFuturasTests(TestCase):
    def _build_quota(self, quota_id, pay_date, total_pending, capital):
        quota = SimpleNamespace(
            id_quota=quota_id,
            pay_date=pay_date,
            capital=Decimal(str(capital)),
        )
        quota.quota_pending = lambda: {
            'total_pending': Decimal(str(total_pending)),
            'pendient_capital': Decimal(str(total_pending)),
            'pendient_int': Decimal('0'),
            'pendient_others': Decimal('0'),
        }
        quota.arrears_info = lambda paid_day=None: {
            'r_value': Decimal('0'),
            'days': 0,
        }
        quota.total_payment = lambda: Decimal(str(total_pending))
        return quota

    @patch('finance.views.Sales_extra_info.objects.get')
    @patch('finance.views.Credit_info.objects.filter')
    def test_simulacion_usa_cuotas_futuras_por_defecto_si_hay_excedente(
        self,
        mock_credit_filter,
        mock_sale_extra_info_get,
    ):
        paid_day = date(2026, 4, 6)
        vencida = self._build_quota('Q1', paid_day, 100, 100)
        futura = self._build_quota('Q2', paid_day + timedelta(days=30), 200, 200)

        mock_credit_filter.return_value = FakeCreditQuerySet([vencida, futura])
        mock_sale_extra_info_get.return_value = SimpleNamespace(
            has_pending_ci_quota=lambda: False
        )

        resultado = apply_income(
            None,
            apply=False,
            no_apply_data={
                'sale': 1,
                'paid_day': paid_day,
                'total_income': 150,
                'rate': Decimal('1'),
            },
        )

        self.assertIsInstance(resultado, list)
        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0]['quota'], 'Q1')
        self.assertEqual(resultado[0]['paid_total'], 100.0)
        self.assertEqual(resultado[1]['quota'], 'Q2')
        self.assertEqual(resultado[1]['paid_total'], 50.0)
