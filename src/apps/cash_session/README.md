# Cash Session - Sistema de Control de Caja

## Descripción

Módulo de gestión de sesiones de caja con control de acceso para cajeros.

## Configuración Inicial

### 1. Cargar el Grupo de Cajeros

Para que el sistema funcione correctamente, primero debes cargar la fixture que crea el grupo "Cajeros":

```bash
cd src
uv run python manage.py loaddata apps/cash_session/fixtures/initial_cashier_group.json
```

### 2. Crear Usuarios Cajeros

Después de cargar la fixture, crea usuarios y agrégalos al grupo "Cajeros":

#### Opción A: Usando Django Admin

1. Accede al admin de Django: `http://localhost:8000/admin/`
2. Ve a "Usuarios" y crea un nuevo usuario
3. Edita el usuario y en la sección "Grupos", selecciona "Cajeros"
4. Guarda los cambios

#### Opción B: Usando Django Shell

```bash
cd src
uv run python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

# Obtener el grupo de Cajeros
cajeros_group = Group.objects.get(name='Cajeros')

# Crear un usuario cajero
cajero = User.objects.create_user(
    username='cajero1',
    password='password123',  # Cambia esto por una contraseña segura
    first_name='Juan',
    last_name='Pérez',
    email='cajero1@example.com'
)

# Agregar al grupo de Cajeros
cajero.groups.add(cajeros_group)

print(f"✅ Usuario cajero '{cajero.username}' creado y agregado al grupo 'Cajeros'")
```

### 3. Verificar el Acceso

1. Ve a: `http://localhost:8000/cash-session/login/`
2. Ingresa las credenciales del cajero
3. Si las credenciales son correctas y el usuario pertenece al grupo "Cajeros", serás redirigido al control de caja

## Flujo de Acceso

```
Usuario intenta acceder a /cash-session/
    ↓
¿Está autenticado?
    NO → Redirige a /cash-session/login/
    SÍ → ¿Pertenece al grupo "Cajeros"?
        NO → Mensaje de error + redirige a login
        SÍ → Acceso permitido ✅
```

## Endpoints

- `/cash-session/login/` - Login de cajeros (GET/POST)
- `/cash-session/logout/` - Cierre de sesión (POST)
- `/cash-session/` - Control de caja (requiere ser cajero)
- `/cash-session/close/` - Cierre de caja (requiere ser cajero)

## Seguridad

- Solo usuarios autenticados y miembros del grupo "Cajeros" pueden acceder al sistema de caja
- El decorador `@cashier_required` protege todas las vistas críticas
- Las credenciales se validan usando el sistema de autenticación de Django
- Los mensajes de error no revelan información sensible sobre usuarios existentes

## Personalización

### Agregar Más Grupos de Acceso

Si necesitas crear más roles (ej: "Supervisores"), edita el decorador en `decorators.py`:

```python
def cashier_or_supervisor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('cash_session:cashier-login')

        # Verificar si pertenece a cualquiera de los grupos permitidos
        if not request.user.groups.filter(
            name__in=['Cajeros', 'Supervisores']
        ).exists():
            messages.error(request, 'No tienes permisos...')
            return redirect('cash_session:cashier-login')

        return view_func(request, *args, **kwargs)
    return wrapper
```

## Troubleshooting

### Error: "No tienes permisos para acceder a esta sección"

**Causa:** El usuario no pertenece al grupo "Cajeros"

**Solución:**
1. Verifica que la fixture se haya cargado: `python manage.py dumpdata auth.group`
2. Asigna el usuario al grupo usando Django Admin o shell

### La página de login no carga los estilos

**Causa:** Tailwind CSS no está disponible desde CDN

**Solución:**
- Verifica tu conexión a internet
- O cambia el CDN por el archivo local de Tailwind en el template
