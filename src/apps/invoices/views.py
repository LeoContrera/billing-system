"""
Views para el módulo de facturación electrónica.

Endpoints REST para crear facturas y emitir CAE.
"""

from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
import logging

from .services import InvoiceService
from .models import Invoice


logger = logging.getLogger('invoices')


@login_required
@require_http_methods(["POST"])
def create_invoice(request, sale_id):
    """
    Crea una factura desde una venta completada.

    POST /invoices/create/<sale_id>/

    Returns:
        JSON: {
            'success': True,
            'invoice_id': int,
            'receipt_type': str,
            'status': str
        }

    Errors:
        400: Validación fallida (sale no COMPLETED, ya tiene factura)
        404: Sale no encontrado
    """
    try:
        invoice = InvoiceService.create_invoice_from_sale(sale_id, request.user)
        return JsonResponse({
            'success': True,
            'invoice_id': invoice.id,
            'receipt_type': invoice.get_receipt_type_display(),
            'status': invoice.get_status_display(),
            'total_amount': str(invoice.total_amount),
            'net_taxed': str(invoice.net_taxed),
            'vat_amount': str(invoice.vat_amount)
        })
    except ValidationError as e:
        logger.warning(f"Error creando factura para sale {sale_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado creando factura para sale {sale_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@login_required
@require_http_methods(["POST"])
def emit_cae(request, invoice_id):
    """
    Emite CAE para una factura.

    POST /invoices/<invoice_id>/emit-cae/

    Returns:
        JSON: {
            'success': True,
            'cae': str,
            'cae_expiration': str,
            'display_number': str
        }

    Errors:
        400: Validación fallida (ya autorizada, error AFIP)
        404: Invoice no encontrado
    """
    try:
        invoice = InvoiceService.emit_cae(invoice_id)
        return JsonResponse({
            'success': True,
            'cae': invoice.cae,
            'cae_expiration': str(invoice.cae_expiration),
            'display_number': invoice.display_number,
            'status': invoice.get_status_display(),
            'notes': invoice.notes
        })
    except ValidationError as e:
        logger.warning(f"Error emitiendo CAE para invoice {invoice_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado emitiendo CAE para invoice {invoice_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@login_required
@require_http_methods(["POST"])
def process_sale_afip(request, sale_id):
    """
    Orquestador completo: Crear factura, emitir CAE, generar PDF y enviar email.

    POST /invoices/process-sale/<sale_id>/

    Este endpoint reemplaza el flujo de 2 pasos (create + emit_cae) por un único
    método que ejecuta todo el proceso de facturación electrónica.

    Returns:
        JSON: {
            'success': True,
            'invoice_id': int,
            'cae': str,
            'display_number': str,
            'email_sent': bool,
            'error': str (opcional - si email falló)
        }

    Errors:
        400: Validación fallida (sale no COMPLETED, error AFIP)
        404: Sale no encontrado

    Notas:
        - Si el email falla, el CAE ya fue autorizado y NO se hace rollback
        - Se retorna success=True pero email_sent=False con mensaje de error
    """
    try:
        result = InvoiceService.procesar_venta_afip(sale_id, request.user)

        response_data = {
            'success': result['success'],
            'invoice_id': result['invoice'].id,
            'receipt_type': result['invoice'].get_receipt_type_display(),
            'cae': result['cae'],
            'cae_expiration': str(result['invoice'].cae_expiration),
            'display_number': result['display_number'],
            'total_amount': str(result['invoice'].total_amount),
            'email_sent': result['email_sent']
        }

        # Si email falló, incluir mensaje de advertencia
        if result.get('error'):
            response_data['error'] = result['error']
            logger.warning(
                f"Factura {result['invoice'].id} autorizada pero email no enviado: "
                f"{result['error']}"
            )

        return JsonResponse(response_data)

    except ValidationError as e:
        logger.warning(f"Error procesando venta {sale_id} con AFIP: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado procesando venta {sale_id} con AFIP: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@login_required
def download_pdf(request, invoice_id):
    """
    Descarga el PDF de una factura autorizada.

    GET /invoices/<invoice_id>/pdf/

    Returns:
        PDF file (application/pdf) o error JSON

    Errors:
        404: Factura no encontrada
        400: Factura no autorizada
    """
    try:
        invoice = Invoice.objects.select_related('sale').get(pk=invoice_id)

        if not invoice.is_authorized:
            return JsonResponse(
                {'success': False, 'error': 'La factura no está autorizada'},
                status=400
            )

        # Generar PDF
        pdf_buffer = InvoiceService.generate_pdf(invoice)

        # Preparar respuesta
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f'Factura_{invoice.get_receipt_type_display()}_{invoice.id}_{invoice.cae}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Factura no encontrada'}, status=404)
    except Exception as e:
        logger.error(f"Error generando PDF para factura {invoice_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Error generando PDF'}, status=500)


@login_required
def invoice_details(request, invoice_id):
    """
    Obtiene detalles de una factura.

    GET /invoices/<invoice_id>/

    Returns:
        JSON: {
            'invoice_id': int,
            'receipt_type': str,
            'status': str,
            'cae': str,
            'cae_expiration': str,
            'display_number': str,
            'customer_name': str,
            'total_amount': str,
            'created_at': str
        }

    Errors:
        404: Invoice no encontrado
    """
    try:
        invoice = Invoice.objects.select_related('sale', 'afip_receipt').get(pk=invoice_id)
        return JsonResponse({
            'invoice_id': invoice.id,
            'receipt_type': invoice.get_receipt_type_display(),
            'status': invoice.get_status_display(),
            'cae': invoice.cae or '',
            'cae_expiration': str(invoice.cae_expiration) if invoice.cae_expiration else '',
            'display_number': invoice.display_number,
            'customer_name': invoice.customer_name,
            'customer_tax_id': invoice.customer_tax_id,
            'customer_tax_category': invoice.customer_tax_category,
            'net_taxed': str(invoice.net_taxed),
            'vat_amount': str(invoice.vat_amount),
            'net_untaxed': str(invoice.net_untaxed),
            'total_amount': str(invoice.total_amount),
            'created_at': invoice.created_at.isoformat(),
            'authorized_at': invoice.authorized_at.isoformat() if invoice.authorized_at else None,
            'notes': invoice.notes
        })
    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Factura no encontrada'}, status=404)
    except Exception as e:
        logger.error(f"Error obteniendo detalles de invoice {invoice_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)
