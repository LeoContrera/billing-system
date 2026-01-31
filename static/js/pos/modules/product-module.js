/**
 * Product Module - Gestión de productos en POS
 *
 * Responsabilidades:
 * - Búsqueda de productos
 * - Verificación de stock
 * - Agregar productos a venta
 * - Remover items de venta
 *
 * NO contiene lógica de negocio - todo se delega al backend.
 */
function createProductModule({ saleId, fetchAPI, showSuccess, showError }) {
    return {
        // Line items from backend
        lineItems: [],

        // Product modal state
        showProductModal: false,
        productSearch: '',
        productResults: [],
        selectedProduct: null,
        newItemQuantity: 1,
        stockInfo: null,
        productError: '',

        /**
         * Open product modal.
         */
        openProductModal() {
            this.productSearch = '';
            this.productResults = [];
            this.selectedProduct = null;
            this.newItemQuantity = 1;
            this.stockInfo = null;
            this.productError = '';
            this.showProductModal = true;
        },

        /**
         * Close product modal.
         */
        closeProductModal() {
            this.showProductModal = false;
            this.productSearch = '';
            this.productResults = [];
            this.selectedProduct = null;
            this.stockInfo = null;
            this.productError = '';
        },

        /**
         * Search products by query string.
         */
        async searchProducts() {
            if (this.productSearch.length < 1) {
                this.productResults = [];
                return;
            }
            try {
                const response = await fetchAPI(`/products/search/?q=${encodeURIComponent(this.productSearch)}`);
                const data = await response.json();
                this.productResults = data.products || [];
            } catch (error) {
                console.error('Error searching products:', error);
            }
        },

        /**
         * Select product and check stock.
         */
        async selectProduct(p) {
            this.selectedProduct = p;
            this.productResults = [];
            this.productSearch = p.name;
            this.newItemQuantity = 1;
            await this.checkStock();
        },

        /**
         * Check stock availability for selected product.
         */
        async checkStock() {
            if (!this.selectedProduct) return;
            try {
                const response = await fetchAPI(
                    `/inventory/check/${this.selectedProduct.sku}/?qty=${this.newItemQuantity}`
                );
                this.stockInfo = await response.json();
            } catch (error) {
                console.error('Error checking stock:', error);
                this.stockInfo = null;
            }
        },

        /**
         * Validate if product can be added.
         */
        canAddProduct() {
            return this.selectedProduct &&
                   this.newItemQuantity > 0 &&
                   this.stockInfo?.available;
        },

        /**
         * Add product to sale.
         */
        async addProduct() {
            if (!this.canAddProduct()) return;

            this.productError = '';

            try {
                const formData = new URLSearchParams();
                formData.append('sale_id', saleId);
                formData.append('sku', this.selectedProduct.sku);
                formData.append('quantity', this.newItemQuantity);

                const response = await fetchAPI('/sale/add-item/', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    const newItem = {
                        id: data.item.id,
                        sku: data.item.sku,
                        description: data.item.description,
                        quantity: data.item.quantity,
                        unitPrice: data.item.unitPrice,
                        discountAmount: data.item.discountAmount,
                        get subtotal() {
                            return (this.quantity * this.unitPrice) - this.discountAmount;
                        }
                    };
                    this.lineItems.push(newItem);
                    this.closeProductModal();
                    showSuccess('Producto agregado');
                } else {
                    this.productError = data.error || 'Error al agregar producto';
                }
            } catch (error) {
                this.productError = 'Error al agregar producto';
            }
        },

        /**
         * Remove line item from sale.
         * TODO: Add backend call to delete item: /sale/remove-item/{id}
         */
        removeLineItem(index) {
            this.lineItems.splice(index, 1);
        }
    };
}

// Make available globally
window.createProductModule = createProductModule;
