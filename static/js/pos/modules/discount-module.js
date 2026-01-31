/**
 * Discount Module - Gestión de descuentos en POS
 *
 * Responsabilidades:
 * - Aplicar descuento global a venta
 * - Aplicar descuento unitario a productos seleccionados
 *
 * NO contiene lógica de negocio - todo se delega al backend.
 */
function createDiscountModule({ saleId, fetchAPI, showSuccess, showError, calculateSubtotal }) {
    return {
        // Global discount from backend
        globalDiscountAmount: 0,

        // Modal states
        showGlobalDiscountModal: false,
        showUnitDiscountModal: false,

        // Temp values for modals
        tempGlobalDiscountPercentage: 0,
        tempUnitDiscountPercentage: 0,
        selectedProductsForDiscount: [],

        /**
         * Get global discount percentage.
         */
        get globalDiscountPercentage() {
            const subtotal = calculateSubtotal();
            if (subtotal === 0) return 0;
            return (this.globalDiscountAmount / subtotal) * 100;
        },

        /**
         * Open global discount modal.
         */
        openGlobalDiscountModal() {
            this.tempGlobalDiscountPercentage = this.globalDiscountPercentage;
            this.showGlobalDiscountModal = true;
        },

        /**
         * Apply global discount.
         */
        async applyGlobalDiscount() {
            if (this.tempGlobalDiscountPercentage < 0 || this.tempGlobalDiscountPercentage > 100) return;

            const subtotal = calculateSubtotal();
            const discountAmount = subtotal * (this.tempGlobalDiscountPercentage / 100);

            try {
                const formData = new URLSearchParams();
                formData.append('sale_id', saleId);
                formData.append('discount_amount', discountAmount.toFixed(2));

                const response = await fetchAPI('/sale/discount-global/', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    this.globalDiscountAmount = data.discount_amount;
                    this.showGlobalDiscountModal = false;
                    this.tempGlobalDiscountPercentage = 0;
                    showSuccess('Descuento aplicado');
                } else {
                    showError(data.error || 'Error al aplicar descuento');
                }
            } catch (error) {
                showError('Error al aplicar descuento');
            }
        },

        /**
         * Open unit discount modal.
         */
        openUnitDiscountModal() {
            this.selectedProductsForDiscount = [];
            this.tempUnitDiscountPercentage = 0;
            this.showUnitDiscountModal = true;
        },

        /**
         * Apply unit discount to selected products.
         */
        async applyUnitDiscount(lineItems) {
            if (this.selectedProductsForDiscount.length === 0 || this.tempUnitDiscountPercentage <= 0) return;

            try {
                for (const itemId of this.selectedProductsForDiscount) {
                    const numericItemId = Number(itemId);
                    const item = lineItems.find(i => i.id === numericItemId);
                    if (!item) continue;

                    const baseAmount = item.quantity * item.unitPrice;
                    const discountAmount = baseAmount * (this.tempUnitDiscountPercentage / 100);

                    const formData = new URLSearchParams();
                    formData.append('line_item_id', itemId);
                    formData.append('discount_amount', discountAmount.toFixed(2));

                    const response = await fetchAPI('/sale/discount-item/', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();

                    if (data.success) {
                        item.discountAmount = data.item.discount_amount;
                    } else {
                        showError(data.error || 'Error al aplicar descuento');
                        return;
                    }
                }

                this.showUnitDiscountModal = false;
                this.selectedProductsForDiscount = [];
                this.tempUnitDiscountPercentage = 0;
                showSuccess('Descuentos aplicados');
            } catch (error) {
                showError('Error al aplicar descuentos');
            }
        }
    };
}

// Make available globally
window.createDiscountModule = createDiscountModule;
