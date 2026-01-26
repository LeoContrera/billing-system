# Migración de Lógica de Pagos a Django Backend

## Resumen

La lógica de pagos que anteriormente estaba implementada en Alpine.js (frontend) ha sido migrada completamente a la capa de servicios de Django, siguiendo el patrón Service Layer del proyecto.

## Cambios Realizados

### 1. Modelo `Transaction` Extendido

**Archivo**: `src/apps/payments/models.py`

Se agregaron los siguientes campos al modelo `Transaction`:

```python
class Transaction(models.Model):
    # Campos existentes
    sale = models.ForeignKey('sale.Sale', ...)
    payment_method = models.ForeignKey(PaymentMethod, ...)
    amount = models.DecimalField(...)  # Monto base
    created_at = models.DateTimeField(...)
    created_by = models.ForeignKey(...)

    # Nuevos campos para tarjetas
    card_type = models.CharField(
        max_length=20,
        choices=CARD_TYPE_CHOICES,  # VISA, MASTERCARD, AMEX, etc.
        null=True,
        blank=True
    )
    installments = models.PositiveIntegerField(default=1)
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
```

**Migraciones aplicadas**:
- `0003_transaction_card_type_...`: Agrega los nuevos campos
- `0004_populate_total_amount`: Migración de datos para registros existentes

### 2. Service Layer - `PaymentService`

**Archivo**: `src/apps/payments/services.py`

#### Método: `calculate_interest()`

Calcula el monto total con interés compuesto:

```python
@staticmethod
def calculate_interest(
    amount: Decimal,
    installments: int,
    interest_rate: Decimal
) -> Decimal:
    """
    Formula: Total = Amount * (1 + rate/100)^installments

    Ejemplo:
        amount = $100,000
        installments = 6
        interest_rate = 5.00%

        Total = 100,000 * (1.05)^6 = $134,009.56
    """
```

#### Método: `validate_payment_data()`

Valida los datos de pago según el método seleccionado:

```python
@staticmethod
def validate_payment_data(
    payment_method: PaymentMethod,
    amount: Decimal,
    card_type: Optional[str] = None,
    installments: int = 1,
    interest_rate: Decimal = Decimal('0.00')
) -> Dict[str, Any]:
    """
    Validaciones:
        - Monto > 0
        - Card type requerido para tarjetas
        - Installments >= 1
        - Interest rate >= 0
    """
```

#### Método: `add_payment()` (Actualizado)

Crea transacciones con cálculo automático de intereses:

```python
@staticmethod
@transaction.atomic
def add_payment(
    sale_id: int,
    payment_method_id: int,
    amount: Decimal,
    user,
    card_type: Optional[str] = None,
    installments: int = 1,
    interest_rate: Decimal = Decimal('0.00')
) -> Transaction:
    """
    Registro de pago con:
        - Validación completa de datos
        - Cálculo automático de intereses
        - Lock de Sale para evitar race conditions
        - Transaction safety (@transaction.atomic)
    """
```

### 3. Vistas (Endpoints HTMX)

**Archivo**: `src/apps/payments/views.py`

#### Vista: `add_payment` (Actualizada)

```python
@login_required
@require_POST
def add_payment(request):
    """
    POST /payments/add/

    Parámetros:
        - sale_id
        - payment_method_id
        - amount
        - card_type (opcional)
        - installments (default: 1)
        - interest_rate (default: 0.00)

    Retorna:
        HTML fragment: Fila de pago para HTMX swap
    """
```

#### Vista: `preview_interest` (Nueva)

```python
@login_required
@require_http_methods(["GET", "POST"])
def preview_interest(request):
    """
    GET/POST /payments/preview-interest/

    Parámetros:
        - amount
        - installments
        - interest_rate

    Retorna:
        JSON: {
            "amount": "10000.00",
            "total_amount": "13400.96",
            "installments": 6,
            "installment_value": "2233.49",
            "interest_rate": "5.00"
        }
    """
```

**URLs**: `src/apps/payments/urls.py`

```python
urlpatterns = [
    path('add/', views.add_payment, name='add_payment'),
    path('preview-interest/', views.preview_interest, name='preview_interest'),
]
```

### 4. Tests Completos

**Archivo**: `src/apps/payments/tests.py`

- **InterestCalculationTests**: Tests de cálculo de intereses
- **PaymentValidationTests**: Tests de validación de datos
- **TransactionCreationTests**: Tests de creación de transacciones

Todos los tests pasan (15/15 OK).

## Integración con Frontend (HTMX)

### Opción 1: Formulario HTMX puro (Recomendado)

Reemplazar la lógica de Alpine.js con llamadas HTMX al backend:

```html
<!-- Modal de Pago -->
<form
    hx-post="{% url 'payments:add_payment' %}"
    hx-target="#payment-list"
    hx-swap="beforeend">

    <input type="hidden" name="sale_id" value="{{ sale.id }}">

    <!-- Método de pago -->
    <select name="payment_method_id" id="payment-method">
        {% for method in payment_methods %}
        <option value="{{ method.id }}">{{ method.name }}</option>
        {% endfor %}
    </select>

    <!-- Tipo de tarjeta (conditional) -->
    <select name="card_type" id="card-type">
        <option value="">Seleccionar...</option>
        <option value="VISA">VISA</option>
        <option value="MASTERCARD">Mastercard</option>
        <!-- ... -->
    </select>

    <!-- Cuotas -->
    <select name="installments" id="installments"
            hx-get="{% url 'payments:preview_interest' %}"
            hx-trigger="change"
            hx-target="#interest-preview"
            hx-include="[name='amount'], [name='interest_rate']">
        <option value="1">1 cuota (sin interés)</option>
        <option value="3">3 cuotas</option>
        <option value="6">6 cuotas</option>
        <!-- ... -->
    </select>

    <!-- Tasa de interés -->
    <input
        type="number"
        name="interest_rate"
        step="0.01"
        hx-get="{% url 'payments:preview_interest' %}"
        hx-trigger="input changed delay:500ms"
        hx-target="#interest-preview"
        hx-include="[name='amount'], [name='installments']">

    <!-- Monto -->
    <input
        type="number"
        name="amount"
        step="0.01"
        value="{{ sale.remaining_balance }}"
        hx-get="{% url 'payments:preview_interest' %}"
        hx-trigger="input changed delay:500ms"
        hx-target="#interest-preview"
        hx-include="[name='installments'], [name='interest_rate']">

    <!-- Preview de interés -->
    <div id="interest-preview"></div>

    <button type="submit">Agregar Pago</button>
</form>

<!-- Lista de pagos -->
<div id="payment-list">
    {% for transaction in sale.transactions.all %}
        {% include 'sale/_payment_row.html' %}
    {% endfor %}
</div>
```

### Opción 2: Híbrida (Alpine.js + Backend)

Mantener Alpine.js para la UI pero delegar cálculos al backend:

```html
<div x-data="paymentModal()">
    <!-- ... campos del formulario ... -->

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
                totalAmount: 0,

                // Llamar al backend para calcular intereses
                async calculateInterest() {
                    const response = await fetch(
                        `/payments/preview-interest/?` +
                        `amount=${this.newPayment.amount}` +
                        `&installments=${this.newPayment.installments}` +
                        `&interest_rate=${this.newPayment.interestRate}`
                    );
                    const data = await response.json();
                    this.totalAmount = parseFloat(data.total_amount);
                },

                // El resto de validaciones y submit via HTMX
                isPaymentValid() {
                    // Validaciones simples en frontend
                    return this.newPayment.amount > 0;
                }
            }
        }
    </script>
</div>
```

## Ventajas de la Migración

### 1. **Single Source of Truth**
- La lógica de negocio reside en un solo lugar (backend)
- Cambios en fórmulas de interés se propagan automáticamente
- No hay riesgo de desincronización frontend-backend

### 2. **Testeable**
- Tests unitarios completos (15 tests)
- Cobertura de casos edge (cuotas = 1, tasa = 0, etc.)
- Validación de datos exhaustiva

### 3. **ORM-First**
- Todas las operaciones usan Django ORM
- Transacciones atómicas con `@transaction.atomic`
- Locks optimistas con `select_for_update()`

### 4. **Auditable**
- Todos los campos se persisten en la BD
- Trazabilidad completa de pagos
- Historial de intereses aplicados

### 5. **Escalable**
- Fácil agregar nuevos métodos de pago
- Fórmulas de interés centralizadas
- Separación de responsabilidades (View → Service → Model)

## Cálculo de Total Pagado

**Importante**: El cálculo de `total_paid` usa el monto **base** (sin intereses):

```python
# En Sale model
@property
def total_paid(self):
    """Suma de todos los pagos registrados."""
    return sum(t.amount for t in self.transactions.all())
```

Esto es correcto porque:
- El cliente debe pagar el total de la venta
- Los intereses son un cargo adicional del procesador de pagos
- El balance se calcula sobre el monto base

**Ejemplo**:
```
Venta total: $100,000
Pago 1: $50,000 en efectivo
Pago 2: $50,000 en crédito 6 cuotas al 5%
    - amount (base): $50,000
    - total_amount (con interés): $67,004.78
    - El cliente paga $67,004.78 al banco
    - Pero cuenta como $50,000 hacia la venta

Total pagado: $100,000 ✓
Venta completada
```

## Próximos Pasos

1. **Actualizar template `pos_index.html`** para usar HTMX en lugar de Alpine.js
2. **Crear template `_payment_row.html`** para renderizar filas de pago
3. **Crear template `_interest_preview.html`** para mostrar preview de intereses
4. **Eliminar código Alpine.js** de cálculo de intereses (ya no necesario)
5. **Agregar indicadores de loading** en HTMX (hx-indicator)

## Comandos para Probar

```bash
# Ejecutar tests
uv run python manage.py test payments

# Ejecutar servidor
just run

# Verificar migraciones
uv run python manage.py showmigrations payments
```

## Referencias

- **CLAUDE.md**: Guía de desarrollo del proyecto
- **PlantUML diagrams**: `documentation/`
- **Django ORM Best Practices**: Usar `select_related`, `prefetch_related`, `F()`, `Q()`
- **Service Layer Pattern**: Lógica de negocio en `services.py`
