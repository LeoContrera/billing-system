/**
 * Calculator Module - Cálculos simples en POS
 *
 * Responsabilidades:
 * - Cálculos de subtotales, totales, pagos
 * - Formateo de moneda
 * - Validaciones simples (puede finalizar, etc.)
 *
 * IMPORTANTE: Este módulo NO contiene lógica de negocio.
 * Solo realiza cálculos aritméticos simples basados en datos del backend.
 * Los cálculos aquí son SOLO para display en UI.
 */
function createCalculatorModule() {
    return {
        /**
         * Calculate gross subtotal (without discounts).
         */
        calculateGrossSubtotal(lineItems) {
            return lineItems.reduce((sum, item) => sum + (item.quantity * item.unitPrice), 0);
        },

        /**
         * Calculate sum of unit discounts.
         */
        calculateUnitDiscounts(lineItems) {
            return lineItems.reduce((sum, item) => sum + (item.discountAmount || 0), 0);
        },

        /**
         * Calculate subtotal (after unit discounts).
         */
        calculateSubtotal(lineItems) {
            return lineItems.reduce((sum, item) => sum + item.subtotal, 0);
        },

        /**
         * Calculate total (after all discounts).
         */
        calculateTotal(lineItems, globalDiscountAmount) {
            const subtotal = this.calculateSubtotal(lineItems);
            return Math.max(0, subtotal - globalDiscountAmount);
        },

        /**
         * Calculate total paid.
         */
        calculateTotalPaid(payments) {
            return payments.reduce((sum, p) => sum + parseFloat(p.amount), 0);
        },

        /**
         * Calculate remaining balance.
         */
        calculateRemaining(lineItems, globalDiscountAmount, payments) {
            return this.calculateTotal(lineItems, globalDiscountAmount) - this.calculateTotalPaid(payments);
        },

        /**
         * Check if sale can be finalized.
         */
        canFinalize(lineItems, payments, globalDiscountAmount) {
            return lineItems.length > 0 && this.calculateRemaining(lineItems, globalDiscountAmount, payments) <= 0;
        },

        /**
         * Format currency for display.
         */
        formatCurrency(value) {
            return new Intl.NumberFormat('es-AR', {
                style: 'currency',
                currency: 'ARS',
                minimumFractionDigits: 2
            }).format(value);
        }
    };
}

// Make available globally
window.createCalculatorModule = createCalculatorModule;
