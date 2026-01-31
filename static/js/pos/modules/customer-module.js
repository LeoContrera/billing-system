/**
 * Customer Module - Gestión de clientes en POS
 *
 * Responsabilidades:
 * - Búsqueda de clientes existentes
 * - Selección y asignación de cliente a venta
 * - Creación de nuevos clientes
 * - Obtención de tipo de comprobante desde backend
 *
 * NO contiene lógica de negocio - todo se delega al backend.
 */
function createCustomerModule({ saleId, csrfToken, issuerTaxCategory, fetchAPI, showSuccess, showError }) {
    return {
        // Customer data
        customer: {
            id: null,
            fullName: '',
            taxId: '',
            taxCategory: '',
            taxCategoryDisplay: ''
        },

        // Search state
        customerSearch: '',
        customerResults: [],
        showCustomerResults: false,

        // Mode: 'search' or 'create'
        customerMode: 'search',

        // New customer form data
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

        // Receipt type (fetched from backend)
        currentReceiptType: 'Ticket',

        /**
         * Search customers by query string.
         */
        async searchCustomers() {
            if (this.customerSearch.length < 2) {
                this.customerResults = [];
                return;
            }
            try {
                const response = await fetchAPI(`/customers/search/?q=${encodeURIComponent(this.customerSearch)}`);
                this.customerResults = await response.json();
            } catch (error) {
                console.error('Error searching customers:', error);
            }
        },

        /**
         * Select and assign customer to sale.
         */
        async selectCustomer(c) {
            try {
                const formData = new URLSearchParams();
                formData.append('sale_id', saleId);
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

                    // Fetch receipt type from backend
                    await this.updateReceiptType();

                    showSuccess('Cliente asignado');
                } else {
                    showError(data.error || 'Error al asignar cliente');
                }
            } catch (error) {
                showError('Error al asignar cliente');
            }
        },

        /**
         * Clear customer assignment.
         */
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

        /**
         * Validate if customer can be created.
         */
        canCreateCustomer() {
            if (!this.newCustomer.firstName.trim() || !this.newCustomer.lastName.trim()) return false;
            if (!this.newCustomer.email.trim()) return false;
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(this.newCustomer.email)) return false;
            if ((this.newCustomer.taxCategory === 'RI' || this.newCustomer.taxCategory === 'MT') && !this.newCustomer.taxId.trim()) return false;
            return true;
        },

        /**
         * Create new customer and assign to sale.
         */
        async createCustomer() {
            if (!this.canCreateCustomer()) return;

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
                    assignFormData.append('sale_id', saleId);
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

                        // Fetch receipt type from backend
                        await this.updateReceiptType();

                        showSuccess('Cliente creado y asignado');
                    }
                } else {
                    showError(data.error || 'Error al crear cliente');
                }
            } catch (error) {
                showError('Error al crear cliente');
            }
        },

        /**
         * Get receipt type display for current customer.
         * Uses backend endpoint - NO business logic in frontend.
         */
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

        /**
         * Get tax category display name.
         */
        getTaxCategoryDisplay(category) {
            const displays = {
                'CF': 'Consumidor Final',
                'RI': 'Responsable Inscripto',
                'MT': 'Monotributo',
                'EX': 'Exento'
            };
            return displays[category] || 'Consumidor Final';
        }
    };
}

// Make available globally
window.createCustomerModule = createCustomerModule;
