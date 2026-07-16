"""Tests for reverse-desist flow in ajax_desist_sale (mocked, no DB)."""
import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, SimpleTestCase

from sales.models import Properties as PropertiesModel
from sales.models import Sales as SalesModel
from sales.views import ajax_desist_sale


@contextmanager
def _noop_atomic():
    yield


def _ajax_post(factory, sale_id, data, user=None):
    request = factory.post(
        f'/sales/ajax/desistsale/{sale_id}',
        data,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )
    request.user = user or AnonymousUser()
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    return request


class ReverseDesistTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(
            pk=1,
            is_authenticated=True,
            is_anonymous=False,
        )
        self.atomic_patcher = patch(
            'sales.views.transaction.atomic', _noop_atomic
        )
        self.atomic_patcher.start()

    def tearDown(self):
        self.atomic_patcher.stop()

    @patch('sales.views.user_check_perms', return_value=False)
    def test_reverse_requires_permission(self, _perms):
        request = _ajax_post(
            self.factory, 10, {'todo': 'reverse-desist'}, user=self.user
        )
        response = ajax_desist_sale(request, 10)
        self.assertEqual(response.status_code, 403)
        body = json.loads(response.content)
        self.assertEqual(body['type'], 'error')

    @patch('sales.views.Sales_history')
    @patch('sales.views.Properties')
    @patch('sales.views.Sales')
    @patch('sales.views.user_check_perms', return_value=True)
    def test_reverse_rejects_non_desistido(self, _perms, Sales, Properties, _hist):
        Sales.DoesNotExist = SalesModel.DoesNotExist
        Properties.DoesNotExist = PropertiesModel.DoesNotExist
        sale = MagicMock()
        sale.pk = 10
        sale.status = 'Adjudicado'
        sale.property_sold_id = 5
        Sales.objects.select_for_update.return_value.get.return_value = sale

        request = _ajax_post(
            self.factory, 10, {'todo': 'reverse-desist'}, user=self.user
        )
        response = ajax_desist_sale(request, 10)
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertIn('Desistido', body['msj'])
        sale.save.assert_not_called()

    @patch('sales.views.Sales_history')
    @patch('sales.views.Properties')
    @patch('sales.views.Sales')
    @patch('sales.views.user_check_perms', return_value=True)
    def test_reverse_rejects_occupied_lot(self, _perms, Sales, Properties, _hist):
        Sales.DoesNotExist = SalesModel.DoesNotExist
        Properties.DoesNotExist = PropertiesModel.DoesNotExist
        sale = MagicMock()
        sale.pk = 10
        sale.status = 'Desistido'
        sale.property_sold_id = 5
        sale.project = MagicMock()
        Sales.objects.select_for_update.return_value.get.return_value = sale

        prop = MagicMock()
        prop.state = 'Asignado'
        Properties.objects.select_for_update.return_value.get.return_value = prop

        Sales.objects.filter.return_value.exclude.return_value.exists.return_value = True

        request = _ajax_post(
            self.factory, 10, {'todo': 'reverse-desist'}, user=self.user
        )
        response = ajax_desist_sale(request, 10)
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertEqual(body['title'], 'Lote no disponible')
        sale.save.assert_not_called()

    @patch('sales.views.Sales_history')
    @patch('sales.views.Properties')
    @patch('sales.views.Sales')
    @patch('sales.views.user_check_perms', return_value=True)
    def test_reverse_rejects_non_libre_even_without_active_sale(
        self, _perms, Sales, Properties, _hist
    ):
        Sales.DoesNotExist = SalesModel.DoesNotExist
        Properties.DoesNotExist = PropertiesModel.DoesNotExist
        sale = MagicMock()
        sale.pk = 10
        sale.status = 'Desistido'
        sale.property_sold_id = 5
        sale.project = MagicMock()
        Sales.objects.select_for_update.return_value.get.return_value = sale

        prop = MagicMock()
        prop.state = 'Bloqueado'
        Properties.objects.select_for_update.return_value.get.return_value = prop
        Sales.objects.filter.return_value.exclude.return_value.exists.return_value = False

        request = _ajax_post(
            self.factory, 10, {'todo': 'reverse-desist'}, user=self.user
        )
        response = ajax_desist_sale(request, 10)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['title'], 'Lote no disponible')

    @patch('sales.views.messages')
    @patch('sales.views.Sales_history')
    @patch('sales.views.Properties')
    @patch('sales.views.Sales')
    @patch('sales.views.user_check_perms', return_value=True)
    def test_reverse_success_restores_status_and_lot(
        self, _perms, Sales, Properties, Sales_history, messages
    ):
        Sales.DoesNotExist = SalesModel.DoesNotExist
        Properties.DoesNotExist = PropertiesModel.DoesNotExist
        sale = MagicMock()
        sale.pk = 10
        sale.status = 'Desistido'
        sale.property_sold_id = 5
        sale.project = MagicMock()
        Sales.objects.select_for_update.return_value.get.return_value = sale

        prop = MagicMock()
        prop.state = 'Libre'
        Properties.objects.select_for_update.return_value.get.return_value = prop

        Sales.objects.filter.return_value.exclude.return_value.exists.return_value = False

        request = _ajax_post(
            self.factory, 10, {'todo': 'reverse-desist'}, user=self.user
        )
        response = ajax_desist_sale(request, 10)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sale.status, 'Adjudicado')
        self.assertEqual(prop.state, 'Asignado')
        sale.save.assert_called()
        prop.save.assert_called()
        Sales_history.objects.create.assert_called_once()
        hist_kwargs = Sales_history.objects.create.call_args.kwargs
        self.assertEqual(hist_kwargs['action'], 'Reversó el desistimiento')
        messages.success.assert_called_once()

    @patch('sales.views.Sales')
    @patch('sales.views.user_check_perms', return_value=True)
    def test_reverse_sale_not_found(self, _perms, Sales):
        Sales.DoesNotExist = SalesModel.DoesNotExist
        Sales.objects.select_for_update.return_value.get.side_effect = (
            SalesModel.DoesNotExist
        )

        request = _ajax_post(
            self.factory, 999, {'todo': 'reverse-desist'}, user=self.user
        )
        response = ajax_desist_sale(request, 999)
        self.assertEqual(response.status_code, 404)
