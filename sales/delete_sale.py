"""Helpers for hard-deleting a pending sale and freeing its consecutive."""

from finance.models import (
    AbonoCapital,
    Collection_budget_detail,
    Incomes,
    Incomes_return,
    SolicitudRecibo,
)
from mcd_site.counter_utils import is_last_contract, rollback_contract_counter
from sales.models import Paid_comissions, Properties


def sale_delete_block_reasons(sale):
    """Return a list of human-readable reasons why the sale cannot be deleted."""
    reasons = []

    if sale.status != 'Pendiente':
        reasons.append(
            'Solo se pueden borrar contratos en estado Pendiente (Sin aprobar).'
        )

    if not is_last_contract(sale):
        reasons.append(
            'Solo se puede borrar el último consecutivo del prefijo en uso. '
            'Si hay un contrato con número mayor (aunque esté anulado), '
            'debes anular en lugar de borrar.'
        )

    if Incomes.objects.filter(sale=sale).exists():
        reasons.append('No se puede borrar un contrato con ingresos registrados.')

    if Incomes_return.objects.filter(sale=sale).exists():
        reasons.append('No se puede borrar un contrato con devoluciones registradas.')

    if SolicitudRecibo.objects.filter(sale=sale).exists():
        reasons.append(
            'No se puede borrar un contrato con solicitudes de recibo asociadas.'
        )

    if Collection_budget_detail.objects.filter(sale=sale).exists():
        reasons.append(
            'No se puede borrar un contrato incluido en un presupuesto de cartera.'
        )

    if AbonoCapital.objects.filter(sale=sale).exists():
        reasons.append(
            'No se puede borrar un contrato con abonos a capital registrados.'
        )

    if Paid_comissions.objects.filter(assign_paid__sale=sale).exists():
        reasons.append(
            'No se puede borrar un contrato con comisiones pagadas asociadas.'
        )

    return reasons


def delete_pending_sale(sale):
    """
    Hard-delete a pending last-consecutive sale, free the lot, and roll back
    the contract counter. Raises ValueError if blockers exist.
    Must be called inside transaction.atomic().
    """
    reasons = sale_delete_block_reasons(sale)
    if reasons:
        raise ValueError(reasons[0])

    # Keep values used after delete() (row gone, Python attrs remain).
    contract_number = sale.contract_number
    contract_label = sale.formatted_contract_label()
    # Ensure FK target is cached before delete.
    _ = sale.project

    prop = Properties.objects.select_for_update().get(pk=sale.property_sold_id)
    prop.state = 'Libre'
    prop.save(update_fields=['state'])

    sale.delete()
    rollback_contract_counter(sale)

    return {
        'contract_number': contract_number,
        'contract_label': contract_label,
    }
