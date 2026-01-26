# Billing System Skills - Structure Guide

This directory contains modular skills for Claude Code to reference when working on the Django billing system.

## Directory Structure

```
billing-skills/
├── CLAUDE.md                    # Main entry point - read this first
├── README.md                    # This file
│
├── project-context/             # Project structure & dependencies
│   └── SKILL.md
│
├── project-best-practices/      # Philosophy & design patterns
│   └── SKILL.md
│
├── django-backend/              # Backend implementation patterns
│   └── SKILL.md
│
├── frontend-design/             # Frontend patterns & guidelines
│   └── SKILL.md
│
└── afip-integration/            # AFIP/ARCA integration specifics
    └── SKILL.md
```

## Skill Descriptions

### 1. CLAUDE.md
**The main instruction file** - High-level guidance and skill references.
- Quick overview of the project
- Links to all skills
- Core principles summary
- Common commands

### 2. project-context
**Context about the project structure and tech stack**
- Directory structure
- Dependencies and versions
- Package management
- Django apps overview
- Common commands

**When to read:**
- Starting new work on the project
- Need to understand how apps are organized
- Adding dependencies
- Setting up development environment

### 3. project-best-practices
**Development philosophy and design patterns**
- ORM-first approach (mandatory)
- Service layer pattern
- Gang of Four design patterns
- Transaction safety
- Code organization
- Testing philosophy

**When to read:**
- Making architectural decisions
- Implementing new features
- Refactoring existing code
- Need guidance on design patterns
- Writing services or complex business logic

### 4. django-backend
**Concrete backend implementation patterns**
- Model design with examples
- Service layer implementation
- View patterns (HTMX, JSON APIs)
- Query optimization
- Transaction patterns
- Error handling

**When to read:**
- Creating or modifying models
- Writing service methods
- Creating API endpoints
- Optimizing database queries
- Implementing business logic

### 5. frontend-design
**Frontend architecture and strict guidelines**
- **CRITICAL Alpine.js rules** (POS only!)
- HTMX interaction patterns
- "Dumb template" philosophy
- Tailwind CSS patterns
- Component examples
- Responsive design

**When to read:**
- Working on ANY template
- Before adding Alpine.js anywhere
- Creating HTMX interactions
- Styling components
- Building forms or UI elements

### 6. afip-integration
**AFIP/ARCA electronic invoicing integration**
- Complete invoice workflow
- Receipt type determination (A/B/C)
- Tax calculation rules
- CAE emission (DEBUG/PRODUCTION)
- PDF generation
- Email delivery
- Error handling

**When to read:**
- Working on invoice features
- Debugging AFIP issues
- Understanding tax calculations
- Modifying invoice workflow
- Setting up production AFIP

## How to Use These Skills

### For New Features

1. **Read CLAUDE.md** - Get oriented
2. **Identify relevant skills** - Usually 2-3 skills apply
3. **Read those skills thoroughly** - Don't skip this!
4. **Implement following the patterns** - Use examples as templates

### Example: Adding a Customer Search Feature

**Skills to read:**
1. `project-best-practices` - Service layer pattern
2. `django-backend` - Search view implementation
3. `frontend-design` - HTMX search with debouncing

**Implementation:**
```python
# 1. Service (from django-backend skill)
class CustomerService:
    @staticmethod
    def search(query):
        return Customer.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(tax_id__icontains=query)
        )

# 2. View (from django-backend skill)
@login_required
def search_customers(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return render(request, 'customers/_search_results.html', {
            'customers': [], 'message': 'Enter at least 2 characters'
        })
    customers = CustomerService.search(query)
    return render(request, 'customers/_search_results.html', {
        'customers': customers
    })

# 3. Template (from frontend-design skill)
# No Alpine.js! Just HTMX:
<input type="search" 
       hx-get="{% url 'customers:search' %}"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#results">
```

### Example: Modifying Invoice Workflow

**Skills to read:**
1. `afip-integration` - Complete workflow documentation
2. `project-best-practices` - Transaction patterns
3. `django-backend` - Service orchestration

## Skill File Format

Each SKILL.md file follows this structure:

```markdown
---
name: skill-name
description: Brief description
---

# Skill Name

## When to Use This Skill
- Clear indicators of when this skill is relevant

## Main Content
- Organized sections with examples
- Code snippets with ✅/❌ indicators
- Real implementations from the project

## Additional Resources
- Links to other relevant skills
```

## Frontmatter Fields

Skills can include YAML frontmatter:

```yaml
---
name: skill-name
description: What this skill covers
disable-model-invocation: false  # Optional
allowed-tools: Read, Grep        # Optional
---
```

## Supporting Files (Future)

Skills can include additional reference files:

```
my-skill/
├── SKILL.md              # Main skill (required)
├── reference.md          # Detailed reference (optional)
├── examples.md           # More examples (optional)
└── scripts/              # Helper scripts (optional)
    └── helper.py
```

Reference these from SKILL.md:
```markdown
## Additional Resources
- For complete API details, see [reference.md](reference.md)
- For more examples, see [examples.md](examples.md)
```

## Best Practices for Using Skills

### DO:
✅ Read relevant skills BEFORE starting work
✅ Follow patterns from the examples
✅ Read 2-3 related skills for complex features
✅ Reference skills when uncertain
✅ Keep skills under 500 lines (use supporting files for more)

### DON'T:
❌ Skip reading skills and guess
❌ Mix patterns from different paradigms
❌ Add code that violates skill guidelines
❌ Duplicate information across skills

## Updating Skills

When project patterns evolve:

1. Update the relevant SKILL.md file
2. Keep examples consistent with actual code
3. Add new patterns as the project grows
4. Reference real implementations

## Integration with Claude Code

Claude Code will:
1. Start by reading CLAUDE.md
2. Identify relevant skills from the task
3. Read those skills before implementing
4. Follow the patterns and examples
5. Maintain consistency with established patterns

## Questions?

If you need to:
- **Add a new skill** - Create a new directory with SKILL.md
- **Modify existing skill** - Edit the SKILL.md directly
- **Add examples** - Put them in the SKILL.md or create examples.md
- **Add reference docs** - Create supporting .md files in the skill directory

---

**Remember: Skills are living documents. Update them as patterns evolve!**