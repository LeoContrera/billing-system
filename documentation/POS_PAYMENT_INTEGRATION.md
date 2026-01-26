# Integración de Pagos con Backend en POS

## Resumen

El modal de pagos en `templates/sale/pos_index.html` ha sido actualizado para integrar completamente con el backend de Django, delegando todos los cálculos de intereses y validaciones al servicio `PaymentService`.

## Cambios Realizados

### 1. Template HTML (líneas 600-727)

**Antes**: Modal con lógica Alpine.js para cálculos
**Después**: Formulario HTML que delega al backend

#### Cambios principales:

```html
<!-- Formulario con submit -->
<form id="payment-form" @submit.prevent="submitPayment($event)">
    <input type="hidden" name="sale_id" value="{{ sale.id }}">

    <!-- Campos con nombres que coinciden con el backend -->
    <select name="payment_method_id" x-model="newPayment.methodId">
        {% for pm in payment_methods %}
        <option value="{{ pm.id }}" data-type="{{ pm.method_type }}">
            {{ pm.name }}
        </option>
        {% endfor %}
    </select>

    <input name="amount" type="number" x-model="newPayment.amount"
           @input.debounce.500ms="fetchInterestPreview()">

    <!-- Preview de intereses cargado desde el backend -->
    <div id="interest-preview"></div>
</form>
```

### 2. Estructura de Datos Alpine.js

#### newPayment (actualizado):

```javascript
newPayment: {
    methodId: null,              // ID del método de pago
    amount: 0,                   // Monto base
    cardType: '',                // Tipo de tarjeta (VISA, MASTERCARD, etc.)
    installments: 1,             // Número de cuotas
    interestRate: 0,             // Tasa de interés mensual
    requiresCard: false,         // Flag: requiere tipo de tarjeta
    isCredit: false,             // Flag: es tarjeta de crédito
    isSubmitting: false          // Flag: formulario en proceso
}
```

#### payments array (actualizado):

```javascript
payments: [
    {
        id: 123,
        method: 'Tarjeta de Crédito',
        methodType: 'CREDIT',
        amount: 50000,              // Monto base
        totalAmount: 67004.78,      // Monto con intereses
        cardType: 'VISA',
        installments: 6,
        interestRate: 5.00
    }
]
```

### 3. Funciones JavaScript Actualizadas

#### Funciones Eliminadas (ahora en backend):

- ❌ `calculateInterest()` - Cálculo de intereses
- ❌ `isPaymentValid()` - Validación de datos

#### Funciones Nuevas:

```javascript
// 1. Actualiza flags según método de pago
updatePaymentMethodFlags() {
    const pm = this.getSelectedPaymentMethod();
    if (pm) {
        this.newPayment.requiresCard = (pm.methodType === 'DEBIT' || pm.methodType === 'CREDIT');
        this.newPayment.isCredit = (pm.methodType === 'CREDIT');
    }
}

// 2. Resetea campos al cambiar método de pago
resetPaymentDetails() {
    this.newPayment.cardType = '';
    this.newPayment.installments = 1;
    this.newPayment.interestRate = 0;
    this.updatePaymentMethodFlags();
    document.getElementById('interest-preview').innerHTML = '';
}

// 3. Obtiene preview de intereses del backend
async fetchInterestPreview() {
    const amount = parseFloat(this.newPayment.amount) || 0;
    if (amount <= 0) return;

    const params = new URLSearchParams({
        amount: this.newPayment.amount,
        installments: this.newPayment.installments,
        interest_rate: this.newPayment.interestRate
    });

    const response = await fetch(`/payments/preview-interest/?${params}`, {
        headers: { 'HX-Request': 'true' }
    });

    if (response.ok) {
        const html = await response.text();
        document.getElementById('interest-preview').innerHTML = html;
    }
}

// 4. Envía el formulario al backend
async submitPayment(event) {
    this.newPayment.isSubmitting = true;

    const formData = new FormData(event.target);
    const response = await fetch('/payments/add/', {
        method: 'POST',
        headers: { 'X-CSRFToken': this.csrfToken },
        body: formData
    });

    if (response.ok) {
        const data = await response.json();
        // Agregar pago a la lista local
        this.payments.push({
            id: data.transaction.id,
            amount: parseFloat(data.transaction.amount),
            totalAmount: parseFloat(data.transaction.total_amount),
            // ...
        });
        this.closePaymentModal();
        this.showSuccess('Pago registrado exitosamente');
    }

    this.newPayment.isSubmitting = false;
}
```

#### Funciones Actualizadas:

```javascript
// openPaymentModal() - Pre-fill con saldo restante
openPaymentModal() {
    this.newPayment.amount = Math.max(0, this.calculateRemaining());
    this.newPayment.isSubmitting = false;

    if (this.paymentMethods.length > 0) {
        this.newPayment.methodId = this.paymentMethods[0].id;
        this.updatePaymentMethodFlags();
    }

    document.getElementById('interest-preview').innerHTML = '';
    this.showPaymentModal = true;
}
```

### 4. Backend - Vista `/payments/add/`

**Archivo**: `src/apps/payments/views.py`

```python
@login_required
@require_POST
def add_payment(request):
    # Parsear datos
    sale_id = int(request.POST.get('sale_id'))
    payment_method_id = int(request.POST.get('payment_method_id'))
    amount = Decimal(request.POST.get('amount', '0'))
    card_type = request.POST.get('card_type') or None
    installments = int(request.POST.get('installments', '1'))
    interest_rate = Decimal(request.POST.get('interest_rate', '0.00'))

    # Delegar al servicio (con validación y cálculo automático)
    transaction = PaymentService.add_payment(
        sale_id=sale_id,
        payment_method_id=payment_method_id,
        amount=amount,
        user=request.user,
        card_type=card_type,
        installments=installments,
        interest_rate=interest_rate
    )

    # Retornar JSON (para Alpine.js) o HTML (para HTMX)
    if request.headers.get('HX-Request'):
        return render(request, 'sale/partials/_payment_row.html', ...)

    return JsonResponse({
        'success': True,
        'transaction': {
            'id': transaction.id,
            'amount': str(transaction.amount),
            'total_amount': str(transaction.total_amount),
            'card_type': transaction.card_type,
            'installments': transaction.installments,
            'interest_rate': str(transaction.interest_rate),
            # ...
        }
    })
```

### 5. Backend - Vista `/payments/preview-interest/`

```python
@login_required
@require_http_methods(["GET", "POST"])
def preview_interest(request):
    params = request.GET if request.method == 'GET' else request.POST

    amount = Decimal(params.get('amount', '0'))
    installments = int(params.get('installments', '1'))
    interest_rate = Decimal(params.get('interest_rate', '0.00'))

    # Calcular usando el servicio
    total_amount = PaymentService.calculate_interest(
        amount=amount,
        installments=installments,
        interest_rate=interest_rate
    )

    # Retornar HTML fragment si es HTMX
    if request.headers.get('HX-Request'):
        return render(request, 'sale/partials/_interest_preview.html', {
            'interest_data': { ... }
        })

    # Retornar JSON si es API
    return JsonResponse({ ... })
```

## Flujo de Interacción

### 1. Apertura del Modal

```
Usuario click "Agregar Pago"
    ↓
openPaymentModal()
    ↓
Pre-fill amount con saldo restante
    ↓
Seleccionar primer método de pago
    ↓
updatePaymentMethodFlags()
    ↓
Mostrar modal
```

### 2. Cambio de Método de Pago

```
Usuario selecciona método
    ↓
@change → resetPaymentDetails()
    ↓
Limpiar campos de tarjeta
    ↓
updatePaymentMethodFlags()
    ↓
Actualizar x-show condicionales
    ↓
Limpiar preview de intereses
```

### 3. Cálculo de Intereses en Tiempo Real

```
Usuario modifica:
  - amount
  - installments
  - interest_rate
    ↓
@input.debounce.500ms → fetchInterestPreview()
    ↓
GET /payments/preview-interest/?amount=...
    ↓
Backend calcula con PaymentService.calculate_interest()
    ↓
Retorna HTML fragment
    ↓
Actualizar #interest-preview div
```

### 4. Envío del Pago

```
Usuario click "Agregar"
    ↓
@submit.prevent → submitPayment(event)
    ↓
FormData con todos los campos
    ↓
POST /payments/add/
    ↓
Backend:
  - PaymentService.validate_payment_data()
  - PaymentService.calculate_interest()
  - PaymentService.add_payment()
  - Transaction.objects.create()
    ↓
Retornar JSON con transaction data
    ↓
Frontend:
  - Agregar a payments array
  - Actualizar UI
  - Cerrar modal
  - Mostrar success message
```

## Ventajas de la Nueva Implementación

### 1. **Single Source of Truth**
- ✅ Cálculos de intereses en un solo lugar (backend)
- ✅ No hay riesgo de desincronización frontend-backend
- ✅ Cambios en fórmulas se propagan automáticamente

### 2. **Validación Robusta**
- ✅ Validación exhaustiva en backend (Django validators)
- ✅ Card type requerido para tarjetas (backend valida)
- ✅ Montos positivos garantizados
- ✅ Transacciones atómicas con `@transaction.atomic`

### 3. **Testeable**
- ✅ 15 tests automatizados en `payments/tests.py`
- ✅ Cobertura completa de cálculos de interés
- ✅ Tests de validación de datos
- ✅ Tests de creación de transacciones

### 4. **Auditable**
- ✅ Todos los campos persistidos en BD
- ✅ Trazabilidad completa de pagos
- ✅ Historial de intereses aplicados
- ✅ Logs de validaciones fallidas

### 5. **Escalable**
- ✅ Fácil agregar nuevos métodos de pago
- ✅ Fácil cambiar fórmulas de interés
- ✅ Separación de responsabilidades clara
- ✅ API reutilizable (HTMX o Alpine.js)

## Comparación Antes/Después

| Aspecto | Antes (Alpine.js) | Después (Backend) |
|---------|------------------|-------------------|
| **Cálculo de intereses** | Frontend (JavaScript) | Backend (Python) |
| **Validación** | Parcial en frontend | Completa en backend |
| **Persistencia** | Solo `amount` | Todos los campos |
| **Testing** | Manual | 15 tests automatizados |
| **Mantenibilidad** | Duplicación de lógica | Single source of truth |
| **Seguridad** | Puede ser bypasseada | Validación obligatoria |
| **Auditoría** | Limitada | Completa |

## Campos Agregados a `Transaction`

```python
class Transaction(models.Model):
    # Campos existentes
    sale = models.ForeignKey('sale.Sale', ...)
    payment_method = models.ForeignKey(PaymentMethod, ...)
    amount = models.DecimalField(...)  # Monto base
    created_at = models.DateTimeField(...)
    created_by = models.ForeignKey(...)

    # NUEVOS CAMPOS
    card_type = models.CharField(
        choices=[
            ('VISA', 'VISA'),
            ('MASTERCARD', 'Mastercard'),
            ('AMEX', 'American Express'),
            ('CABAL', 'Cabal'),
            ('NARANJA', 'Naranja'),
            ('MAESTRO', 'Maestro'),
            ('OTHER', 'Otra'),
        ],
        null=True, blank=True
    )
    installments = models.PositiveIntegerField(default=1)
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(...)  # amount + intereses
```

## Ejemplo de Uso

### Pago en Efectivo

```javascript
// Usuario selecciona "Efectivo"
// requiresCard = false
// isCredit = false

// Envía:
{
    sale_id: 123,
    payment_method_id: 1,
    amount: 10000.00,
    card_type: null,
    installments: 1,
    interest_rate: 0.00
}

// Backend guarda:
{
    amount: 10000.00,
    total_amount: 10000.00,
    card_type: null,
    installments: 1,
    interest_rate: 0.00
}
```

### Pago con Tarjeta de Crédito en Cuotas

```javascript
// Usuario selecciona "Tarjeta de Crédito"
// requiresCard = true
// isCredit = true

// Ingresa:
// - Card type: VISA
// - Installments: 6
// - Interest rate: 5.00%
// - Amount: 50000.00

// Preview automático:
// GET /payments/preview-interest/?amount=50000&installments=6&interest_rate=5.00
// → Muestra: Total $67,004.78 (6 cuotas de $11,167.46)

// Envía al confirmar:
{
    sale_id: 123,
    payment_method_id: 3,
    amount: 50000.00,
    card_type: 'VISA',
    installments: 6,
    interest_rate: 5.00
}

// Backend calcula y guarda:
{
    amount: 50000.00,
    total_amount: 67004.78,  // 50000 * (1.05)^6
    card_type: 'VISA',
    installments: 6,
    interest_rate: 5.00
}
```

## Testing

```bash
# Ejecutar tests
uv run python manage.py test payments

# Output esperado:
# test_no_interest_single_installment ... ok
# test_no_interest_zero_rate ... ok
# test_compound_interest_calculation ... ok
# test_validate_card_type_required_for_credit ... ok
# test_create_credit_payment_with_installments ... ok
# ... (15 tests)
# OK
```

## Archivos Modificados

1. ✅ `templates/sale/pos_index.html` (líneas 600-727)
2. ✅ `src/apps/payments/models.py` - Campos nuevos
3. ✅ `src/apps/payments/services.py` - Lógica de negocio
4. ✅ `src/apps/payments/views.py` - Endpoints
5. ✅ `src/apps/payments/urls.py` - URL preview-interest
6. ✅ `src/apps/payments/tests.py` - 15 tests
7. ✅ `templates/sale/partials/_payment_row.html` - Template parcial
8. ✅ `templates/sale/partials/_interest_preview.html` - Template parcial

## Próximos Pasos (Opcional)

1. **Eliminar endpoint antiguo**: `/sale/add-payment/` (ahora usa `/payments/add/`)
2. **Agregar eliminación de pagos**: Endpoint DELETE `/payments/<id>/delete/`
3. **Agregar tooltips**: Explicar cómo se calculan los intereses
4. **Agregar notificaciones**: Usar HTMX para notificaciones toast
5. **Optimizar UI**: Agregar skeleton loaders durante cálculos

## Notas Importantes

- ✅ **CSRF Token**: Configurado correctamente en headers
- ✅ **Compatibilidad**: Funciona con HTMX y Alpine.js
- ✅ **Performance**: Debounce de 500ms en preview de intereses
- ✅ **UX**: Loading states durante submit
- ✅ **Error Handling**: Mensajes de error específicos
- ✅ **Accesibilidad**: Labels descriptivos, required fields
