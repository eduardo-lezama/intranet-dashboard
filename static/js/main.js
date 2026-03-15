/**
 * MAIN.JS - Funcionalidades globales
 */

  // Utilidades globales con rate limiting
const utils = {
  // Rate limiting para prevenir múltiples peticiones rápidas
  pendingRequests: new Map(),
  // Formatear fecha
  formatDate: (date) => {
    const options = { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    };
    return date.toLocaleDateString('es-ES', options);
  },

  // Formatear hora
  formatTime: (date) => {
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  },

  // Determinar saludo según hora
  getGreeting: () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Buenos días';
    if (hour < 19) return 'Buenas tardes';
    return 'Buenas noches';
  },

  // Fetch con manejo de errores mejorado y rate limiting
  async fetchJSON(url, options = {}) {
    // Evitar peticiones duplicadas simultáneas
    if (this.pendingRequests.has(url)) {
      console.log(`⏳ Petición ya en curso: ${url}`);
      return this.pendingRequests.get(url);
    }
    
    const promise = this._doFetch(url, options);
    this.pendingRequests.set(url, promise);
    
    try {
      const result = await promise;
      return result;
    } finally {
      this.pendingRequests.delete(url);
    }
  },
  
  async _doFetch(url, options = {}) {
    try {
      const controller = new AbortController();
      const timeoutMs = typeof options.timeout === 'number' ? options.timeout : 30000;
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
      
      const { timeout, ...fetchOptions } = options;

      const response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('Timeout en petición');
      }
      console.error('Fetch error:', error);
      throw error;
    }
  },

  // Sistema de notificaciones mejorado
  showToast: (message, type = 'info', duration = 3000) => {
    // Crear toast container si no existe
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.style.cssText = `
        position: fixed;
        top: var(--space-lg);
        right: var(--space-lg);
        z-index: var(--z-toast);
        display: flex;
        flex-direction: column;
        gap: var(--space-sm);
      `;
      document.body.appendChild(container);
    }

    // Crear toast
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.style.cssText = `
      background: var(--color-bg-elevated);
      color: var(--color-text-primary);
      padding: var(--space-md);
      border-radius: var(--radius-md);
      border: 1px solid var(--glass-border);
      box-shadow: var(--shadow-lg);
      min-width: 250px;
      transform: translateX(100%);
      transition: transform var(--transition-base);
    `;
    
    toast.innerHTML = `
      <div style="display: flex; align-items: center; gap: var(--space-sm);">
        <span>${message}</span>
        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: inherit; cursor: pointer;">✕</button>
      </div>
    `;

    container.appendChild(toast);
    
    // Animar entrada
    setTimeout(() => toast.style.transform = 'translateX(0)', 10);
    
    // Auto-remover
    setTimeout(() => {
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 250);
    }, duration);
  },

  // Debounce utility
  debounce: (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  // Manejo de errores unificado
  handleError: (error, context = 'Unknown', element = null) => {
    console.error(`❌ Error en ${context}:`, error);
    
    // Mostrar error en UI si hay elemento
    if (element) {
      element.innerHTML = `
        <div class="weather-state weather-state--error">
          <div class="weather-state__icon">⚠️</div>
          <div class="weather-state__content">
            <div class="weather-state__title">Error</div>
            <div class="weather-state__message">${error.message}</div>
          </div>
        </div>
      `;
    }
    
    // Mostrar toast
    utils.showToast(`Error en ${context}: ${error.message}`, 'error');
  }
};

// Exponer utilidades globalmente
window.utils = utils;

// Inicialización cuando el DOM está listo
document.addEventListener('DOMContentLoaded', () => {
  console.log('🏠 Intranet Casa cargada correctamente');
  
  // Añadir listener para links externos
  document.querySelectorAll('a[target="_blank"]').forEach(link => {
    link.addEventListener('click', (e) => {
      console.log(`Abriendo: ${link.href}`);
    });
  });
});

// Manejo de errores global mejorado
window.addEventListener('error', (event) => {
  console.error('Error global capturado:', event.error);
  utils.showToast('Ha ocurrido un error inesperado', 'error');
});

// Manejo de promesas rechazadas no manejadas
window.addEventListener('unhandledrejection', (event) => {
  console.error('Promesa rechazada no manejada:', event.reason);
  utils.showToast('Error en operación asíncrona', 'error');
});

// Service Worker para PWA (opcional - futuro)
if ('serviceWorker' in navigator) {
  // Descomentar cuando quieras añadir PWA
  // navigator.serviceWorker.register('/sw.js');
}
