import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import date, timedelta
from finance.views import recalcular_plan_por_abono

pytestmark = pytest.mark.django_db

@pytest.fixture
def sale():
    sale = MagicMock()
    sale.pk = 1
    sale.sale_plan.rate = 1.5
    return sale

@pytest.fixture
def income(sale):
    income = MagicMock()
    income.payment_date = date.today()
    income.sale = sale
    return income

@pytest.fixture
def payment_plan_objs():
    cuota1 = MagicMock()
    cuota1.capital = Decimal('1000')
    cuota1.pay_date = date.today() + timedelta(days=30)
    cuota1.quota_type = "SCR"
    cuota1.id_quota = "Q1"
    cuota1.total_payment.return_value = Decimal('1100')

    cuota2 = MagicMock()
    cuota2.capital = Decimal('1000')
    cuota2.pay_date = date.today() + timedelta(days=60)
    cuota2.quota_type = "SCR"
    cuota2.id_quota = "Q2"
    cuota2.total_payment.return_value = Decimal('1100')

    return [cuota1, cuota2]

@patch("sales.models.Payment_plans")
@patch("sales.models.backup_payment_plans")
@patch("finance.models.AbonoCapital")
@patch("finance.models.Incomes_detail")
def test_recalcular_plan_por_abono_reducir_tiempo(mock_incomes_detail, mock_abonocapital, mock_backup, mock_payment_plans, income, sale, payment_plan_objs):
    # Simular QuerySet
    mock_qs = MagicMock()
    mock_qs.order_by.return_value = payment_plan_objs
    mock_qs.exists.return_value = True
    mock_qs.count.return_value = len(payment_plan_objs)
    mock_qs.filter.side_effect = lambda **kwargs: payment_plan_objs

    mock_payment_plans.objects.filter.return_value = mock_qs

    recalcular_plan_por_abono(income, Decimal('500'), "reducir_tiempo")

    assert mock_backup.objects.create.called
    assert payment_plan_objs[0].save.called
    assert payment_plan_objs[1].save.called

@patch("sales.models.Payment_plans")
@patch("sales.models.backup_payment_plans")
@patch("finance.models.AbonoCapital")
@patch("finance.models.Incomes_detail")
def test_recalcular_plan_por_abono_reducir_cuota(mock_incomes_detail, mock_abonocapital, mock_backup, mock_payment_plans, income, sale, payment_plan_objs):
    cuota3 = MagicMock()
    cuota3.capital = Decimal('1000')
    cuota3.pay_date = date.today() + timedelta(days=90)
    cuota3.quota_type = "SCE"
    cuota3.id_quota = "Q3"
    cuota3.total_payment.return_value = Decimal('1100')

    cuotas = payment_plan_objs + [cuota3]

    mock_qs = MagicMock()
    mock_qs.order_by.return_value = cuotas
    mock_qs.exists.return_value = True
    mock_qs.count.return_value = len(cuotas)
    mock_qs.filter.side_effect = lambda **kwargs: [c for c in cuotas if c.quota_type in kwargs.get('quota_type__in', [])]

    mock_payment_plans.objects.filter.return_value = mock_qs

    recalcular_plan_por_abono(income, Decimal('500'), "reducir_cuota")

    assert mock_backup.objects.create.called
    assert mock_payment_plans.objects.create.called
    assert mock_abonocapital.objects.create.called
    assert mock_incomes_detail.objects.create.called

@patch("sales.models.Payment_plans")
def test_recalcular_plan_por_abono_no_cuotas(mock_payment_plans, income):
    mock_qs = MagicMock()
    mock_qs.order_by.return_value = []
    mock_qs.exists.return_value = False
    mock_payment_plans.objects.filter.return_value = mock_qs

    recalcular_plan_por_abono(income, Decimal('500'), "reducir_tiempo")
    assert mock_payment_plans.objects.create.call_count == 0
