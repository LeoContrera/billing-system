/**
 * POS Application - Alpine.js Component (Refactored v2)
 *
 * ARQUITECTURA:
 * - TODO el estado vive en el objeto Alpine.js (reactivo)
 * - Los módulos proveen SOLO funciones helper (sin estado propio)
 * - Alpine.js rastrea todos los cambios automáticamente
 */
function posApp(initialData) {
    // ====================
    // SHARED UTILITIES
    // ====================

    const csrfToken = initialData.csrfToken;

    const fetchAPI = async (url, options = {}) => {
        const defaultOptions = {
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            credentials: 'same-origin'
        };
        return await fetch(url, { ...defaultOptions, ...options });
    };

    // ====================
    // ALPINE.JS DATA OBJECT
    // ====================

    return {
        // ========== CORE STATE ==========
        saleId: initialData.saleId,
        csrfToken: csrfToken,
        issuerTaxCategory: initialData.issuerTaxCategory || 'RI',
        isLoading: false,
        errorMessage: '',
        successMessage: '',

        // ========== CUSTOMER STATE ==========
        customer: initialData.customer || {
            id: null,
            fullName: '',
            taxId: '',
            taxCategory: '',
            taxCategoryDisplay: ''
        },
        customerSearch: '',
        customerResults: [],
        showCustomerResults: false,
        customerMode: 'search',
        newCustomer: {
            firstName: '',
            lastName: '',
            email: '',
            phone: '',
            locality: '',
            address: '',
            taxId: '',
            taxCategory: 'CF'
        },
        currentReceiptType: 'Ticket',

        // ========== PRODUCT STATE ==========
        lineItems: initialData.lineItems || [],
        showProductModal: false,
        productSearch: '',
        productResults: [],
        selectedProduct: null,
        newItemQuantity: 1,
        stockInfo: null,
        productError: '',

        // ========== PAYMENT STATE ==========
        paymentMethods: initialData.paymentMethods || [],
        payments: initialData.payments || [],
        showPaymentModal: false,
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

        // ========== DISCOUNT STATE ==========
        globalDiscountAmount: initialData.globalDiscountAmount || 0,
        showGlobalDiscountModal: false,
        showUnitDiscountModal: false,
        tempGlobalDiscountPercentage: 0,
        tempUnitDiscountPercentage: 0,
        selectedProductsForDiscount: [],

        // ========== INVOICE STATE ==========
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
        showInvoiceModal: false,
        showDetailsModal: false,

        // ========== INITIALIZATION ==========
        init() {
            // Set default payment method
            const cashMethod = this.paymentMethods.find(pm => pm.id === 1);
            if (cashMethod) {
                this.newPayment.methodId = 1;
            } else if (this.paymentMethods.length > 0) {
                this.newPayment.methodId = this.paymentMethods[0].id;
            }

            // Update receipt type if customer exists
            if (this.customer.id) {
                this.updateReceiptType();
            }
        },

        // ========== MESSAGE HELPERS ==========
        showError(message) {
            this.errorMessage = message;
            setTimeout(() => this.errorMessage = '', 5000);
        },

        showSuccess(message) {
            this.successMessage = message;
            setTimeout(() => this.successMessage = '', 3000);
        },

        // ========== CUSTOMER METHODS ==========
        async searchCustomers() {
            if (this.customerSearch.length < 2) {
                this.customerResults = [];
                return;
            }
            try {
                const response = await fetchAPI(`/customers/search/?q=${encodeURIComponent(this.customerSearch)}`);
                this.customerResults = await response.json();
                this.showCustomerResults = true;
            } catch (error) {
                console.error('Error searching customers:', error);
            }
        },

        async selectCustomer(c) {
            this.isLoading = true;
            try {
                const formData = new URLSearchParams();
                formData.append('sale_id', this.saleId);
                formData.append('customer_id', c.id);

                const response = await fetchAPI('/sale/set-customer/', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    this.customer = {
                        id: c.id,
                        fullName: c.full_name,
                        taxId: c.tax_id || '',
                        taxCategory: c.tax_category || '',
                        taxCategoryDisplay: c.tax_category_display || ''
                    };
                    this.customerSearch = '';
                    this.customerResults = [];
                    this.showCustomerResults = false;
                    await this.updateReceiptType();
                    this.showSuccess('Cliente asignado');
                } else {
                    this.showError(data.error || 'Error al asignar cliente');
                }
            } catch (error) {
                this.showError('Error al asignar cliente');
            }
            this.isLoading = false;
        },

        clearCustomer() {
            this.customer = {
                id: null,
                fullName: '',
                taxId: '',
                taxCategory: '',
                taxCategoryDisplay: ''
            };
            this.customerMode = 'search';
            this.newCustomer = {
                firstName: '',
                lastName: '',
                email: '',
                phone: '',
                locality: '',
                address: '',
                taxId: '',
                taxCategory: 'CF'
            };
            this.currentReceiptType = 'Ticket';
        },

        canCreateCustomer() {
            if (!this.newCustomer.firstName.trim() || !this.newCustomer.lastName.trim()) return false;
            if (!this.newCustomer.email.trim()) return false;
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(this.newCustomer.email)) return false;
            if ((this.newCustomer.taxCategory === 'RI' || this.newCustomer.taxCategory === 'MT') && !this.newCustomer.taxId.trim()) return false;
            return true;
        },

        async createCustomer() {
            if (!this.canCreateCustomer()) return;
            this.isLoading = true;
            try {
                const formData = new URLSearchParams();
                formData.append('first_name', this.newCustomer.firstName);
                formData.append('last_name', this.newCustomer.lastName);
                formData.append('email', this.newCustomer.email);
                formData.append('phone', this.newCustomer.phone);
                formData.append('locality', this.newCustomer.locality);
                formData.append('address', this.newCustomer.address);
                formData.append('tax_category', this.newCustomer.taxCategory);
                formData.append('tax_id', this.newCustomer.taxId);

                const response = await fetchAPI('/customers/create/', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    const assignFormData = new URLSearchParams();
                    assignFormData.append('sale_id', this.saleId);
                    assignFormData.append('customer_id', data.customer.id);

                    const assignResponse = await fetchAPI('/sale/set-customer/', {
                        method: 'POST',
                        body: assignFormData
                    });

                    if (assignResponse.ok) {
                        this.customer = {
                            id: data.customer.id,
                            fullName: data.customer.full_name,
                            taxId: data.customer.tax_id || '',
                            taxCategory: data.customer.tax_category,
                            taxCategoryDisplay: data.customer.tax_category_display
                        };
                        this.newCustomer = {
                            firstName: '',
                            lastName: '',
                            email: '',
                            phone: '',
                            locality: '',
                            address: '',
                            taxId: '',
                            taxCategory: 'CF'
                        };
                        this.customerMode = 'search';
                        await this.updateReceiptType();
                        this.showSuccess('Cliente creado y asignado');
                    }
                } else {
                    this.showError(data.error || 'Error al crear cliente');
                }
            } catch (error) {
                this.showError('Error al crear cliente');
            }
            this.isLoading = false;
        },

        async updateReceiptType() {
            try {
                const customerCategory = this.customer.id
                    ? this.customer.taxCategory
                    : (this.customerMode === 'create' ? this.newCustomer.taxCategory : '');

                const hasCustomer = this.customer.id || this.customerMode === 'create';

                const params = new URLSearchParams();
                if (customerCategory) {
                    params.append('customer_tax_category', customerCategory);
                }
                params.append('customer_identified', hasCustomer ? 'true' : 'false');

                const response = await fetchAPI(`/sale/preview-receipt-type/?${params}`);
                const data = await response.json();

                this.currentReceiptType = data.receipt_type_display;
            } catch (error) {
                console.error('Error fetching receipt type:', error);
                this.currentReceiptType = 'Ticket';
            }
        },

        getTaxCategoryDisplay(category) {
            const displays = {
                'CF': 'Consumidor Final',
                'RI': 'Responsable Inscripto',
                'MT': 'Monotributo',
                'EX': 'Exento'
            };
            return displays[category] || 'Consumidor Final';
        },

        getCurrentReceiptType() {
            return this.currentReceiptType;
        },

        // ========== PRODUCT METHODS ==========
        openProductModal() {
            this.productSearch = '';
            this.productResults = [];
            this.selectedProduct = null;
            this.newItemQuantity = 1;
            this.stockInfo = null;
            this.productError = '';
            this.showProductModal = true;
        },

        closeProductModal() {
            this.showProductModal = false;
            this.productSearch = '';
            this.productResults = [];
            this.selectedProduct = null;
            this.stockInfo = null;
            this.productError = '';
        },

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

        async selectProduct(p) {
            this.selectedProduct = p;
            this.productResults = [];
            this.productSearch = p.name;
            this.newItemQuantity = 1;
            await this.checkStock();
        },

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

        canAddProduct() {
            return this.selectedProduct &&
                   this.newItemQuantity > 0 &&
                   this.stockInfo?.available;
        },

        async addProduct() {
            if (!this.canAddProduct()) return;

            this.isLoading = true;
            this.productError = '';

            try {
                const formData = new URLSearchParams();
                formData.append('sale_id', this.saleId);
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
                    this.showSuccess('Producto agregado');
                } else {
                    this.productError = data.error || 'Error al agregar producto';
                }
            } catch (error) {
                this.productError = 'Error al agregar producto';
            }
            this.isLoading = false;
        },

        removeLineItem(index) {
            this.lineItems.splice(index, 1);
        },

        // ========== CALCULATOR METHODS ==========
        calculateGrossSubtotal() {
            return this.lineItems.reduce((sum, item) => sum + (item.quantity * item.unitPrice), 0);
        },

        calculateUnitDiscounts() {
            return this.lineItems.reduce((sum, item) => sum + (item.discountAmount || 0), 0);
        },

        calculateSubtotal() {
            return this.lineItems.reduce((sum, item) => sum + item.subtotal, 0);
        },

        calculateTotal() {
            const subtotal = this.calculateSubtotal();
            return Math.max(0, subtotal - this.globalDiscountAmount);
        },

        calculateTotalPaid() {
            return this.payments.reduce((sum, p) => sum + parseFloat(p.amount), 0);
        },

        calculateRemaining() {
            return this.calculateTotal() - this.calculateTotalPaid();
        },

        canFinalize() {
            return this.lineItems.length > 0 && this.calculateRemaining() <= 0;
        },

        formatCurrency(value) {
            return new Intl.NumberFormat('es-AR', {
                style: 'currency',
                currency: 'ARS',
                minimumFractionDigits: 2
            }).format(value);
        },

        // ========== PAYMENT METHODS ==========
        getSelectedPaymentMethod() {
            return this.paymentMethods.find(pm => pm.id === parseInt(this.newPayment.methodId));
        },

        openPaymentModal() {
            this.newPayment.amount = Math.max(0, this.calculateRemaining());
            this.newPayment.cardType = '';
            this.newPayment.installments = 1;
            this.newPayment.interestRate = 0;
            this.newPayment.isSubmitting = false;

            const cashMethod = this.paymentMethods.find(pm => pm.id === 1);
            if (cashMethod) {
                this.newPayment.methodId = 1;
            } else if (this.paymentMethods.length > 0 && !this.newPayment.methodId) {
                this.newPayment.methodId = this.paymentMethods[0].id;
            }
            this.updatePaymentMethodFlags();

            const preview = document.getElementById('interest-preview');
            if(preview) preview.innerHTML = '';

            this.showPaymentModal = true;
        },

        closePaymentModal() {
            this.showPaymentModal = false;
            const errorContainer = document.getElementById('payment-error');
            if(errorContainer) errorContainer.innerHTML = '';
        },

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

        resetPaymentDetails() {
            this.updatePaymentMethodFlags();
            this.newPayment.cardType = '';
            this.newPayment.installments = 1;
            this.newPayment.interestRate = 0;

            const preview = document.getElementById('interest-preview');
            if(preview) preview.innerHTML = '';

            if (!this.newPayment.isCredit) {
                this.fetchInterestPreview();
            }
        },

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

        async submitPayment(event) {
            if (this.newPayment.isSubmitting) return;

            this.newPayment.isSubmitting = true;
            const errorContainer = document.getElementById('payment-error');
            if(errorContainer) errorContainer.innerHTML = '';

            try {
                const formData = new FormData(event.target);

                const response = await fetch('/payments/add/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.csrfToken,
                    },
                    body: formData
                });

                if (response.ok) {
                    const data = await response.json();
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
                    this.showSuccess('Pago registrado exitosamente');
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

        removePayment(index) {
            this.payments.splice(index, 1);
        },

        // ========== DISCOUNT METHODS ==========
        get globalDiscountPercentage() {
            const subtotal = this.calculateSubtotal();
            if (subtotal === 0) return 0;
            return (this.globalDiscountAmount / subtotal) * 100;
        },

        openGlobalDiscountModal() {
            this.tempGlobalDiscountPercentage = this.globalDiscountPercentage;
            this.showGlobalDiscountModal = true;
        },

        async applyGlobalDiscount() {
            if (this.tempGlobalDiscountPercentage < 0 || this.tempGlobalDiscountPercentage > 100) return;

            this.isLoading = true;
            const subtotal = this.calculateSubtotal();
            const discountAmount = subtotal * (this.tempGlobalDiscountPercentage / 100);

            try {
                const formData = new URLSearchParams();
                formData.append('sale_id', this.saleId);
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
                    this.showSuccess('Descuento aplicado');
                } else {
                    this.showError(data.error || 'Error al aplicar descuento');
                }
            } catch (error) {
                this.showError('Error al aplicar descuento');
            }
            this.isLoading = false;
        },

        openUnitDiscountModal() {
            this.selectedProductsForDiscount = [];
            this.tempUnitDiscountPercentage = 0;
            this.showUnitDiscountModal = true;
        },

        async applyUnitDiscount() {
            if (this.selectedProductsForDiscount.length === 0 || this.tempUnitDiscountPercentage <= 0) return;

            this.isLoading = true;

            try {
                for (const itemId of this.selectedProductsForDiscount) {
                    const numericItemId = Number(itemId);
                    const item = this.lineItems.find(i => i.id === numericItemId);
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
                        this.showError(data.error || 'Error al aplicar descuento');
                        this.isLoading = false;
                        return;
                    }
                }

                this.showUnitDiscountModal = false;
                this.selectedProductsForDiscount = [];
                this.tempUnitDiscountPercentage = 0;
                this.showSuccess('Descuentos aplicados');
            } catch (error) {
                this.showError('Error al aplicar descuentos');
            }
            this.isLoading = false;
        },

        // ========== INVOICE METHODS ==========
        async finalizeSale() {
            if (!this.canFinalize()) return;

            if (!confirm('¿Confirmar finalización de venta y emisión de comprobante AFIP?')) return;

            this.isLoading = true;

            try {
                const formData = new URLSearchParams();
                formData.append('sale_id', this.saleId);

                const response = await fetchAPI('/sale/finalize/', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (!data.success) {
                    this.showError(data.error || 'Error al finalizar venta');
                    this.isLoading = false;
                    return;
                }

                const afipResponse = await fetchAPI(`/invoices/process-sale/${this.saleId}/`, {
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

                    this.isLoading = false;
                    this.showInvoiceModal = true;

                    if (!afipData.email_sent && afipData.error) {
                        console.warn('Factura autorizada pero email no enviado:', afipData.error);
                    }
                } else {
                    this.showError(afipData.error || 'Error al procesar facturación AFIP');
                    this.isLoading = false;
                }
            } catch (error) {
                console.error('Error:', error);
                this.showError('Error al procesar la venta');
                this.isLoading = false;
            }
        },

        closeInvoiceModal() {
            this.showInvoiceModal = false;
            setTimeout(() => {
                window.location.href = '/sale/pos/';
            }, 300);
        },

        downloadPDF() {
            if (!this.invoice.id) {
                this.showError('No hay factura para descargar');
                return;
            }
            const url = `/invoices/${this.invoice.id}/pdf/`;
            window.open(url, '_blank');
        },

        viewDetails() {
            this.showDetailsModal = true;
        },

        closeDetailsModal() {
            this.showDetailsModal = false;
        },

        formatReceiptType(receiptType) {
            if (receiptType === 'Factura C' && !this.customer.id) {
                return 'Ticket';
            }
            return receiptType;
        }
    };
}

window.posApp = posApp;
