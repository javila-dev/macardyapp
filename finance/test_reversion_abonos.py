"""
Tests para la funcionalidad de reversión de abonos a capital

Este archivo contiene tests para identificar y prevenir errores en:
1. preview_reversion_abono - Validación de preview
2. revertir_abono_capital - Ejecución de reversión
3. Re-aplicación de abonos y recibos posteriores
"""

import pytest
from unittest.mock import MagicMock, patch, call
from decimal import Decimal
from datetime import date, datetime, timedelta
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.http import JsonResponse
import json

# Marcar todos los tests para usar la base de datos
pytestmark = pytest.mark.django_db


class TestPreviewReversionAbono(TestCase):
    """
    Tests para la función preview_reversion_abono

    Posibles errores a validar:
    1. Abono no existe
    2. No hay backup anterior
    3. Backup existe pero está corrupto
    4. Error al calcular saldos
    5. Permisos incorrectos
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    @patch('finance.views.AbonoCapital')
    @patch('finance.views.backup_payment_plans')
    def test_preview_sin_backup(self, mock_backup, mock_abono_model):
        """
        ERROR POTENCIAL 1: No existe backup anterior al abono

        Escenario:
        - El abono fue el primero creado en la venta
        - No hay backup anterior

        Resultado esperado:
        - Debe retornar can_revert: False con mensaje apropiado
        """
        # Setup
        from finance.views import preview_reversion_abono

        mock_abono = MagicMock()
        mock_abono.id = 1
        mock_abono.fecha = date(2025, 1, 15)
        mock_abono.sale.contract_number = 100

        mock_abono_model.objects.get.return_value = mock_abono

        # No hay backup
        mock_backup.objects.filter.return_value.values.return_value.distinct.return_value.order_by.return_value.first.return_value = None

        request = self.factory.get('/test')
        request.user = self.user

        # Execute
        response = preview_reversion_abono(request, 'test_project', 1)

        # Assert
        data = json.loads(response.content)
        assert data['can_revert'] is False
        assert 'no_backup' in data.get('error_type', '')
        print("✓ Test 1: Manejo correcto cuando no existe backup")

    @patch('finance.views.AbonoCapital')
    @patch('finance.views.backup_payment_plans')
    @patch('finance.views.Payment_plans')
    def test_preview_con_plan_vacio(self, mock_payment_plans, mock_backup, mock_abono_model):
        """
        ERROR POTENCIAL 2: Plan de pagos actual está vacío

        Escenario:
        - Existe backup
        - Plan actual no tiene cuotas (corrupto o eliminado)

        Resultado esperado:
        - Debe manejar el caso sin crash
        """
        from finance.views import preview_reversion_abono

        mock_abono = MagicMock()
        mock_abono.fecha = date(2025, 1, 15)
        mock_abono.income.receipt = 'REC001'
        mock_abono.capital_aplicado = 5000000
        mock_abono.get_tipo_display.return_value = 'Reducir tiempo'
        mock_abono.cuotas_afectadas = 5
        mock_abono.sale.first_owner.full_name.return_value = 'Juan Pérez'
        mock_abono.sale.contract_number = 100

        mock_abono_model.objects.get.return_value = mock_abono

        # Simular backup existe
        mock_backup.objects.filter.return_value.values.return_value.distinct.return_value.order_by.return_value.first.return_value = {
            'backup_date': datetime(2025, 1, 10)
        }

        # Simular cuotas backup
        mock_cuota_backup = MagicMock()
        mock_cuota_backup.capital = 1000000
        mock_cuota_backup.interest = 100000
        mock_cuota_backup.quota_type = 'SCR'
        mock_backup.objects.filter.return_value = [mock_cuota_backup]

        # Plan actual VACÍO
        mock_payment_plans.objects.filter.return_value = []
        mock_payment_plans.objects.filter.return_value.count.return_value = 0
        mock_payment_plans.objects.filter.return_value.filter.return_value.count.return_value = 0
        mock_payment_plans.objects.filter.return_value.values.return_value.distinct.return_value = []

        request = self.factory.get('/test')
        request.user = self.user

        # Execute
        try:
            response = preview_reversion_abono(request, 'test_project', 1)
            data = json.loads(response.content)
            assert 'actual' in data
            assert data['actual']['total_cuotas'] == 0
            print("✓ Test 2: Manejo correcto de plan vacío")
        except Exception as e:
            pytest.fail(f"No debe lanzar excepción con plan vacío: {e}")


class TestRevertirAbonoCapital(TestCase):
    """
    Tests para la función revertir_abono_capital

    Posibles errores a validar:
    1. Motivo vacío
    2. No hay backup para restaurar
    3. Error al re-aplicar abonos posteriores
    4. Error al re-aplicar recibos posteriores
    5. Rollback en caso de error
    6. Inconsistencia en fechas de abonos
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    @patch('finance.views.AbonoCapital')
    def test_reversion_sin_motivo(self, mock_abono_model):
        """
        ERROR POTENCIAL 3: Usuario no proporciona motivo

        Resultado esperado:
        - Debe retornar error pidiendo el motivo
        """
        from finance.views import revertir_abono_capital

        request = self.factory.post('/test', {'motivo': ''})
        request.user = self.user

        response = revertir_abono_capital(request, 'test_project', 1)
        data = json.loads(response.content)

        assert data['status'] == 'error'
        assert 'motivo' in data['message'].lower()
        print("✓ Test 3: Validación correcta de motivo obligatorio")

    @patch('finance.views.AbonoCapital')
    @patch('finance.views.backup_payment_plans')
    def test_reversion_sin_backup(self, mock_backup, mock_abono_model):
        """
        ERROR POTENCIAL 4: No existe backup para restaurar

        Resultado esperado:
        - Debe retornar error sin modificar la BD
        """
        from finance.views import revertir_abono_capital

        mock_abono = MagicMock()
        mock_abono.fecha = date(2025, 1, 15)
        mock_abono.sale.project.name = 'test_project'

        mock_abono_model.objects.get.return_value = mock_abono

        # No hay backup
        mock_backup.objects.filter.return_value.values.return_value.distinct.return_value.order_by.return_value.first.return_value = None

        request = self.factory.post('/test', {'motivo': 'Error en aplicación'})
        request.user = self.user

        response = revertir_abono_capital(request, 'test_project', 1)
        data = json.loads(response.content)

        assert data['status'] == 'error'
        assert 'backup' in data['message'].lower()
        print("✓ Test 4: Manejo correcto cuando no hay backup")

    @patch('finance.views.transaction')
    @patch('finance.views.AbonoCapital')
    @patch('finance.views.backup_payment_plans')
    @patch('finance.views.Payment_plans')
    @patch('finance.views.Incomes_detail')
    @patch('finance.views.Incomes')
    @patch('finance.views.apply_income')
    def test_reversion_falla_reaplicar_abono_posterior(
        self, mock_apply_income, mock_incomes, mock_incomes_detail,
        mock_payment_plans, mock_backup, mock_abono_model, mock_transaction
    ):
        """
        ERROR POTENCIAL 5: Falla al re-aplicar un abono posterior

        Escenario:
        - Existe un abono posterior que no puede re-aplicarse con su tipo original
        - Debe intentar con 'cuotas_futuras' como fallback

        Resultado esperado:
        - Debe usar el fallback y completar la reversión exitosamente
        """
        from finance.views import revertir_abono_capital

        # Setup abono a revertir
        mock_abono = MagicMock()
        mock_abono.id = 1
        mock_abono.fecha = date(2025, 1, 15)
        mock_abono.income.receipt = 'REC001'
        mock_abono.capital_aplicado = 5000000
        mock_abono.get_tipo_display.return_value = 'Reducir tiempo'
        mock_abono.sale.project.name = 'test_project'
        mock_abono.sale.contract_number = 100

        mock_abono_model.objects.get.return_value = mock_abono

        # Simular abono posterior
        mock_abono_model.objects.filter.return_value.order_by.return_value.values.return_value = [
            {'income_id': 2, 'tipo': 'reducir_cuota', 'capital_aplicado': 3000000}
        ]

        # Simular que primer intento falla, segundo funciona
        mock_apply_income.side_effect = [
            ValueError("No se puede aplicar reducir_cuota"),  # Primera llamada falla
            None  # Segunda llamada (con cuotas_futuras) funciona
        ]

        # Simular backup
        mock_backup.objects.filter.return_value.values.return_value.distinct.return_value.order_by.return_value.first.return_value = {
            'backup_date': datetime(2025, 1, 10)
        }

        mock_cuota_backup = MagicMock()
        mock_backup.objects.filter.return_value = [mock_cuota_backup]

        # Mock transaction.atomic
        mock_transaction.atomic.return_value.__enter__ = MagicMock()
        mock_transaction.atomic.return_value.__exit__ = MagicMock(return_value=False)

        request = self.factory.post('/test', {'motivo': 'Corrección de error'})
        request.user = self.user

        # Execute
        response = revertir_abono_capital(request, 'test_project', 1)

        # Assert - debe haber intentado dos veces
        assert mock_apply_income.call_count == 2
        print("✓ Test 5: Fallback correcto al re-aplicar abonos posteriores")

    @patch('finance.views.transaction')
    @patch('finance.views.AbonoCapital')
    @patch('finance.views.backup_payment_plans')
    @patch('finance.views.Payment_plans')
    @patch('finance.views.Incomes_detail')
    @patch('finance.views.Incomes')
    @patch('finance.views.apply_income')
    def test_reversion_falla_reaplicar_recibo_monto_excesivo(
        self, mock_apply_income, mock_incomes, mock_incomes_detail,
        mock_payment_plans, mock_backup, mock_abono_model, mock_transaction
    ):
        """
        ERROR POTENCIAL 6: Recibo posterior no cabe en el plan restaurado

        Escenario:
        - Existe un recibo posterior con valor muy grande
        - No cabe en las cuotas pendientes después de restaurar
        - Debe aplicarse como abono a capital

        Resultado esperado:
        - Debe detectar el error y aplicar como abono a cuotas_futuras
        """
        from finance.views import revertir_abono_capital

        # Setup similar al test anterior
        mock_abono = MagicMock()
        mock_abono.id = 1
        mock_abono.fecha = date(2025, 1, 15)
        mock_abono.income.receipt = 'REC001'
        mock_abono.capital_aplicado = 5000000
        mock_abono.get_tipo_display.return_value = 'Reducir tiempo'
        mock_abono.sale.project.name = 'test_project'
        mock_abono.sale.contract_number = 100

        mock_abono_model.objects.get.return_value = mock_abono

        # No hay abonos posteriores
        mock_abono_model.objects.filter.return_value.order_by.return_value.values.return_value = []
        mock_abono_model.objects.filter.return_value.values_list.return_value = []

        # Simular recibo posterior
        mock_incomes.objects.filter.return_value.exclude.return_value.order_by.return_value.values_list.return_value = [3]

        mock_income = MagicMock()
        mock_incomes.objects.get.return_value = mock_income

        # Primera llamada falla por valor excesivo, segunda funciona como abono
        mock_apply_income.side_effect = [
            ValueError("El valor supera el saldo pendiente"),
            None  # Segunda llamada (como abono) funciona
        ]

        # Simular backup
        mock_backup.objects.filter.return_value.values.return_value.distinct.return_value.order_by.return_value.first.return_value = {
            'backup_date': datetime(2025, 1, 10)
        }

        mock_cuota_backup = MagicMock()
        mock_backup.objects.filter.return_value = [mock_cuota_backup]

        # Mock transaction.atomic
        mock_transaction.atomic.return_value.__enter__ = MagicMock()
        mock_transaction.atomic.return_value.__exit__ = MagicMock(return_value=False)

        request = self.factory.post('/test', {'motivo': 'Corrección'})
        request.user = self.user

        # Execute
        response = revertir_abono_capital(request, 'test_project', 1)

        # Assert
        assert mock_apply_income.call_count == 2
        # Verificar que segunda llamada tiene abono_capital=True
        second_call = mock_apply_income.call_args_list[1]
        assert second_call[1]['abono_capital'] is True
        assert second_call[1]['tipo_abono'] == 'cuotas_futuras'
        print("✓ Test 6: Fallback correcto para recibos que no caben")


class TestEdgeCasesReversion(TestCase):
    """
    Tests para casos especiales y edge cases
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    @patch('finance.views.AbonoCapital')
    @patch('finance.views.backup_payment_plans')
    def test_multiples_abonos_mismo_dia(self, mock_backup, mock_abono_model):
        """
        ERROR POTENCIAL 7: Múltiples abonos en la misma fecha

        Escenario:
        - Hay varios abonos aplicados el mismo día
        - Revertir uno del medio

        Resultado esperado:
        - Solo debe revertir el seleccionado
        - Los demás del mismo día deben re-aplicarse correctamente
        """
        from finance.views import preview_reversion_abono

        # Abono a revertir
        mock_abono = MagicMock()
        mock_abono.id = 2
        mock_abono.fecha = date(2025, 1, 15)
        mock_abono.income.receipt = 'REC002'
        mock_abono.capital_aplicado = 3000000
        mock_abono.get_tipo_display.return_value = 'Reducir cuota'
        mock_abono.cuotas_afectadas = 3
        mock_abono.sale.first_owner.full_name.return_value = 'María López'
        mock_abono.sale.contract_number = 200

        mock_abono_model.objects.get.return_value = mock_abono

        # Abonos posteriores (incluyendo mismo día)
        mock_abono_model.objects.filter.return_value.count.return_value = 2

        # Simular backup
        mock_backup.objects.filter.return_value.values.return_value.distinct.return_value.order_by.return_value.first.return_value = {
            'backup_date': datetime(2025, 1, 14)
        }

        mock_cuota_backup = MagicMock()
        mock_cuota_backup.capital = 1500000
        mock_cuota_backup.interest = 150000
        mock_cuota_backup.quota_type = 'SCR'
        mock_backup.objects.filter.return_value = [mock_cuota_backup]

        request = self.factory.get('/test')
        request.user = self.user

        # Execute
        response = preview_reversion_abono(request, 'test_project', 2)
        data = json.loads(response.content)

        # Assert
        assert data['can_revert'] is True
        assert data['abonos_posteriores'] == 2  # Los otros del mismo día
        print("✓ Test 7: Manejo correcto de múltiples abonos mismo día")

    @patch('finance.views.AbonoCapital')
    @patch('finance.views.backup_payment_plans')
    @patch('finance.views.Payment_plans')
    def test_backup_con_datos_corruptos(self, mock_payment_plans, mock_backup, mock_abono_model):
        """
        ERROR POTENCIAL 8: Backup tiene datos inconsistentes

        Escenario:
        - Backup existe pero tiene valores negativos o null

        Resultado esperado:
        - Debe manejar valores None/null sin crash
        """
        from finance.views import preview_reversion_abono

        mock_abono = MagicMock()
        mock_abono.fecha = date(2025, 1, 15)
        mock_abono.income.receipt = 'REC003'
        mock_abono.capital_aplicado = 2000000
        mock_abono.get_tipo_display.return_value = 'Cuotas futuras'
        mock_abono.cuotas_afectadas = 2
        mock_abono.sale.first_owner.full_name.return_value = 'Pedro García'
        mock_abono.sale.contract_number = 300

        mock_abono_model.objects.get.return_value = mock_abono

        # Simular backup con datos problemáticos
        mock_backup.objects.filter.return_value.values.return_value.distinct.return_value.order_by.return_value.first.return_value = {
            'backup_date': datetime(2025, 1, 10)
        }

        # Cuota con valores None
        mock_cuota_corrupta = MagicMock()
        mock_cuota_corrupta.capital = None  # Valor corrupto
        mock_cuota_corrupta.interest = 0
        mock_cuota_corrupta.quota_type = 'SCR'

        mock_cuota_normal = MagicMock()
        mock_cuota_normal.capital = 1000000
        mock_cuota_normal.interest = 100000
        mock_cuota_normal.quota_type = 'SCR'

        mock_backup.objects.filter.return_value = [mock_cuota_corrupta, mock_cuota_normal]

        request = self.factory.get('/test')
        request.user = self.user

        # Execute
        try:
            response = preview_reversion_abono(request, 'test_project', 3)
            # Si llega aquí, maneja el error (puede retornar error o manejar None)
            print("✓ Test 8: Manejo de datos corruptos sin crash")
        except TypeError as e:
            pytest.fail(f"No debe crashear con datos None: {e}")


# ============================================================================
# REPORTE DE ERRORES POTENCIALES IDENTIFICADOS
# ============================================================================

"""
RESUMEN DE ERRORES POTENCIALES EN LA FUNCIÓN DE REVERSIÓN:

1. ❌ NO VALIDADO: Permisos de usuario
   - Línea: revertir_abono_capital (línea 3826)
   - Problema: No verifica si el usuario tiene permiso para revertir abonos
   - Solución: Agregar decorador de permisos o validación explícita

2. ⚠️  PARCIALMENTE MANEJADO: Re-aplicación de abonos posteriores con tipo diferente
   - Líneas: 3915-3929
   - Problema: Si falla con tipo original, intenta con 'cuotas_futuras'
   - Mejora: Podría loggear este cambio de tipo para auditoría

3. ⚠️  PARCIALMENTE MANEJADO: Re-aplicación de recibos que no caben
   - Líneas: 3934-3946
   - Problema: Detecta error por monto excesivo pero solo busca "supera" o "futuras"
   - Mejora: Hacer la detección más robusta

4. ❌ POSIBLE PROBLEMA: Orden de re-aplicación de abonos y recibos
   - Líneas: 3872-3882
   - Problema: Los recibos posteriores excluyen los que son abonos, pero qué pasa
     si hay un recibo NO-abono entre dos abonos? El orden podría ser incorrecto.
   - Solución: Combinar abonos y recibos en una sola lista ordenada por fecha

5. ❌ NO VALIDADO: Integridad referencial
   - Líneas: 3885-3891
   - Problema: Elimina Payment_plans, Incomes_detail y AbonoCapital sin verificar
     si hay referencias en otras tablas (ej: pagos de comisión)
   - Solución: Validar que no haya comisión pagada antes de permitir reversión

6. ⚠️  POSIBLE RACE CONDITION: Fechas auto_now_add
   - Línea: 3848 (backup_date__lt=abono.fecha)
   - Problema: AbonoCapital.fecha usa auto_now_add, podría haber microsegundos
     de diferencia causando que backup se cree "después" del abono
   - Solución: Usar __lte en lugar de __lt, o agregar margen de tiempo

7. ❌ NO MANEJADO: Comisión ya pagada
   - No hay validación
   - Problema: Si se revierte un abono con comisión pagada, se pierde el registro
   - Solución: Prevenir reversión si hay comisión pagada, o revertir también la comisión

8. ⚠️  FALTA LOGGING: Errores silenciosos en re-aplicación
   - Líneas: 3922-3929
   - Problema: El fallback captura excepciones pero no las registra
   - Solución: Loggear cuando se usa fallback para debugging

9. ❌ POSIBLE INCONSISTENCIA: Restauración de cuotas ABCAP
   - Líneas: 3894-3910
   - Problema: Al restaurar desde backup, las cuotas ABCAP restauradas tendrán
     códigos con sale.pk si fueron creadas antes del fix
   - Solución: Recalcular id_quota para cuotas ABCAP usando contract_number

10. ⚠️  VALIDACIÓN DÉBIL: Motivo de reversión
    - Línea: 3834
    - Problema: Solo valida que no esté vacío, pero acepta cualquier texto
    - Mejora: Validar longitud mínima o formato

PRIORIDADES DE CORRECCIÓN:
1. ALTA: Validar comisión pagada (#7)
2. ALTA: Verificar orden de re-aplicación (#4)
3. MEDIA: Recalcular códigos ABCAP al restaurar (#9)
4. MEDIA: Agregar logging de fallbacks (#8)
5. BAJA: Mejorar validación de motivo (#10)
"""


def print_error_summary():
    """Imprime resumen de errores para revisión"""
    print("\n" + "="*80)
    print("ANÁLISIS DE ERRORES POTENCIALES - REVERSIÓN DE ABONOS A CAPITAL")
    print("="*80)

    errores = [
        ("CRÍTICO", "No valida si comisión ya fue pagada antes de revertir"),
        ("CRÍTICO", "Orden de re-aplicación podría ser incorrecto (abonos vs recibos)"),
        ("ALTO", "Cuotas ABCAP restauradas podrían tener códigos incorrectos"),
        ("MEDIO", "Falta logging cuando se usa fallback en re-aplicación"),
        ("MEDIO", "Detección de error 'monto excesivo' es frágil (busca texto)"),
        ("BAJO", "Validación de motivo es muy simple"),
        ("BAJO", "No hay validación explícita de permisos de usuario"),
        ("INFO", "Posible race condition con auto_now_add en fechas"),
    ]

    for i, (nivel, error) in enumerate(errores, 1):
        print(f"\n{i}. [{nivel}] {error}")

    print("\n" + "="*80)
    print("RECOMENDACIÓN: Ejecutar tests y revisar casos críticos antes de producción")
    print("="*80 + "\n")


if __name__ == '__main__':
    print_error_summary()
