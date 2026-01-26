/**
 * POS Application - Alpine.js Component
 * Refactored to accept initial data from Django backend
 */
function posApp(initialData) {
    return {
        // Sale ID from backend
        saleId: initialData.saleId,

        // CSRF Token
        csrfToken: initialData.csrfToken,

        // Loading and messages
        isLoading: false,
        errorMessage: '',
        successMessage: '',

        // Issuer tax category (configured in backend)
        issuerTaxCategory: initialData.issuerTaxCategory || 'RI',

        // Customer data
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
        customerMode: 'search', // 'search' or 'create'
        newCustomer: {
            firstName: '',
            lastName: '',
            email: '',
            phone: '',
            locality: '',
            address: '',
            taxId: '',
            taxCategory: 'CF'  // Default: Consumidor Final
        },

        // Line items from backend
        lineItems: initialData.lineItems || [],

        // Global discount
        globalDiscountAmount: initialData.globalDiscountAmount || 0,

        // Payments from backend
        payments: initialData.payments || [],

        // Payment methods from backend
        paymentMethods: initialData.paymentMethods || [],

        // Modal states
        showPaymentModal: false,
        showGlobalDiscountModal: false,
        showUnitDiscountModal: false,
        showProductModal: false,
        showInvoiceModal: false,

        // Invoice data
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

        // Product modal data
        productSearch: '',
        productResults: [],
        selectedProduct: null,
        newItemQuantity: 1,
        stockInfo: null,
        productError: '',

        // Payment modal data
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

        // Discount modal data
        tempGlobalDiscountPercentage: 0,
        tempUnitDiscountPercentage: 0,
        selectedProductsForDiscount: [],

        // Initialize
        init() {
            if (this.paymentMethods.length > 0) {
                this.newPayment.methodId = this.paymentMethods[0].id;
            }
        },

        // API helper
        async fetchAPI(url, options = {}) {
            const defaultOptions = {
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                credentials: 'same-origin'
            };
            const response = await fetch(url, { ...defaultOptions, ...options });
            return response;
        },

        // Show error message temporarily
        showError(message) {
            this.errorMessage = message;
            setTimeout(() => this.errorMessage = '', 5000);
        },

        // Show success message temporarily
        showSuccess(message) {
            this.successMessage = message;
            setTimeout(() => this.successMessage = '', 3000);
        },

        // Customer methods
        async searchCustomers() {
            if (this.customerSearch.length < 2) {
                this.customerResults = [];
                return;
            }
            try {
                const response = await this.fetchAPI(`/customers/search/?q=${encodeURIComponent(this.customerSearch)}`);
                this.customerResults = await response.json();
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

                const response = await this.fetchAPI('/sale/set-customer/', {
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
        },

        getCurrentReceiptType() {
            if (this.customer.id) {
                return this.determineReceiptType(this.customer.taxCategory, true);
            } else if (this.customerMode === 'create') {
                return this.determineReceiptType(this.newCustomer.taxCategory, true);
            } else {
                return this.determineReceiptType(null, false);
            }
        },

        determineReceiptType(customerCategory, hasCustomer) {
            if (this.issuerTaxCategory === 'RI') {
                if (!hasCustomer) return 'Ticket';
                if (customerCategory === 'RI') return 'Factura A';
                return 'Factura B';
            } else {
                return 'Factura C';
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

                const response = await this.fetchAPI('/customers/create/', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    const assignFormData = new URLSearchParams();
                    assignFormData.append('sale_id', this.saleId);
                    assignFormData.append('customer_id', data.customer.id);

                    const assignResponse = await this.fetchAPI('/sale/set-customer/', {
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

        // Product methods
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
                const response = await this.fetchAPI(`/products/search/?q=${encodeURIComponent(this.productSearch)}`);
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
                const response = await this.fetchAPI(
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

                const response = await this.fetchAPI('/sale/add-item/', {
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

        // Calculation methods
        calculateSubtotal() {
            return this.lineItems.reduce((sum, item) => sum + item.subtotal, 0);
        },

        calculateTotal() {
            const subtotal = this.calculateSubtotal();
            return Math.max(0, subtotal - this.globalDiscountAmount);
        },

        get globalDiscount() {
            return this.globalDiscountAmount;
        },

        get globalDiscountPercentage() {
            const subtotal = this.calculateSubtotal();
            if (subtotal === 0) return 0;
            return (this.globalDiscountAmount / subtotal) * 100;
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

        // Payment methods logic simplified for Backend interaction
        getSelectedPaymentMethod() {
            return this.paymentMethods.find(pm => pm.id === parseInt(this.newPayment.methodId));
        },

        openPaymentModal() {
            this.newPayment.amount = Math.max(0, this.calculateRemaining());
            this.newPayment.cardType = '';
            this.newPayment.installments = 1;
            this.newPayment.interestRate = 0;
            this.newPayment.isSubmitting = false;

            // Set default if available
            if (this.paymentMethods.length > 0 && !this.newPayment.methodId) {
                this.newPayment.methodId = this.paymentMethods[0].id;
            }
            this.updatePaymentMethodFlags();

            // Clear HTML preview
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
                        'X-CSRFToken': this.csrfToken,
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
            // TODO: Add backend call to delete transaction: /payments/delete/{id}
            this.payments.splice(index, 1);
        },

        // Discount methods
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

                const response = await this.fetchAPI('/sale/discount-global/', {
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

                    const response = await this.fetchAPI('/sale/discount-item/', {
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

        // Sale actions
        viewDetails() {
            const summary = `
Venta #${this.saleId}
Subtotal: ${this.formatCurrency(this.calculateSubtotal())}
Descuento: ${this.formatCurrency(this.globalDiscountAmount)}
Total: ${this.formatCurrency(this.calculateTotal())}
Pagado: ${this.formatCurrency(this.calculateTotalPaid())}
Restante: ${this.formatCurrency(this.calculateRemaining())}
Items: ${this.lineItems.length}
            `;
            alert(summary);
        },

        async finalizeSale() {
            if (!this.canFinalize()) return;

            if (!confirm('¿Confirmar finalización de venta y emisión de comprobante AFIP?')) return;

            this.isLoading = true;

            try {
                // Step 1: Finalize sale
                const formData = new URLSearchParams();
                formData.append('sale_id', this.saleId);

                const response = await this.fetchAPI('/sale/finalize/', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (!data.success) {
                    this.showError(data.error || 'Error al finalizar venta');
                    this.isLoading = false;
                    return;
                }

                // Step 2: Process AFIP
                const afipResponse = await this.fetchAPI(`/invoices/process-sale/${this.saleId}/`, {
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

        formatReceiptType(receiptType) {
            if (receiptType === 'Factura C' && !this.customer.id) {
                return 'Ticket';
            }
            return receiptType;
        }
    }
}

// Make available globally for Alpine.js
window.posApp = posApp;
