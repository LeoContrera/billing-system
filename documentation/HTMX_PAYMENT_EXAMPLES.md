# Ejemplos de Integración HTMX para Pagos

## Ejemplo Completo: Modal de Pago con HTMX

Este ejemplo muestra cómo integrar el backend de pagos con HTMX, eliminando la necesidad de Alpine.js para cálculos y validaciones.

### 1. Formulario de Pago

```html
<!-- Modal de Pago -->
<div id="payment-modal" class="modal">
    <div class="card p-8 max-w-lg w-full">
        <h3 class="text-xl font-bold mb-6 text-blue-600">Agregar Pago</h3>

        <form
            id="payment-form"
            hx-post="{% url 'payments:add_payment' %}"
            hx-target="#payment-list"
            hx-swap="beforeend"
            hx-on::after-request="if(event.detail.successful) closeModal()">

            <input type="hidden" name="sale_id" value="{{ sale.id }}">

            <div class="space-y-4">
                <!-- Método de Pago -->
                <div>
                    <label class="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                        Método de Pago
                    </label>
                    <select
                        name="payment_method_id"
                        id="payment-method"
                        class="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 text-sm text-gray-900"
                        hx-get="{% url 'payments:payment_method_fields' %}"
                        hx-target="#conditional-fields"
                        hx-swap="innerHTML">
                        {% for method in payment_methods %}
                        <option value="{{ method.id }}" data-type="{{ method.method_type }}">
                            {{ method.name }}
                        </option>
                        {% endfor %}
                    </select>
                </div>

                <!-- Campos condicionales (se cargan via HTMX) -->
                <div id="conditional-fields">
                    <!-- Se cargará dinámicamente según el método seleccionado -->
                </div>

                <!-- Cuotas (solo para crédito) -->
                <div id="installments-section" style="display: none;">
                    <label class="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                        Cuotas
                    </label>
                    <select
                        name="installments"
                        id="installments"
                        class="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 text-sm text-gray-900"
                        hx-get="{% url 'payments:preview_interest' %}"
                        hx-trigger="change"
                        hx-target="#interest-preview"
                        hx-include="[name='amount'], [name='interest_rate']">
                        <option value="1">1 cuota (sin interés)</option>
                        <option value="3">3 cuotas</option>
                        <option value="6">6 cuotas</option>
                        <option value="9">9 cuotas</option>
                        <option value="12">12 cuotas</option>
                        <option value="18">18 cuotas</option>
                        <option value="24">24 cuotas</option>
                    </select>
                </div>

                <!-- Tasa de Interés (solo para crédito con cuotas > 1) -->
                <div id="interest-rate-section" style="display: none;">
                    <label class="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                        Tasa de Interés (%)
                    </label>
                    <div class="relative">
                        <input
                            type="number"
                            name="interest_rate"
                            id="interest-rate"
                            min="0"
                            max="100"
                            step="0.01"
                            value="0.00"
                            class="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 pr-10 text-sm font-mono text-gray-900"
                            placeholder="0.00"
                            hx-get="{% url 'payments:preview_interest' %}"
                            hx-trigger="input changed delay:500ms"
                            hx-target="#interest-preview"
                            hx-include="[name='amount'], [name='installments']">
                        <span class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 font-mono font-semibold">%</span>
                    </div>
                    <div class="mt-1 text-xs text-gray-600">
                        Tasa mensual aplicada al monto base
                    </div>
                </div>

                <!-- Monto -->
                <div>
                    <label class="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                        Monto Base
                    </label>
                    <div class="relative">
                        <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-mono font-semibold">$</span>
                        <input
                            type="number"
                            name="amount"
                            id="amount"
                            step="0.01"
                            value="{{ sale.remaining_balance }}"
                            required
                            class="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 pl-8 text-sm font-mono text-gray-900"
                            placeholder="0.00"
                            hx-get="{% url 'payments:preview_interest' %}"
                            hx-trigger="input changed delay:500ms"
                            hx-target="#interest-preview"
                            hx-include="[name='installments'], [name='interest_rate']">
                    </div>
                    <div class="mt-2 text-xs text-gray-600">
                        Saldo restante:
                        <span class="font-mono font-semibold text-amber-600">
                            $ {{ sale.remaining_balance|floatformat:2 }}
                        </span>
                    </div>
                </div>

                <!-- Preview de Interés -->
                <div id="interest-preview">
                    <!-- Se carga dinámicamente via HTMX -->
                </div>

                <!-- Botones de Acción -->
                <div class="flex gap-3 mt-6">
                    <button
                        type="button"
                        onclick="closeModal()"
                        class="btn flex-1 py-3 bg-white border-2 border-gray-300 text-gray-700 rounded-lg font-semibold text-sm hover:bg-gray-50">
                        Cancelar
                    </button>
                    <button
                        type="submit"
                        class="btn flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-sm">
                        <span class="htmx-indicator">
                            <svg class="animate-spin h-5 w-5 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                        </span>
                        <span class="htmx-content">Agregar Pago</span>
                    </button>
                </div>
            </div>
        </form>
    </div>
</div>

<!-- Lista de Pagos -->
<div class="mt-6">
    <h4 class="text-lg font-bold mb-4">Pagos Registrados</h4>

    <table class="w-full">
        <thead>
            <tr class="table-header">
                <th class="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider text-gray-700">Método</th>
                <th class="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider text-gray-700">Monto Base</th>
                <th class="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider text-gray-700">Cuotas</th>
                <th class="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider text-gray-700">Total</th>
                <th class="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider text-gray-700">Fecha</th>
                <th class="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider text-gray-700">Acciones</th>
            </tr>
        </thead>
        <tbody id="payment-list">
            {% for transaction in sale.transactions.all %}
                {% include 'sale/partials/_payment_row.html' %}
            {% endfor %}
        </tbody>
    </table>

    <!-- Empty State -->
    {% if not sale.transactions.all %}
    <div class="text-center py-12 text-gray-500 text-sm">
        No hay pagos registrados
    </div>
    {% endif %}
</div>

<script>
    // JavaScript mínimo para UI
    function closeModal() {
        document.getElementById('payment-modal').style.display = 'none';
        // Reset form
        document.getElementById('payment-form').reset();
        document.getElementById('interest-preview').innerHTML = '';
    }

    function openModal() {
        document.getElementById('payment-modal').style.display = 'flex';
    }

    // Mostrar/ocultar campos según método de pago
    document.getElementById('payment-method').addEventListener('change', function(e) {
        const selectedOption = e.target.options[e.target.selectedIndex];
        const methodType = selectedOption.dataset.type;

        // Mostrar campos de tarjeta si es DEBIT o CREDIT
        const cardFields = document.getElementById('conditional-fields');
        const installmentsSection = document.getElementById('installments-section');
        const interestSection = document.getElementById('interest-rate-section');

        if (methodType === 'CREDIT') {
            installmentsSection.style.display = 'block';
            // Interest section se muestra cuando installments > 1
        } else {
            installmentsSection.style.display = 'none';
            interestSection.style.display = 'none';
        }
    });

    // Mostrar sección de interés cuando cuotas > 1
    document.getElementById('installments').addEventListener('change', function(e) {
        const installments = parseInt(e.target.value);
        const interestSection = document.getElementById('interest-rate-section');

        if (installments > 1) {
            interestSection.style.display = 'block';
        } else {
            interestSection.style.display = 'none';
            document.getElementById('interest-rate').value = '0.00';
        }
    });
</script>
```

## 2. Ejemplo de Uso con Alpine.js (Híbrido)

Si prefieres mantener Alpine.js para la UI pero delegar cálculos al backend:

```html
<div x-data="paymentModal()">
    <form @submit.prevent="submitPayment()">
        <!-- ... campos del formulario ... -->

        <input
            type="number"
            x-model="newPayment.amount"
            @input.debounce.500ms="fetchInterestPreview()">

        <select
            x-model="newPayment.installments"
            @change="fetchInterestPreview()">
            <!-- opciones -->
        </select>

        <input
            type="number"
            x-model="newPayment.interestRate"
            @input.debounce.500ms="fetchInterestPreview()">

        <!-- Preview renderizado desde el backend -->
        <div id="interest-preview"></div>
    </form>

    <script>
        function paymentModal() {
            return {
                newPayment: {
                    method: 'EFECTIVO',
                    amount: 0,
                    cardType: '',
                    installments: 1,
                    interestRate: 0
                },

                // Llamar al backend para calcular intereses
                fetchInterestPreview() {
                    htmx.ajax('GET',
                        `/payments/preview-interest/?amount=${this.newPayment.amount}&installments=${this.newPayment.installments}&interest_rate=${this.newPayment.interestRate}`,
                        {target: '#interest-preview', swap: 'innerHTML'}
                    );
                },

                // Submit via HTMX
                submitPayment() {
                    const formData = new FormData();
                    formData.append('sale_id', {{ sale.id }});
                    formData.append('payment_method_id', this.newPayment.methodId);
                    formData.append('amount', this.newPayment.amount);
                    formData.append('card_type', this.newPayment.cardType);
                    formData.append('installments', this.newPayment.installments);
                    formData.append('interest_rate', this.newPayment.interestRate);

                    htmx.ajax('POST', '{% url "payments:add_payment" %}', {
                        values: Object.fromEntries(formData),
                        target: '#payment-list',
                        swap: 'beforeend'
                    }).then(() => {
                        this.resetForm();
                    });
                },

                resetForm() {
                    this.newPayment = {
                        method: 'EFECTIVO',
                        amount: 0,
                        cardType: '',
                        installments: 1,
                        interestRate: 0
                    };
                }
            }
        }
    </script>
</div>
```

## 3. Validación en Tiempo Real

```html
<!-- Input con validación en tiempo real -->
<input
    type="number"
    name="amount"
    hx-post="{% url 'payments:validate_amount' %}"
    hx-trigger="blur"
    hx-target="#amount-error"
    hx-swap="innerHTML">

<div id="amount-error" class="text-red-600 text-xs mt-1"></div>
```

## 4. Loading States con HTMX

```html
<!-- Indicador de carga en botón -->
<button
    type="submit"
    hx-post="{% url 'payments:add_payment' %}"
    hx-indicator="#spinner">
    <span id="spinner" class="htmx-indicator">
        <svg class="animate-spin h-5 w-5 inline" ...></svg>
    </span>
    <span>Agregar Pago</span>
</button>

<!-- Indicador de carga global -->
<div id="global-spinner" class="htmx-indicator fixed top-4 right-4">
    Procesando...
</div>
```

## 5. Manejo de Errores

```html
<form
    hx-post="{% url 'payments:add_payment' %}"
    hx-target="#payment-list"
    hx-swap="beforeend"
    hx-on::response-error="handleError(event)">

    <!-- campos -->
</form>

<script>
    function handleError(event) {
        if (event.detail.xhr.status === 400) {
            // Error de validación
            const errorDiv = document.getElementById('form-errors');
            errorDiv.innerHTML = event.detail.xhr.responseText;
        } else {
            // Error del servidor
            alert('Error al procesar el pago. Intente nuevamente.');
        }
    }
</script>
```

## 6. Actualización de Balance en Tiempo Real

```html
<!-- El balance se actualiza automáticamente después de cada pago -->
<div id="sale-balance">
    <div class="font-mono text-2xl font-bold">
        Saldo: $ <span hx-swap-oob="true" id="remaining-balance">{{ sale.remaining_balance|floatformat:2 }}</span>
    </div>
</div>

<!-- En la vista, retornar también el balance actualizado -->
<!-- Esto se puede hacer agregando hx-swap-oob en el template _payment_row.html -->
```

## 7. Confirmación de Eliminación

```html
<button
    hx-delete="{% url 'payments:delete_payment' transaction.id %}"
    hx-confirm="¿Está seguro de eliminar este pago de ${{ transaction.amount }}?"
    hx-target="#payment-{{ transaction.id }}"
    hx-swap="outerHTML swap:0.3s"
    class="text-red-600 hover:text-red-700">
    Eliminar
</button>
```

## Ventajas de HTMX vs Alpine.js

| Característica | HTMX | Alpine.js |
|----------------|------|-----------|
| **Lógica de negocio** | Backend (testeable) | Frontend (difícil de testear) |
| **Mantenimiento** | Single source of truth | Duplicación de código |
| **SEO** | HTML renderizado en servidor | Requiere hidratación |
| **Validación** | Django forms + backend | Debe duplicarse en frontend |
| **Seguridad** | Validación en servidor | Puede ser bypasseada |
| **Performance** | Menos JavaScript | Más JavaScript descargado |
| **Developer Experience** | Menos código total | Más flexible para UI compleja |

## Recomendación

Para el sistema POS, se recomienda **HTMX puro** porque:

1. La lógica de pagos es crítica y debe estar en el backend
2. Menor superficie de ataque (validaciones centralizadas)
3. Más fácil de testear (15 tests ya escritos)
4. Menor complejidad en el frontend
5. Mejor alineación con los principios del proyecto (Service Layer, ORM-First)

Usar Alpine.js solo para interacciones puramente visuales (animaciones, modals, tabs) que no involucren lógica de negocio.
