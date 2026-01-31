/**
 * Invoice Module - Finalización de venta y facturación
 *
 * Responsabilidades:
 * - Finalizar venta
 * - Procesar facturación AFIP
 * - Gestionar modal de factura generada
 * - Descargar PDF de factura
 * - Ver detalles de venta
 *
 * NO contiene lógica de negocio - todo se delega al backend.
 */
function createInvoiceModule({ saleId, fetchAPI, showError }) {
    return {
        // Invoice data from backend
        invoice: {
            id: null,
            receiptType: '',
            cae: '',
            caeExpiration: '',
            displayNumber: '',
            totalAmount: 0,
            emailSent: false,
            emailError: ''
        },

        // Modal states
        showInvoiceModal: false,
        showDetailsModal: false,

        /**
         * Finalize sale and process AFIP invoice.
         */
        async finalizeSale(canFinalize) {
            if (!canFinalize()) return;

            if (!confirm('¿Confirmar finalización de venta y emisión de comprobante AFIP?')) return;

            try {
                // Step 1: Finalize sale
                const formData = new URLSearchParams();
                formData.append('sale_id', saleId);

                const response = await fetchAPI('/sale/finalize/', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (!data.success) {
                    showError(data.error || 'Error al finalizar venta');
                    return;
                }

                // Step 2: Process AFIP
                const afipResponse = await fetchAPI(`/invoices/process-sale/${saleId}/`, {
                    method: 'POST'
                });

                const afipData = await afipResponse.json();

                if (afipData.success) {
                    this.invoice = {
                        id: afipData.invoice_id,
                        receiptType: afipData.receipt_type,
                        cae: afipData.cae,
                        caeExpiration: afipData.cae_expiration,
                        displayNumber: afipData.display_number,
                        totalAmount: parseFloat(afipData.total_amount),
                        emailSent: afipData.email_sent,
                        emailError: afipData.error || ''
                    };

                    this.showInvoiceModal = true;

                    if (!afipData.email_sent && afipData.error) {
                        console.warn('Factura autorizada pero email no enviado:', afipData.error);
                    }
                } else {
                    showError(afipData.error || 'Error al procesar facturación AFIP');
                }
            } catch (error) {
                console.error('Error:', error);
                showError('Error al procesar la venta');
            }
        },

        /**
         * Close invoice modal and redirect to new sale.
         */
        closeInvoiceModal() {
            this.showInvoiceModal = false;
            setTimeout(() => {
                window.location.href = '/sale/pos/';
            }, 300);
        },

        /**
         * Download invoice PDF.
         */
        downloadPDF() {
            if (!this.invoice.id) {
                showError('No hay factura para descargar');
                return;
            }
            const url = `/invoices/${this.invoice.id}/pdf/`;
            window.open(url, '_blank');
        },

        /**
         * View sale details.
         */
        viewDetails() {
            this.showDetailsModal = true;
        },

        /**
         * Close details modal.
         */
        closeDetailsModal() {
            this.showDetailsModal = false;
        },

        /**
         * Format receipt type for display.
         */
        formatReceiptType(receiptType, hasCustomer) {
            if (receiptType === 'Factura C' && !hasCustomer) {
                return 'Ticket';
            }
            return receiptType;
        }
    };
}

// Make available globally
window.createInvoiceModule = createInvoiceModule;
