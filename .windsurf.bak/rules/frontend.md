---
trigger: model_decision
description: Aplicar cuando se trabajen archivos en static/js/, static/css/, o templates/
---

# Frontend - JavaScript y CSS

## Estructura JavaScript

```
static/js/
├── main.js       # Utilidades globales (utils object)
└── dashboard.js  # Clase Dashboard (widgets, data loading)
```

## Patrón de Widget en Dashboard

```javascript
// En dashboard.js - método para cargar datos
async loadNuevoWidget() {
  const container = document.getElementById('nuevoWidget');
  if (!container) return;

  try {
    const data = await utils.fetchJSON('/api/nuevo', { timeout: 15000 });
    
    if (data.error) {
      this.renderWidgetError(container, data.error);
      return;
    }
    
    container.innerHTML = `
      <div class="metric">
        <span class="metric__value">${data.valor}</span>
        <span class="metric__label">${data.label}</span>
      </div>
    `;
  } catch (error) {
    utils.handleError(error, 'NuevoWidget', container);
  }
}
```

## Utilidades Disponibles (main.js)

```javascript
utils.fetchJSON(url, options)     // Fetch con timeout y rate limiting
utils.formatDate(date)            // Formato español: "miércoles, 12 de marzo"
utils.formatTime(date)            // Formato 24h: "19:30"
utils.getGreeting()               // "Buenos días/tardes/noches"
utils.showToast(msg, type, ms)    // Notificaciones toast
utils.debounce(fn, wait)          // Debounce utility
utils.handleError(err, ctx, el)   // Manejo unificado de errores
```

## Estructura CSS (BEM)

```css
/* Bloque */
.card { }

/* Elemento */
.card__header { }
.card__content { }
.card__footer { }

/* Modificador */
.card--highlighted { }
.card__header--compact { }
```

## Variables CSS Principales

```css
/* Colores */
--color-bg-primary: #0E1A1A;
--color-bg-secondary: #132222;
--color-text-primary: #F4F4F4;
--color-accent-primary: #E4981E;

/* Estados */
--color-success: #4ADE80;
--color-warning: #FACC15;
--color-error: #EF4444;

/* Espaciado */
--space-sm: 0.75rem;
--space-md: 1rem;
--space-lg: 1.5rem;

/* Radios */
--radius-md: 0.75rem;
--radius-lg: 1rem;
```

## Rutas de Archivos

- **Nuevo widget JS**: Añadir método en `static/js/dashboard.js`
- **Nueva utilidad**: Añadir a `utils` en `static/js/main.js`
- **Nuevos estilos**: `static/css/components.css` o `dashboard.css`
- **Nuevas variables**: `static/css/variables.css`
- **Nuevo template**: `templates/` + extender `base.html`

## Antipatrones Frontend

❌ Usar `var` - usar `const`/`let`
❌ Callbacks anidados - usar `async/await`
❌ Estilos inline - usar clases CSS
❌ IDs duplicados en HTML
❌ Fetch sin timeout - usar `utils.fetchJSON()`
