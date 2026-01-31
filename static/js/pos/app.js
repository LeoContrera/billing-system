/**
 * POS Application - Alpine.js Component (Refactored)
 *
 * ARQUITECTURA:
 * Este archivo es el ORQUESTADOR principal que compone módulos cohesivos.
 * NO contiene lógica de negocio - solo orquesta y delega.
 *
 * Módulos:
 * - customer-module.js: Gestión de clientes
 * - product-module.js: Gestión de productos
 * - payment-module.js: Gestión de pagos
 * - discount-module.js: Gestión de descuentos
 * - calculator-module.js: Cálculos simples
 * - invoice-module.js: Finalización y facturación
 *
 * Responsabilidades de este archivo:
 * - Inicialización con datos del backend
 * - API helper (fetchAPI)
 * - Gestión de mensajes (success/error)
 * - Gestión de loading state
 * - Composición de módulos en un solo objeto Alpine.js
 */
function posApp(initialData) {
    // ====================
    // CORE STATE & HELPERS
    // ====================

    const state = {
        saleId: initialData.saleId,
        csrfToken: initialData.csrfToken,
        issuerTaxCategory: initialData.issuerTaxCategory || 'RI',
        isLoading: false,
        errorMessage: '',
        successMessage: ''
    };

    // API helper
    const fetchAPI = async (url, options = {}) => {
        const defaultOptions = {
            headers: {
                'X-CSRFToken': state.csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            credentials: 'same-origin'
        };
        return await fetch(url, { ...defaultOptions, ...options });
    };

    // Message helpers
    const showError = (message) => {
        state.errorMessage = message;
        setTimeout(() => state.errorMessage = '', 5000);
    };

    const showSuccess = (message) => {
        state.successMessage = message;
        setTimeout(() => state.successMessage = '', 3000);
    };

    // ====================
    // MODULE CREATION
    // ====================

    // Calculator module (no dependencies)
    const calculator = createCalculatorModule();

    // Customer module
    const customer = createCustomerModule({
        saleId: state.saleId,
        csrfToken: state.csrfToken,
        issuerTaxCategory: state.issuerTaxCategory,
        fetchAPI,
        showSuccess,
        showError
    });

    // Product module
    const product = createProductModule({
        saleId: state.saleId,
        fetchAPI,
        showSuccess,
        showError
    });

    // Initialize line items from backend
    product.lineItems = initialData.lineItems || [];

    // Payment module
    const payment = createPaymentModule({
        saleId: state.saleId,
        csrfToken: state.csrfToken,
        paymentMethods: initialData.paymentMethods || [],
        fetchAPI,
        showSuccess,
        showError,
        calculateRemaining: () => calculator.calculateRemaining(
            product.lineItems,
            discount.globalDiscountAmount,
            payment.payments
        )
    });

    // Initialize payments from backend
    payment.payments = initialData.payments || [];

    // Discount module
    const discount = createDiscountModule({
        saleId: state.saleId,
        fetchAPI,
        showSuccess,
        showError,
        calculateSubtotal: () => calculator.calculateSubtotal(product.lineItems)
    });

    // Initialize global discount from backend
    discount.globalDiscountAmount = initialData.globalDiscountAmount || 0;

    // Invoice module
    const invoice = createInvoiceModule({
        saleId: state.saleId,
        fetchAPI,
        showError
    });

    // Initialize customer if provided
    if (initialData.customer && initialData.customer.id) {
        customer.customer = initialData.customer;
        customer.updateReceiptType();
    }

    // ====================
    // COMPOSED APP OBJECT
    // ====================

    return {
        // Core state
        saleId: state.saleId,
        csrfToken: state.csrfToken,
        issuerTaxCategory: state.issuerTaxCategory,
        isLoading: state.isLoading,
        errorMessage: state.errorMessage,
        successMessage: state.successMessage,

        // Customer module properties & methods
        customer: customer.customer,
        customerSearch: customer.customerSearch,
        customerResults: customer.customerResults,
        showCustomerResults: customer.showCustomerResults,
        customerMode: customer.customerMode,
        newCustomer: customer.newCustomer,
        searchCustomers: customer.searchCustomers.bind(customer),
        selectCustomer: async (c) => {
            state.isLoading = true;
            await customer.selectCustomer(c);
            state.isLoading = false;
        },
        clearCustomer: customer.clearCustomer.bind(customer),
        canCreateCustomer: customer.canCreateCustomer.bind(customer),
        createCustomer: async () => {
            state.isLoading = true;
            await customer.createCustomer();
            state.isLoading = false;
        },
        getTaxCategoryDisplay: customer.getTaxCategoryDisplay.bind(customer),
        getCurrentReceiptType: () => customer.currentReceiptType,

        // Product module properties & methods
        lineItems: product.lineItems,
        showProductModal: product.showProductModal,
        productSearch: product.productSearch,
        productResults: product.productResults,
        selectedProduct: product.selectedProduct,
        newItemQuantity: product.newItemQuantity,
        stockInfo: product.stockInfo,
        productError: product.productError,
        openProductModal: product.openProductModal.bind(product),
        closeProductModal: product.closeProductModal.bind(product),
        searchProducts: product.searchProducts.bind(product),
        selectProduct: product.selectProduct.bind(product),
        checkStock: product.checkStock.bind(product),
        canAddProduct: product.canAddProduct.bind(product),
        addProduct: async () => {
            state.isLoading = true;
            await product.addProduct();
            state.isLoading = false;
        },
        removeLineItem: product.removeLineItem.bind(product),

        // Payment module properties & methods
        paymentMethods: payment.paymentMethods,
        payments: payment.payments,
        showPaymentModal: payment.showPaymentModal,
        newPayment: payment.newPayment,
        getSelectedPaymentMethod: payment.getSelectedPaymentMethod.bind(payment),
        openPaymentModal: payment.openPaymentModal.bind(payment),
        closePaymentModal: payment.closePaymentModal.bind(payment),
        updatePaymentMethodFlags: payment.updatePaymentMethodFlags.bind(payment),
        resetPaymentDetails: payment.resetPaymentDetails.bind(payment),
        fetchInterestPreview: payment.fetchInterestPreview.bind(payment),
        submitPayment: payment.submitPayment.bind(payment),
        removePayment: payment.removePayment.bind(payment),

        // Discount module properties & methods
        globalDiscountAmount: discount.globalDiscountAmount,
        globalDiscountPercentage: discount.globalDiscountPercentage,
        showGlobalDiscountModal: discount.showGlobalDiscountModal,
        showUnitDiscountModal: discount.showUnitDiscountModal,
        tempGlobalDiscountPercentage: discount.tempGlobalDiscountPercentage,
        tempUnitDiscountPercentage: discount.tempUnitDiscountPercentage,
        selectedProductsForDiscount: discount.selectedProductsForDiscount,
        openGlobalDiscountModal: discount.openGlobalDiscountModal.bind(discount),
        applyGlobalDiscount: async () => {
            state.isLoading = true;
            await discount.applyGlobalDiscount();
            state.isLoading = false;
        },
        openUnitDiscountModal: discount.openUnitDiscountModal.bind(discount),
        applyUnitDiscount: async () => {
            state.isLoading = true;
            await discount.applyUnitDiscount(product.lineItems);
            state.isLoading = false;
        },

        // Calculator module methods
        calculateGrossSubtotal: () => calculator.calculateGrossSubtotal(product.lineItems),
        calculateUnitDiscounts: () => calculator.calculateUnitDiscounts(product.lineItems),
        calculateSubtotal: () => calculator.calculateSubtotal(product.lineItems),
        calculateTotal: () => calculator.calculateTotal(product.lineItems, discount.globalDiscountAmount),
        calculateTotalPaid: () => calculator.calculateTotalPaid(payment.payments),
        calculateRemaining: () => calculator.calculateRemaining(product.lineItems, discount.globalDiscountAmount, payment.payments),
        canFinalize: () => calculator.canFinalize(product.lineItems, payment.payments, discount.globalDiscountAmount),
        formatCurrency: calculator.formatCurrency.bind(calculator),

        // Invoice module properties & methods
        invoice: invoice.invoice,
        showInvoiceModal: invoice.showInvoiceModal,
        showDetailsModal: invoice.showDetailsModal,
        finalizeSale: async () => {
            state.isLoading = true;
            await invoice.finalizeSale(() => this.canFinalize());
            state.isLoading = false;
        },
        closeInvoiceModal: invoice.closeInvoiceModal.bind(invoice),
        downloadPDF: invoice.downloadPDF.bind(invoice),
        viewDetails: invoice.viewDetails.bind(invoice),
        closeDetailsModal: invoice.closeDetailsModal.bind(invoice),
        formatReceiptType: (receiptType) => invoice.formatReceiptType(receiptType, customer.customer.id),

        // API helper (exposed for modules that need it)
        fetchAPI,

        // Message helpers (exposed for modules that need them)
        showError: (msg) => {
            state.errorMessage = msg;
            setTimeout(() => state.errorMessage = '', 5000);
        },
        showSuccess: (msg) => {
            state.successMessage = msg;
            setTimeout(() => state.successMessage = '', 3000);
        },

        // Initialize
        init() {
            payment.init();
        }
    };
}

// Make available globally for Alpine.js
window.posApp = posApp;
