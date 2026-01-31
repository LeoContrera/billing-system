/**
 * Payment Module - Gestión de pagos en POS
 *
 * Responsabilidades:
 * - Gestión de métodos de pago
 * - Preview de intereses (fetched from backend)
 * - Registro de pagos
 * - Eliminación de pagos
 *
 * NO contiene lógica de negocio - todo se delega al backend.
 */
function createPaymentModule({ saleId, csrfToken, paymentMethods, fetchAPI, showSuccess, showError, calculateRemaining }) {
    return {
        // Payment methods from backend
        paymentMethods: paymentMethods || [],

        // Payments from backend
        payments: [],

        // Payment modal state
        showPaymentModal: false,

        // New payment form data
        newPayment: {
            methodId: null,
            amount: 0,
            cardType: '',
            installments: 1,
            interestRate: 0,
            requiresCard: false,
            isCredit: false,
            isSubmitting: false
        },

        /**
         * Initialize default payment method.
         */
        init() {
            // Set Efectivo (id=1) as default if available, otherwise use first method
            const cashMethod = this.paymentMethods.find(pm => pm.id === 1);
            if (cashMethod) {
                this.newPayment.methodId = 1;
            } else if (this.paymentMethods.length > 0) {
                this.newPayment.methodId = this.paymentMethods[0].id;
            }
        },

        /**
         * Get selected payment method.
         */
        getSelectedPaymentMethod() {
            return this.paymentMethods.find(pm => pm.id === parseInt(this.newPayment.methodId));
        },

        /**
         * Open payment modal.
         */
        openPaymentModal() {
            this.newPayment.amount = Math.max(0, calculateRemaining());
            this.newPayment.cardType = '';
            this.newPayment.installments = 1;
            this.newPayment.interestRate = 0;
            this.newPayment.isSubmitting = false;

            // Set Efectivo (id=1) as default if available
            const cashMethod = this.paymentMethods.find(pm => pm.id === 1);
            if (cashMethod) {
                this.newPayment.methodId = 1;
            } else if (this.paymentMethods.length > 0 && !this.newPayment.methodId) {
                this.newPayment.methodId = this.paymentMethods[0].id;
            }
            this.updatePaymentMethodFlags();

            // Clear HTML preview
            const preview = document.getElementById('interest-preview');
            if(preview) preview.innerHTML = '';

            this.showPaymentModal = true;
        },

        /**
         * Close payment modal.
         */
        closePaymentModal() {
            this.showPaymentModal = false;
            const errorContainer = document.getElementById('payment-error');
            if(errorContainer) errorContainer.innerHTML = '';
        },

        /**
         * Update payment method flags based on selected method.
         */
        updatePaymentMethodFlags() {
            const pm = this.getSelectedPaymentMethod();
            if (pm) {
                this.newPayment.requiresCard = (pm.methodType === 'DEBIT' || pm.methodType === 'CREDIT');
                this.newPayment.isCredit = (pm.methodType === 'CREDIT');
            } else {
                this.newPayment.requiresCard = false;
                this.newPayment.isCredit = false;
            }
        },

        /**
         * Reset payment details when method changes.
         */
        resetPaymentDetails() {
            // Update flags first
            this.updatePaymentMethodFlags();

            // Reset values that depend on method type
            this.newPayment.cardType = '';
            this.newPayment.installments = 1;
            this.newPayment.interestRate = 0;

            // Clear HTML preview
            const preview = document.getElementById('interest-preview');
            if(preview) preview.innerHTML = '';

            // Trigger fetch if not credit (to clear or set simple preview)
            if (!this.newPayment.isCredit) {
                this.fetchInterestPreview();
            }
        },

        /**
         * Fetch interest preview from backend.
         * Backend generates HTML with calculations.
         */
        async fetchInterestPreview() {
            const amount = parseFloat(this.newPayment.amount) || 0;
            const previewContainer = document.getElementById('interest-preview');
            if (!previewContainer) return;

            if (amount <= 0) {
                previewContainer.innerHTML = '';
                return;
            }

            try {
                const params = new URLSearchParams({
                    amount: this.newPayment.amount,
                    installments: this.newPayment.installments,
                    interest_rate: this.newPayment.interestRate
                });

                // Rely entirely on Backend HTML generation for complex logic
                const response = await fetch(`/payments/preview-interest/?${params}`, {
                    headers: { 'HX-Request': 'true' }
                });

                if (response.ok) {
                    previewContainer.innerHTML = await response.text();
                }
            } catch (error) {
                console.error('Error fetching interest preview:', error);
            }
        },

        /**
         * Submit payment.
         */
        async submitPayment(event) {
            if (this.newPayment.isSubmitting) return;

            this.newPayment.isSubmitting = true;
            const errorContainer = document.getElementById('payment-error');
            if(errorContainer) errorContainer.innerHTML = '';

            try {
                const formData = new FormData(event.target);

                // Use Fetch to submit form data exactly as Django expects
                const response = await fetch('/payments/add/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                    },
                    body: formData
                });

                if (response.ok) {
                    const data = await response.json();
                    // Update UI solely based on Backend Response
                    const pm = this.getSelectedPaymentMethod();
                    const payment = {
                        id: data.transaction.id,
                        method: pm ? pm.name : 'Desconocido',
                        methodType: pm ? pm.methodType : 'OTHER',
                        amount: parseFloat(data.transaction.amount),
                        totalAmount: parseFloat(data.transaction.total_amount),
                        cardType: data.transaction.card_type || null,
                        installments: parseInt(data.transaction.installments) || 1,
                        interestRate: parseFloat(data.transaction.interest_rate) || 0
                    };

                    this.payments.push(payment);
                    this.closePaymentModal();
                    showSuccess('Pago registrado exitosamente');
                } else {
                    const text = await response.text();
                    if(errorContainer) errorContainer.innerHTML = text;
                }
            } catch (error) {
                console.error('Error submitting payment:', error);
                if(errorContainer) errorContainer.innerHTML = '<div class="text-red-600 text-sm p-3 bg-red-50 rounded-lg border border-red-200">Error de conexión. Intente nuevamente.</div>';
            }

            this.newPayment.isSubmitting = false;
        },

        /**
         * Remove payment.
         * TODO: Add backend call to delete transaction: /payments/delete/{id}
         */
        removePayment(index) {
            this.payments.splice(index, 1);
        }
    };
}

// Make available globally
window.createPaymentModule = createPaymentModule;
