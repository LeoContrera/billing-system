---
name: frontend-design
description: Frontend patterns and strict guidelines for templates, HTMX, Alpine.js usage, and styling
---

# Frontend Design Skill

This skill defines frontend architecture, component patterns, and strict guidelines for template design.

## When to Use This Skill

Use this skill when you need to:
- Create or modify Django templates
- Implement HTMX interactions
- Use (or decide NOT to use) Alpine.js
- Style components with Tailwind CSS
- Follow frontend best practices

## ⚠️ CRITICAL: Alpine.js Usage Rules

**Alpine.js is ONLY for complex, standalone, single-page interfaces.**

### ✅ WHEN TO USE Alpine.js

**ONE use case: POS (Point of Sale) interface**

The POS is a complex, standalone page that needs:
- Client-side state management (cart, payments, calculations)
- Real-time calculations without server round-trips
- Complex reactive UI (totals, balances, validations)
- Offline-capable functionality

```html
<!-- templates/sale/pos_index.html - Alpine.js IS appropriate here -->
<div x-data="posApp()">
  <div x-text="formatCurrency(total)"></div>
  <button @click="addItem(product)">Add</button>
</div>
```

### ❌ WHEN NOT TO USE Alpine.js

**99% of templates should NOT use Alpine.js.**

For normal pages with HTMX, Alpine.js is NOT needed and should NOT be used:

```html
<!-- ❌ WRONG: Don't do this in regular HTMX templates -->
<div x-data="{ open: false }">
  <button @click="open = !open">Toggle</button>
  <div x-show="open">Content</div>
</div>

<!-- ✅ CORRECT: Use HTMX or CSS for simple interactions -->
<details>
  <summary>Toggle</summary>
  <div>Content</div>
</details>

<!-- ✅ CORRECT: Use HTMX for server interactions -->
<button hx-get="/items" hx-target="#list">Load Items</button>
<div id="list"></div>
```

### The Rule: "Dumb Templates"

**All templates except POS should be "dumb"** - they receive data and display it:

```html
<!-- ✅ CORRECT: Dumb template -->
<div class="card">
  <h2>{{ customer.name }}</h2>
  <p>{{ customer.email }}</p>
  <button hx-get="{% url 'customers:edit' customer.id %}" 
          hx-target="#content">
    Edit
  </button>
</div>
```

**No Alpine.js logic:**
- ❌ No `x-data`
- ❌ No `x-show`/`x-if`
- ❌ No `@click`
- ❌ No client-side state
- ❌ No JavaScript calculations

**Exception**: If you need complex interactivity like POS, then create a NEW standalone page with Alpine.js. Don't add Alpine.js to existing HTMX pages.

## Frontend Stack Overview

### Core Technologies

1. **HTMX** - Server-driven interactions
2. **Alpine.js** - ONLY for complex standalone pages (POS)
3. **Tailwind CSS v4** - Utility-first styling
4. **Flowbite** - Component library

### Configuration Files

```css
/* static/css/input.css - Tailwind v4 source */
@import "tailwindcss";
@plugin "@tailwindcss/typography";
@plugin "flowbite/plugin";

@layer base {
  /* Custom base styles */
}
```

## HTMX Patterns

### Basic HTMX Request

```html
<!-- Load content into target -->
<button hx-get="/endpoint" 
        hx-target="#result"
        hx-swap="innerHTML">
  Load
</button>

<div id="result">
  <!-- Content swapped here -->
</div>
```

### HTMX with POST (Forms)

```html
<form hx-post="{% url 'myapp:create' %}" 
      hx-target="#content"
      hx-swap="innerHTML">
  {% csrf_token %}
  <input type="text" name="name" required>
  <button type="submit">Create</button>
</form>
```

### HTMX Search with Debouncing

```html
<input type="search" 
       name="q"
       hx-get="{% url 'customers:search' %}"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#search-results"
       placeholder="Search customers...">

<div id="search-results">
  <!-- Results appear here -->
</div>
```

### HTMX Indicators (Loading States)

```html
<button hx-get="/slow-endpoint" 
        hx-target="#content"
        hx-indicator="#spinner">
  Load Data
</button>

<div id="spinner" class="htmx-indicator">
  <svg class="animate-spin h-5 w-5" ...>
    <!-- Spinner icon -->
  </svg>
</div>

<style>
.htmx-indicator {
  display: none;
}
.htmx-request .htmx-indicator {
  display: inline-block;
}
</style>
```

### HTMX Modals

```html
<!-- Trigger button -->
<button hx-get="{% url 'products:create-form' %}"
        hx-target="#modal-content"
        hx-swap="innerHTML"
        onclick="document.getElementById('modal').classList.remove('hidden')">
  Create Product
</button>

<!-- Modal container -->
<div id="modal" class="fixed inset-0 bg-black/50 hidden">
  <div class="bg-white p-6 rounded-lg">
    <div id="modal-content">
      <!-- Form loaded here -->
    </div>
  </div>
</div>
```

## Template Patterns

### Base Template Structure

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Billing System{% endblock %}</title>
    
    <!-- Tailwind CSS -->
    <link rel="stylesheet" href="{% static 'css/output.css' %}">
    
    <!-- HTMX -->
    <script src="{% static 'js/htmx.min.js' %}" defer></script>
    
    <!-- Flowbite (if needed for this page) -->
    {% block extra_head %}{% endblock %}
</head>
<body class="bg-gray-50">
    <!-- Navbar -->
    <nav class="bg-white shadow">
        <!-- Navigation content -->
    </nav>
    
    <!-- Main content -->
    <main class="container mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>
    
    <!-- HTMX Configuration -->
    <script>
        document.body.addEventListener('htmx:configRequest', (event) => {
            event.detail.headers['X-CSRFToken'] = '{{ csrf_token }}';
        });
    </script>
    
    {% block extra_scripts %}{% endblock %}
</body>
</html>
```

### List View Template

```html
<!-- templates/customers/customer_list.html -->
{% extends "base.html" %}

{% block content %}
<div class="space-y-6">
    <!-- Header with search -->
    <div class="flex justify-between items-center">
        <h1 class="text-2xl font-bold">Customers</h1>
        
        <!-- Search input with HTMX -->
        <input type="search"
               name="q"
               hx-get="{% url 'customers:search' %}"
               hx-trigger="keyup changed delay:300ms"
               hx-target="#customer-list"
               placeholder="Search..."
               class="px-4 py-2 border rounded-lg">
    </div>
    
    <!-- List container (HTMX target) -->
    <div id="customer-list">
        {% include "customers/_customer_list_partial.html" %}
    </div>
</div>
{% endblock %}
```

### Partial Template (HTMX Response)

```html
<!-- templates/customers/_customer_list_partial.html -->
{% if customers %}
    <div class="grid gap-4">
        {% for customer in customers %}
        <div class="bg-white p-4 rounded-lg shadow">
            <h3 class="font-semibold">{{ customer.first_name }} {{ customer.last_name }}</h3>
            <p class="text-gray-600">{{ customer.email }}</p>
            <p class="text-sm text-gray-500">{{ customer.tax_id }}</p>
            
            <div class="mt-4 flex gap-2">
                <button hx-get="{% url 'customers:detail' customer.id %}"
                        hx-target="#main-content"
                        class="text-blue-600 hover:text-blue-800">
                    View Details
                </button>
                <button hx-get="{% url 'customers:edit-form' customer.id %}"
                        hx-target="#modal-content"
                        class="text-gray-600 hover:text-gray-800">
                    Edit
                </button>
            </div>
        </div>
        {% endfor %}
    </div>
{% else %}
    <div class="text-center py-12 text-gray-500">
        No customers found
    </div>
{% endif %}
```

### Form Template

```html
<!-- templates/customers/_customer_form.html -->
<form hx-post="{% url 'customers:create' %}"
      hx-target="#customer-list"
      class="space-y-4">
    {% csrf_token %}
    
    <div>
        <label class="block text-sm font-medium text-gray-700">
            First Name
        </label>
        <input type="text" 
               name="first_name" 
               required
               class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
    </div>
    
    <div>
        <label class="block text-sm font-medium text-gray-700">
            Email
        </label>
        <input type="email" 
               name="email"
               class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
    </div>
    
    <div class="flex gap-2">
        <button type="submit" 
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Create Customer
        </button>
        <button type="button"
                onclick="document.getElementById('modal').classList.add('hidden')"
                class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
            Cancel
        </button>
    </div>
</form>
```

### Detail View Template

```html
<!-- templates/customers/customer_detail.html -->
{% extends "base.html" %}

{% block content %}
<div class="bg-white rounded-lg shadow p-6">
    <!-- Header -->
    <div class="flex justify-between items-start mb-6">
        <div>
            <h1 class="text-3xl font-bold">
                {{ customer.first_name }} {{ customer.last_name }}
            </h1>
            <p class="text-gray-500">{{ customer.get_tax_category_display }}</p>
        </div>
        
        <button hx-get="{% url 'customers:edit-form' customer.id %}"
                hx-target="#edit-modal"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Edit
        </button>
    </div>
    
    <!-- Details grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
            <h3 class="text-sm font-medium text-gray-500">Contact Information</h3>
            <dl class="mt-2 space-y-2">
                <div>
                    <dt class="text-sm text-gray-500">Email</dt>
                    <dd class="text-base">{{ customer.email|default:"—" }}</dd>
                </div>
                <div>
                    <dt class="text-sm text-gray-500">Phone</dt>
                    <dd class="text-base">{{ customer.phone|default:"—" }}</dd>
                </div>
            </dl>
        </div>
        
        <div>
            <h3 class="text-sm font-medium text-gray-500">Fiscal Information</h3>
            <dl class="mt-2 space-y-2">
                <div>
                    <dt class="text-sm text-gray-500">Tax ID</dt>
                    <dd class="text-base">{{ customer.tax_id }}</dd>
                </div>
                <div>
                    <dt class="text-sm text-gray-500">Category</dt>
                    <dd class="text-base">{{ customer.get_tax_category_display }}</dd>
                </div>
            </dl>
        </div>
    </div>
    
    <!-- Related sales section (loaded via HTMX) -->
    <div class="mt-8">
        <h2 class="text-xl font-semibold mb-4">Recent Sales</h2>
        <div hx-get="{% url 'customers:sales' customer.id %}"
             hx-trigger="load"
             hx-indicator="#sales-loading"
             id="customer-sales">
            <div id="sales-loading" class="text-center py-4">
                Loading sales...
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## Tailwind CSS Patterns

### Design System Variables

```html
<!-- Typography -->
<h1 class="text-3xl font-bold">Main Heading</h1>
<h2 class="text-2xl font-semibold">Section Heading</h2>
<h3 class="text-xl font-medium">Subsection</h3>
<p class="text-base text-gray-700">Body text</p>
<p class="text-sm text-gray-500">Small text</p>

<!-- Colors (Project Palette) -->
<button class="bg-blue-600 hover:bg-blue-700">Primary Action</button>
<button class="bg-amber-500 hover:bg-amber-600">Warning/Discount</button>
<button class="bg-green-500 hover:bg-green-600">Success</button>
<button class="bg-red-500 hover:bg-red-600">Danger/Delete</button>

<!-- Spacing -->
<div class="space-y-4">     <!-- Vertical spacing between children -->
<div class="space-x-4">     <!-- Horizontal spacing -->
<div class="p-6">           <!-- Padding -->
<div class="m-4">           <!-- Margin -->

<!-- Shadows -->
<div class="shadow">        <!-- Small shadow -->
<div class="shadow-md">     <!-- Medium shadow -->
<div class="shadow-lg">     <!-- Large shadow -->
```

### Card Component Pattern

```html
<div class="bg-white rounded-lg shadow p-6">
    <h3 class="text-lg font-semibold mb-4">Card Title</h3>
    <p class="text-gray-600">Card content</p>
</div>
```

### Button Patterns

```html
<!-- Primary button -->
<button class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
    Primary Action
</button>

<!-- Secondary button -->
<button class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition">
    Secondary Action
</button>

<!-- Danger button -->
<button class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition">
    Delete
</button>

<!-- Disabled button -->
<button disabled class="px-4 py-2 bg-gray-300 text-gray-500 rounded-lg cursor-not-allowed">
    Disabled
</button>
```

### Form Input Patterns

```html
<!-- Text input -->
<input type="text"
       class="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">

<!-- Select dropdown -->
<select class="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
    <option>Option 1</option>
    <option>Option 2</option>
</select>

<!-- Textarea -->
<textarea rows="4"
          class="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
</textarea>

<!-- Checkbox -->
<input type="checkbox"
       class="rounded border-gray-300 text-blue-600 focus:ring-blue-500">
```

### Table Pattern

```html
<div class="overflow-x-auto">
    <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
            <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                </th>
            </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
            {% for customer in customers %}
            <tr>
                <td class="px-6 py-4 whitespace-nowrap">
                    {{ customer.first_name }} {{ customer.last_name }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    {{ customer.email }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <a href="#" class="text-blue-600 hover:text-blue-900">Edit</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
```

### Badge/Pill Pattern

```html
<!-- Status badges -->
<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
    Completed
</span>

<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
    Pending
</span>

<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
    Rejected
</span>
```

## Responsive Design Patterns

### Mobile-First Approach

```html
<!-- Stack on mobile, grid on desktop -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <!-- Cards -->
</div>

<!-- Hidden on mobile, visible on desktop -->
<div class="hidden md:block">
    <!-- Desktop-only content -->
</div>

<!-- Visible on mobile, hidden on desktop -->
<div class="md:hidden">
    <!-- Mobile-only content -->
</div>

<!-- Different text sizes for mobile/desktop -->
<h1 class="text-2xl md:text-3xl lg:text-4xl">
    Responsive Heading
</h1>
```

## Flowbite Components

Use Flowbite for complex components like modals, dropdowns:

```html
<!-- Flowbite Modal -->
<button data-modal-target="default-modal" 
        data-modal-toggle="default-modal" 
        type="button"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg">
    Toggle modal
</button>

<div id="default-modal" 
     tabindex="-1" 
     aria-hidden="true" 
     class="hidden overflow-y-auto overflow-x-hidden fixed top-0 right-0 left-0 z-50 justify-center items-center w-full md:inset-0 h-[calc(100%-1rem)] max-h-full">
    <div class="relative p-4 w-full max-w-2xl max-h-full">
        <div class="relative bg-white rounded-lg shadow">
            <!-- Modal content -->
        </div>
    </div>
</div>

{% block extra_scripts %}
<script src="{% static 'js/flowbite.min.js' %}"></script>
{% endblock %}
```

## Alpine.js for POS ONLY

**Remember: This is ONLY for the POS interface.**

```html
<!-- templates/sale/pos_index.html -->
<div x-data="posApp()" class="container mx-auto p-4">
    <!-- Product search -->
    <input type="text" 
           x-model="searchQuery"
           @input.debounce.300ms="searchProducts()"
           placeholder="Search products...">
    
    <!-- Cart -->
    <div class="mt-4">
        <h2 class="text-xl font-bold">Cart</h2>
        <template x-for="item in lineItems" :key="item.id">
            <div class="flex justify-between items-center p-2 border-b">
                <span x-text="item.product.name"></span>
                <span x-text="formatCurrency(item.total)"></span>
                <button @click="removeItem(item.id)">Remove</button>
            </div>
        </template>
    </div>
    
    <!-- Totals -->
    <div class="mt-4 text-right">
        <div>Subtotal: <span x-text="formatCurrency(subtotal)"></span></div>
        <div>Discount: <span x-text="formatCurrency(globalDiscount)"></span></div>
        <div class="text-2xl font-bold">
            Total: <span x-text="formatCurrency(total)"></span>
        </div>
    </div>
</div>

<script>
function posApp() {
    return {
        lineItems: [],
        searchQuery: '',
        globalDiscountPercent: 0,
        
        get subtotal() {
            return this.lineItems.reduce((sum, item) => 
                sum + (item.quantity * item.unit_price - item.discount_amount), 0
            );
        },
        
        get globalDiscount() {
            return this.subtotal * (this.globalDiscountPercent / 100);
        },
        
        get total() {
            return this.subtotal - this.globalDiscount;
        },
        
        formatCurrency(value) {
            return new Intl.NumberFormat('es-AR', {
                style: 'currency',
                currency: 'ARS'
            }).format(value);
        }
    };
}
</script>
```

## Additional Resources

For related information, see:
- [project-best-practices](../project-best-practices/SKILL.md) - General design principles
- [project-context](../project-context/SKILL.md) - Frontend stack details
- [django-backend](../django-backend/SKILL.md) - Backend view patterns