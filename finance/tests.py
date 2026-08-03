from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from finance.views import (
    _apply_to_balance_cache,
    _arrears_from_cache,
    _pending_from_cache,
    _zero_paid,
    apply_income,
)


def _empty_balance_cache(mora_rate=None):
    return {
        'paid_by_quota': {},
        'last_pay_by_quota': {},
        'last_only_arrears_by_quota': {},
        'mora_rate': mora_rate,
    }


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


class ApplyIncomeDefaultCuotasFuturasTests(SimpleTestCase):
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

    @patch('finance.views._load_apply_income_balance_cache', return_value=_empty_balance_cache())
    @patch('finance.views.Sales_extra_info.objects.get')
    @patch('finance.views.Credit_info.objects.filter')
    def test_simulacion_usa_cuotas_futuras_por_defecto_si_hay_excedente(
        self,
        mock_credit_filter,
        mock_sale_extra_info_get,
        mock_balance_cache,
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

    @patch('finance.views._load_apply_income_balance_cache', return_value=_empty_balance_cache())
    @patch('finance.views.Sales_extra_info.objects.get')
    @patch('finance.views.Credit_info.objects.filter')
    def test_supera_total_pendiente_usa_check_unico(
        self,
        mock_credit_filter,
        mock_sale_extra_info_get,
        mock_balance_cache,
    ):
        """Excedente sobre el saldo total debe fallar con el check único previo al loop."""
        paid_day = date(2026, 4, 6)
        q1 = self._build_quota('Q1', paid_day, 100, 100)
        q2 = self._build_quota('Q2', paid_day, 100, 100)

        mock_credit_filter.return_value = FakeCreditQuerySet([q1, q2])
        mock_sale_extra_info_get.return_value = SimpleNamespace(
            has_pending_ci_quota=lambda: False
        )

        # tipo_abono truthy evita el auto cuotas_futuras; fuerza el check de total pendiente.
        resultado = apply_income(
            None,
            apply=False,
            no_apply_data={
                'sale': 1,
                'paid_day': paid_day,
                'total_income': 250,
                'rate': Decimal('1'),
            },
            abono_capital=False,
            tipo_abono='manual',
        )
        self.assertIsInstance(resultado, dict)
        self.assertIn('error', resultado)
        self.assertIn('supera el total pendiente', resultado['error'])


class ApplyIncomeBalanceCacheParityTests(SimpleTestCase):
    """Paridad de helpers de cache vs fórmulas de Credit_info."""

    def _quota(self, pk, pay_date, capital, interest=0, others=0):
        return SimpleNamespace(
            pk=pk,
            id_quota=f'Q{pk}',
            pay_date=pay_date,
            capital=Decimal(str(capital)),
            interest=Decimal(str(interest)),
            others=Decimal(str(others)),
        )

    def test_pending_from_cache_matches_manual_formula(self):
        quota = self._quota(10, date(2026, 1, 1), capital=1000, interest=200, others=50)
        cache = {
            'paid_by_quota': {
                10: {
                    'paid_capital': Decimal('100'),
                    'paid_interest': Decimal('50'),
                    'paid_others': Decimal('0'),
                    'paid_arrears': Decimal('10'),
                }
            },
            'last_pay_by_quota': {},
            'last_only_arrears_by_quota': {},
            'mora_rate': Decimal('2'),
        }
        pending = _pending_from_cache(quota, cache)
        self.assertEqual(pending['pendient_capital'], Decimal('900'))
        self.assertEqual(pending['pendient_int'], Decimal('150'))
        self.assertEqual(pending['pendient_others'], Decimal('50'))
        self.assertEqual(pending['total_pending'], Decimal('1100'))

    def test_arrears_from_cache_zero_when_not_overdue(self):
        paid_day = date(2026, 1, 1)
        quota = self._quota(11, paid_day, capital=500, interest=0, others=0)
        cache = _empty_balance_cache(mora_rate=Decimal('3'))
        arrears = _arrears_from_cache(quota, paid_day, cache)
        self.assertEqual(arrears['days'], 0)
        self.assertEqual(arrears['r_value'], 0)

    def test_arrears_from_cache_matches_credit_info_formula(self):
        pay_date = date(2026, 1, 1)
        paid_day = date(2026, 1, 31)
        quota = self._quota(12, pay_date, capital=300000, interest=0, others=0)
        rate = Decimal('3')
        cache = _empty_balance_cache(mora_rate=rate)
        arrears = _arrears_from_cache(quota, paid_day, cache)
        days = (paid_day - pay_date).days
        expected = int(Decimal('300000') * days * (rate / 30) / 100)
        self.assertEqual(arrears['days'], days)
        self.assertEqual(arrears['r_value'], expected)

    def test_apply_to_balance_cache_updates_paid_and_dates(self):
        cache = _empty_balance_cache(mora_rate=Decimal('2'))
        quota = self._quota(13, date(2026, 1, 1), 1000, 100, 0)
        paid_day = date(2026, 2, 1)
        _apply_to_balance_cache(cache, quota, 100, 50, 0, 0, paid_day)
        paid = cache['paid_by_quota'][13]
        self.assertEqual(paid['paid_capital'], Decimal('100'))
        self.assertEqual(paid['paid_interest'], Decimal('50'))
        self.assertEqual(cache['last_pay_by_quota'][13], paid_day)

        pending = _pending_from_cache(quota, cache)
        self.assertEqual(pending['pendient_capital'], Decimal('900'))
        self.assertEqual(pending['pendient_int'], Decimal('50'))
        self.assertEqual(_zero_paid()['paid_arrears'], Decimal('0'))
