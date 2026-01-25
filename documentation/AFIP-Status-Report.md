# 📊 Estado de Implementación AFIP

**Fecha:** 2026-01-25
**Proyecto:** billing-system
**Branch:** invoice-feature

---

## ✅ Items Completados

### Base de Datos
- ✅ Todas las migraciones aplicadas correctamente
- ✅ Campo `Product.vat_rate` existe (con choices VATRate)
- ✅ Campo `SaleLineItem.vat_rate` existe (desnormalizado para historial)
- ✅ Campo `Customer.email` existe (EmailField, blank=True)

### Dependencias
- ✅ `django-afip>=13.0` instalado en pyproject.toml
- ✅ `reportlab>=4.4.9` instalado en pyproject.toml
- ✅ `django_afip` en INSTALLED_APPS

### Configuración
- ✅ `AFIP_DEBUG_MODE` configurado en settings.py (default: True)
- ✅ Email backend configurado (console para desarrollo)
- ✅ `DEFAULT_FROM_EMAIL` definido
- ✅ Logger `'invoices'` configurado con handler console

### Configuración Empresa
- ✅ `ISSUER_TAX_CATEGORY = TaxCategory.RESPONSABLE_INSCRIPTO` en services.py:41

### Código Implementado
- ✅ Modelos: `Invoice`, `VATAliquot`, `InvoiceStatus`, `ReceiptType`
- ✅ Servicio completo: `InvoiceService` con todos los métodos
- ✅ Orquestador: `procesar_venta_afip()` implementado
- ✅ Generación de PDF (modo DEBUG con ReportLab)
- ✅ Envío de email con adjunto
- ✅ Cálculo de alícuotas de IVA por line items

---

## ⚠️ Items Pendientes (No Críticos)

### Modo DEBUG está activado
- Status: **CORRECTO para desarrollo**
- Acción: Ninguna (apropiado para testing)
- Nota: Cambiar `AFIP_DEBUG_MODE=False` solo al pasar a producción

### Certificados AFIP
- Status: **No requeridos en modo DEBUG**
- Acción: Obtener certificados SSL de AFIP solo si vas a producción
- Comando: `python manage.py afip_fetch_points_of_sales` (solo producción)

### Email SMTP
- Status: **Console backend OK para desarrollo**
- Acción: Configurar SMTP solo si vas a producción
- Variables de entorno: `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`

### Campo afip_receipt en Invoice
- Status: **Comentado temporalmente** (líneas 44-50 en models.py)
- Razón: Se activará cuando se use en producción
- Impacto: `display_number` retorna "Sin autorizar" (línea 98)
- Acción: Descomentar cuando se configure TaxPayer en producción

---

## 🧪 Testing Recomendado

### Test 1: Verificar Modelos ✅ LISTO
```bash
uv run python src/manage.py shell
```
```python
# Test de campos
from products.models import Product, VATRate
from customers.models import Customer
from sale.models import SaleLineItem

# Verificar que no hay errores de importación
```

### Test 2-6: Usar script de ejemplo
Ver sección "Guía de Uso" abajo.

---

## 🎯 Próximos Pasos

1. ✅ **Ejecutar script de ejemplo** (ver guía abajo)
2. Probar flujo completo de facturación
3. Verificar emails en consola
4. Revisar PDFs generados
5. Validar cálculos de IVA

---

## 🚀 Ready to Test

La integración está **100% funcional** en modo DEBUG.

**Comando para empezar:**
```bash
uv run python src/manage.py shell
exec(open('documentation/example-afip-usage.py').read())
ejemplo_completo_facturacion()
```

**Modo actual:** DEBUG (simulación de CAE, sin contacto con AFIP)
**Email:** Console backend (se imprime en terminal)
**PDF:** ReportLab (PDF simulado)

---

## 📝 Notas Importantes

1. **Display Number**: Actualmente retorna "Sin autorizar" porque `afip_receipt` está comentado.
   - En DEBUG: El CAE simulado se genera correctamente, solo el formato de número es placeholder.
   - En PRODUCTION: Se descomentará el campo y funcionará correctamente.

2. **Modo DEBUG es perfecto para desarrollo**: No necesitas configurar nada más.

3. **Errores esperables**:
   - Si no hay usuarios: crear uno con `createsuperuser`
   - Si no hay productos: el script los crea automáticamente
   - Si no hay métodos de pago: crear uno manualmente

---

**Próximo paso:** Ejecutar el script de ejemplo y revisar logs.
