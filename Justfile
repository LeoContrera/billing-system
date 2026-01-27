# Cross-platform shell configuration
# Windows users: Install Git Bash for full compatibility
# Most commands work with PowerShell, but some require bash
set shell := if os() == "windows" { ["powershell.exe", "-NoLogo", "-Command"] } else { ["bash", "-c"] }

default:
    @just --list

# Run Django development server
run:
    uv run python src/manage.py runserver

# Watch and rebuild CSS on changes (cross-platform)
watch-css:
    pnpm dlx @tailwindcss/cli -i ./static/css/input.css -o ./static/css/output.css --watch

# Build and minify CSS for production (cross-platform)
build-css:
    pnpm dlx @tailwindcss/cli -i ./static/css/input.css -o ./static/css/output.css --minify

# AFIP Testing Recipes
# Note: These commands use Python file execution instead of shell redirection for cross-platform compatibility

# Run AFIP quick test
test-afip-quick:
    @echo "Running AFIP Quick Test..."
    uv run python -c "import sys; sys.path.insert(0, 'src'); import django; django.setup(); exec(open('documentation/quick-test-afip.py').read())"

# Run complete AFIP invoicing example
test-afip-example:
    @echo "Running AFIP Full Example..."
    @echo "Ejecutando ejemplo_completo_facturacion()..."
    uv run python -c "import sys; sys.path.insert(0, 'src'); import django; django.setup(); exec(open('documentation/example-afip-usage.py').read()); ejemplo_completo_facturacion()"

# Open Django shell with AFIP examples preloaded
test-afip-shell:
    @echo "Opening Django shell with AFIP examples loaded..."
    @echo "Available functions:"
    @echo "  - ejemplo_completo_facturacion()"
    @echo "  - ejemplo_flujo_paso_a_paso()"
    @echo "  - ejemplo_reintentar_envio_email()"
    @echo "  - ejemplo_consultar_factura()"
    uv run python src/manage.py shell -c "exec(open('documentation/example-afip-usage.py').read())"

# Django management commands (cross-platform)
migrate:
    uv run python src/manage.py migrate

makemigrations:
    uv run python src/manage.py makemigrations

shell:
    uv run python src/manage.py shell

# Create Django superuser
createsuperuser:
    uv run python src/manage.py createsuperuser

# Load fixtures
loaddata fixture:
    uv run python src/manage.py loaddata {{fixture}}

# Run tests
test:
    uv run python src/manage.py test

# Code quality
lint:
    uv run ruff check

format:
    uv run ruff format

# Check for common issues
check:
    uv run python src/manage.py check
