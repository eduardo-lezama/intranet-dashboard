/**
 * DASHBOARD.JS — Bento 2.0 Dashboard Controller
 * Modular data loading with lazy-init and modal shopping input
 */

class Dashboard {
  constructor() {
    this.intervals = new Set();
    this.serviceCardConfigs = {
      menuProcessor: {
        badgeId: 'menuProcessorBadge',
        badgeTextId: 'menuProcessorBadgeText',
        buttonId: 'menuProcessorButton',
        activeLabel: 'Activo',
        inactiveLabel: 'Inactivo'
      }
    };
    this.init();
  }

  async init() {
    this.updateDateTime();
    this.addInterval(() => this.updateDateTime(), 1000);

    await Promise.allSettled([
      this.loadInitialData(),
      this.loadDocuments()
    ]);

    this.setupEventListeners();
    this.setupServicesPopup();
    this.setupShoppingModal();
  }

  async loadInitialData() {
    try {
      await Promise.all([
        this.loadShoppingList(),
        this.loadDashboardStatus()
      ]);

      await Promise.allSettled([
        this.loadWeatherData(),
        this.loadMealieStats(),
        this.loadPiHoleStats(),
        this.loadEnergyData(),
        this.loadSettleUpData(),
        this.loadDevices()
      ]);
    } catch (error) {
      console.error('Error en carga inicial:', error);
    }
  }

  // ═══════════════ CLOCK ═══════════════
  updateDateTime() {
    const now = new Date();
    const timeEl = document.getElementById('currentTime');
    const dateEl = document.getElementById('currentDate');
    if (timeEl) timeEl.textContent = utils.formatTime(now);
    if (dateEl) dateEl.textContent = utils.formatDate(now);
  }

  // ═══════════════ WEATHER ═══════════════
  async loadWeatherData() {
    const widget = document.getElementById('weatherWidget');
    if (!widget) return;

    try {
      const data = await utils.fetchJSON('/api/weather');

      if (data.error) {
        this.renderWeatherPlaceholder(widget);
        return;
      }

      const currentData = data.current;
      const forecastData = data.forecast;

      // Condensar forecast en 5 días
      const dailyMap = {};
      forecastData.list.forEach(entry => {
        const date = new Date(entry.dt * 1000);
        const dayKey = date.toISOString().slice(0, 10);
        const hour = date.getHours();
        const diffFromNoon = Math.abs(12 - hour);

        if (!dailyMap[dayKey] || diffFromNoon < dailyMap[dayKey].diff) {
          dailyMap[dayKey] = {
            diff: diffFromNoon,
            temp: entry.main.temp,
            weather: entry.weather[0]
          };
        }
      });

      const days = Object.keys(dailyMap).slice(0, 5)
        .map(key => ({ date: key, ...dailyMap[key] }));

      widget.innerHTML = `
        <div class="weather-widget">
          <div class="weather-current">
            <div class="weather-current__icon">${this.getWeatherEmoji(currentData.weather[0].icon)}</div>
            <div class="weather-current__info">
              <div class="weather-current__temp">${Math.round(currentData.main.temp)}°C</div>
              <div class="weather-current__desc">${currentData.weather[0].description}</div>
              <div class="weather-current__details">💧 ${currentData.main.humidity}%  ·  💨 ${Math.round(currentData.wind.speed * 3.6)} km/h</div>
            </div>
          </div>
          <div class="weather-forecast">
            ${days.map(d => {
              const weekday = new Date(d.date).toLocaleDateString('es-ES', { weekday: 'short' });
              return `
                <div class="weather-forecast__day">
                  <div class="weather-forecast__weekday">${weekday}</div>
                  <div class="weather-forecast__temp">${Math.round(d.temp)}°</div>
                  <div class="weather-forecast__icon">${this.getWeatherEmoji(d.weather.icon)}</div>
                </div>`;
            }).join('')}
          </div>
        </div>`;
    } catch (error) {
      utils.handleError(error, 'Weather', widget);
    }
  }

  renderWeatherPlaceholder(widget) {
    widget.innerHTML = `
      <div class="weather-state weather-state--warning">
        <div class="weather-state__icon">🌡️</div>
        <div class="weather-state__content">
          <div class="weather-state__title">API key no configurada</div>
          <div class="weather-state__message">Añade <code>OPENWEATHER_API_KEY</code> en <code>.env</code></div>
          <a href="https://openweathermap.org/api" target="_blank" class="weather-state__link">Obtener API key gratis →</a>
        </div>
      </div>`;
  }

  getWeatherEmoji(iconCode) {
    const map = {
      '01d': '☀️', '01n': '🌙', '02d': '⛅', '02n': '☁️',
      '03d': '☁️', '03n': '☁️', '04d': '☁️', '04n': '☁️',
      '09d': '🌧️', '09n': '🌧️', '10d': '🌦️', '10n': '🌧️',
      '11d': '⛈️', '11n': '⛈️', '13d': '❄️', '13n': '❄️',
      '50d': '🌫️', '50n': '🌫️'
    };
    return map[iconCode] || '🌡️';
  }

  // ═══════════════ DOCUMENTS ═══════════════
  async loadDocuments() {
    const docsTree = document.getElementById('docsTree');
    if (!docsTree) return;

    try {
      const structure = await utils.fetchJSON('/api/docs/structure') || {};

      if (Object.keys(structure).length === 0) {
        docsTree.innerHTML = '<div class="text-muted">No hay documentos disponibles.</div>';
        return;
      }

      docsTree.innerHTML = Object.entries(structure).map(([folder, files]) => `
        <div class="docs-folder" data-folder="${folder}">
          <div class="docs-folder-header" onclick="dashboardInstance.toggleFolder('${folder}')">
            <i class="bi bi-chevron-down"></i>
            <span class="docs-folder-name">${folder}</span>
            <span class="docs-folder-count">${files.length}</span>
          </div>
          <div class="docs-file-list">${this.renderDocumentsTree(files)}</div>
        </div>`).join('');

      document.querySelectorAll('.docs-folder').forEach(f => f.classList.add('collapsed'));
      document.querySelectorAll('.docs-file-list').forEach(l => { l.style.maxHeight = '0'; });
    } catch (error) {
      utils.handleError(error, 'Documents', docsTree);
    }
  }

  renderDocumentsTree(files) {
    const tree = { files: [], folders: {} };
    files.forEach(file => {
      const parts = (file?.name || '').split('/').filter(Boolean);
      if (parts.length <= 1) {
        tree.files.push({ ...file, displayName: parts[0] || file.filename });
        return;
      }
      let node = tree;
      parts.slice(0, -1).forEach(part => {
        if (!node.folders[part]) node.folders[part] = { files: [], folders: {} };
        node = node.folders[part];
      });
      node.files.push({ ...file, displayName: parts[parts.length - 1] });
    });
    return this.renderDocumentNode(tree, 0);
  }

  renderDocumentNode(node, level) {
    const icons = { '.pdf': 'bi-file-earmark-pdf-fill', '.jpg': 'bi-file-earmark-image-fill', '.jpeg': 'bi-file-earmark-image-fill', '.png': 'bi-file-earmark-image-fill', '.txt': 'bi-file-earmark-text-fill' };
    const foldersHtml = Object.entries(node.folders)
      .sort(([a], [b]) => a.localeCompare(b, 'es'))
      .map(([name, child]) => `
        <div class="docs-subfolder"><div class="docs-subfolder-title">📁 ${name}</div>
        <div class="docs-subfolder-content">${this.renderDocumentNode(child, level + 1)}</div></div>`).join('');
    const filesHtml = node.files
      .sort((a, b) => (a.displayName || '').localeCompare(b.displayName || '', 'es'))
      .map(f => `<a href="${f.path}" target="_blank" class="docs-file-item">
        <i class="bi ${icons[f.type] || 'bi-file-earmark-fill'}"></i>
        <span class="docs-file-name">${f.displayName || f.name}</span></a>`).join('');
    return foldersHtml + filesHtml;
  }

  toggleFolder(folderName) {
    const folder = document.querySelector(`.docs-folder[data-folder="${folderName}"]`);
    if (!folder) return;
    const list = folder.querySelector('.docs-file-list');
    folder.classList.toggle('collapsed');
    if (folder.classList.contains('collapsed')) {
      list.style.maxHeight = '0';
    } else {
      list.style.maxHeight = list.scrollHeight + 'px';
    }
  }

  toggleAllFolders() {
    const folders = document.querySelectorAll('.docs-folder');
    const button = document.querySelector('.docs-toggle');
    if (!folders.length || !button) return;
    const allCollapsed = Array.from(folders).every(f => f.classList.contains('collapsed'));

    folders.forEach(folder => {
      const list = folder.querySelector('.docs-file-list');
      if (allCollapsed) {
        folder.classList.remove('collapsed');
        if (list) list.style.maxHeight = list.scrollHeight + 'px';
      } else {
        folder.classList.add('collapsed');
        if (list) list.style.maxHeight = '0';
      }
    });

    const icon = button.querySelector('i');
    if (icon) icon.className = allCollapsed ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
    button.setAttribute('aria-expanded', allCollapsed);
  }

  // ═══════════════ DASHBOARD STATUS ═══════════════
  async loadDashboardStatus() {
    try {
      const piholeData = await utils.fetchJSON('/api/pihole').catch(() => null);
      const wifiEl = document.getElementById('wifiStatus');
      if (wifiEl && piholeData?.raw_data) {
        const active = piholeData.raw_data?.clients?.active ?? 0;
        wifiEl.textContent = `${active} disp.`;
      }

      const serviceChecks = [
        { name: 'Pi-hole', endpoint: '/api/pihole' },
        { name: 'Weather', endpoint: '/api/weather' },
        { name: 'Shopping', endpoint: '/api/shopping' },
        { name: 'Mealie', endpoint: '/api/mealie' },
        { name: 'Energy', endpoint: '/api/energy' },
        { name: 'SettleUp', endpoint: '/api/settleup' },
        { key: 'menuProcessor', name: 'Menu Processor', endpoint: '/api/menu-processor' },
        { name: 'DNSCrypt', endpoint: '/api/dnscrypt' }
      ];

      const checks = await Promise.allSettled(
        serviceChecks.map(s => utils.fetchJSON(s.endpoint, { timeout: 5000 }))
      );

      const results = serviceChecks.map((s, i) => {
        const c = checks[i];
        const ok = c.status === 'fulfilled' && !c.value?.error;
        return { key: s.key, name: s.name, status: ok ? 'ok' : 'error' };
      });

      const okCount = results.filter(r => r.status === 'ok').length;
      const servicesEl = document.getElementById('servicesStatus');
      if (servicesEl) {
        servicesEl.textContent = `${okCount}/${serviceChecks.length}`;
        servicesEl.className = okCount === serviceChecks.length
          ? 'status-pill__value status-pill__value--ok'
          : 'status-pill__value status-pill__value--warning';
      }

      this.renderServicesPopup(results);
      this.syncServiceCardsFromResults(results);
    } catch (error) {
      utils.handleError(error, 'Dashboard Status');
    }
  }

  renderServicesPopup(services) {
    const el = document.getElementById('servicesPopupList');
    if (!el) return;
    el.innerHTML = services.map(s => `
      <li class="services-popup__item">
        <span class="services-popup__name">${s.name}</span>
        <span class="services-popup__status services-popup__status--${s.status}">
          ${s.status === 'ok' ? 'OK' : 'ERROR'}
        </span>
      </li>`).join('');
  }

  syncServiceCardsFromResults(results) {
    const byKey = new Map(results.filter(r => r.key).map(r => [r.key, r]));
    Object.entries(this.serviceCardConfigs).forEach(([key, config]) => {
      const state = byKey.get(key);
      const active = state ? state.status === 'ok' : false;
      this.updateServiceCardState(config, active);
    });
  }

  updateServiceCardState(config, isActive) {
    const badge = document.getElementById(config.badgeId);
    const badgeText = document.getElementById(config.badgeTextId);
    const button = document.getElementById(config.buttonId);

    if (badge) {
      badge.classList.remove('badge--success', 'badge--inactive');
      badge.classList.add(isActive ? 'badge--success' : 'badge--inactive');
    }
    if (badgeText) badgeText.textContent = isActive ? config.activeLabel : config.inactiveLabel;

    if (button) {
      const href = button.dataset.originalHref || button.getAttribute('href') || '';
      if (isActive) {
        if (href) button.setAttribute('href', href);
        button.classList.remove('btn--disabled');
        button.removeAttribute('aria-disabled');
      } else {
        if (href) button.dataset.originalHref = href;
        button.removeAttribute('href');
        button.classList.add('btn--disabled');
        button.setAttribute('aria-disabled', 'true');
      }
    }
  }

  setupServicesPopup() {
    const pill = document.getElementById('servicesPill');
    if (!pill) return;
    pill.addEventListener('click', e => {
      e.stopPropagation();
      pill.setAttribute('aria-expanded', pill.getAttribute('aria-expanded') !== 'true');
    });
    document.addEventListener('click', e => {
      if (!pill.contains(e.target)) pill.setAttribute('aria-expanded', 'false');
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') pill.setAttribute('aria-expanded', 'false');
    });
  }

  // ═══════════════ DEVICES ═══════════════
  async loadDevices() {
    const listEl = document.getElementById('devicesList');
    const countEl = document.getElementById('devicesTotalCount');
    if (!listEl) return;

    try {
      const { devices = [], total = 0 } = await utils.fetchJSON('/api/devices') || {};
      if (countEl) countEl.textContent = total;

      if (devices.length === 0) {
        listEl.innerHTML = '<li class="devices-list__item"><span class="text-muted">Sin dispositivos</span></li>';
        return;
      }

      listEl.innerHTML = devices.map(d => `
        <li class="devices-list__item">
          <div class="devices-list__info">
            <span class="devices-list__icon">${d.icon}</span>
            <span class="devices-list__name">${d.name}</span>
          </div>
          <span class="devices-list__state devices-list__state--${d.status}">${d.state}</span>
        </li>`).join('');
    } catch (error) {
      listEl.innerHTML = '<li class="devices-list__item"><span class="text-muted">Error al cargar</span></li>';
    }
  }

  // ═══════════════ MEALIE ═══════════════
  async loadMealieStats() {
    if (!document.getElementById('mealieStats')) return;
    try {
      const { total_recipes = 0, meals_today = {} } = await utils.fetchJSON('/api/mealie') || {};

      const recipesEl = document.getElementById('mealieRecipesCount');
      const countEl = document.getElementById('mealieMealsTodayCount');
      const listEl = document.getElementById('mealieMealsList');

      if (recipesEl) recipesEl.textContent = total_recipes;

      const flat = Object.entries(meals_today).flatMap(([type, titles]) =>
        titles.map(title => ({ type, title }))
      );
      if (countEl) countEl.textContent = flat.length;

      if (listEl) {
        listEl.innerHTML = flat.length === 0
          ? '<div class="text-muted" style="font-size:var(--text-sm)">Sin plan para hoy</div>'
          : flat.map(m => `<div class="mealie-meal-item"><span class="mealie-meal-type">${m.type}</span><span class="mealie-meal-title">${m.title}</span></div>`).join('');
      }
    } catch (error) {
      utils.handleError(error, 'Mealie');
    }
  }

  // ═══════════════ PI-HOLE ═══════════════
  async loadPiHoleStats() {
    const el = document.getElementById('piholeStats');
    if (!el) return;
    try {
      const data = await utils.fetchJSON('/api/pihole');
      if (!data || data.error) throw new Error(data?.error || 'Sin datos');

      el.innerHTML = `
        <div class="metric metric--center">
          <span class="metric__value metric__value--xl">${data.ads_blocked_today.toLocaleString()}</span>
          <span class="metric__label">Bloqueados hoy</span>
          <span class="metric__change metric__change--positive">${data.ads_percentage_today}%</span>
        </div>
        <div class="metric metric--center" style="margin-top: var(--space-sm);">
          <span class="metric__value">${data.dns_queries_today.toLocaleString()}</span>
          <span class="metric__label">Queries DNS</span>
        </div>`;
    } catch (error) {
      el.innerHTML = `
        <div class="metric metric--center">
          <span class="metric__value">--</span>
          <span class="metric__label">Error conexión</span>
        </div>`;
    }
  }

  // ═══════════════ SETTLE UP ═══════════════
  async loadSettleUpData() {
    try {
      const data = await utils.fetchJSON('/api/settleup') || {};
      const statusEl = document.getElementById('finMainStatus');
      const gastosEl = document.getElementById('finGastosMes');
      if (statusEl && data.status) statusEl.textContent = data.status;
      if (gastosEl) gastosEl.textContent = data.monthly_expenses?.toFixed(2) || '0.00';
    } catch (error) {
      const statusEl = document.getElementById('finMainStatus');
      if (statusEl) statusEl.textContent = 'Error al cargar';
    }
  }

  // ═══════════════ ENERGY ═══════════════
  async loadEnergyData() {
    try {
      const data = await utils.fetchJSON('/api/energy', { timeout: 30000 }) || {};
      const cEl = document.getElementById('energyConsumption');
      const costEl = document.getElementById('energyCost');
      const powerEl = document.getElementById('energyPower');

      if (data.consumption && cEl) cEl.textContent = data.consumption.consumption_kwh || '--';
      if (data.cost && costEl) costEl.textContent = data.cost.cost_eur || '--';
      if (data.current_power && powerEl) powerEl.textContent = data.current_power.power_w || '--';
    } catch (error) {
      ['energyConsumption', 'energyCost', 'energyPower'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '--';
      });
    }
  }

  // ═══════════════ SHOPPING LIST ═══════════════
  async loadShoppingList() {
    const list = document.getElementById('shoppingList');
    if (!list) return;
    try {
      const items = await utils.fetchJSON('/api/shopping') || [];
      if (items.length === 0) {
        list.innerHTML = '<div style="text-align:center;color:var(--color-text-muted);padding:var(--space-lg);font-size:var(--text-sm);">Lista vacía<br><small>Pulsa + para añadir</small></div>';
      } else {
        list.innerHTML = items.map((item, i) => `
          <li class="shopping-item">
            <span>${item.text}</span>
            <button class="btn btn--icon btn--ghost btn--sm" onclick="dashboardInstance.deleteShoppingItem(${i})" title="Eliminar">
              <svg class="icon icon--sm" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </li>`).join('');
      }
    } catch (error) {
      utils.handleError(error, 'Shopping', list);
    }
  }

  // Shopping modal (replaces native prompt)
  setupShoppingModal() {
    const modal = document.getElementById('shoppingModal');
    const input = document.getElementById('shoppingInput');
    const cancelBtn = document.getElementById('shoppingModalCancel');
    const confirmBtn = document.getElementById('shoppingModalConfirm');
    if (!modal || !input) return;

    const open = () => {
      modal.classList.add('shopping-modal--open');
      input.value = '';
      setTimeout(() => input.focus(), 100);
    };

    const close = () => {
      modal.classList.remove('shopping-modal--open');
      input.value = '';
    };

    const submit = () => {
      const text = input.value.trim();
      if (!text) return;
      close();
      utils.fetchJSON('/api/shopping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      }).then(() => {
        this.loadShoppingList();
        utils.showToast('Producto añadido', 'success');
      }).catch(e => utils.handleError(e, 'Add Item'));
    };

    document.getElementById('addShoppingBtn')?.addEventListener('click', open);
    cancelBtn?.addEventListener('click', close);
    confirmBtn?.addEventListener('click', submit);
    input?.addEventListener('keydown', e => { if (e.key === 'Enter') submit(); if (e.key === 'Escape') close(); });
    modal?.addEventListener('click', e => { if (e.target === modal) close(); });
  }

  addShoppingItem() {
    document.getElementById('shoppingModal')?.classList.add('shopping-modal--open');
    setTimeout(() => document.getElementById('shoppingInput')?.focus(), 100);
  }

  deleteShoppingItem(index) {
    utils.fetchJSON('/api/shopping', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ index })
    }).then(() => {
      this.loadShoppingList();
      utils.showToast('Eliminado', 'success');
    }).catch(e => utils.handleError(e, 'Delete Item'));
  }

  // ═══════════════ EVENT LISTENERS ═══════════════
  setupEventListeners() {
    // Refresh data every 10 minutes
    this.addInterval(utils.debounce(() => {
      this.loadWeatherData();
      this.loadMealieStats();
      this.loadPiHoleStats();
      this.loadEnergyData();
    }, 2000), 10 * 60 * 1000);

    // Refresh status every 2 minutes
    this.addInterval(() => this.loadDashboardStatus(), 2 * 60 * 1000);
  }

  // ═══════════════ UTILITIES ═══════════════
  addInterval(callback, delay) {
    const id = setInterval(callback, delay);
    this.intervals.add(id);
    return id;
  }

  destroy() {
    this.intervals.forEach(id => clearInterval(id));
    this.intervals.clear();
  }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('currentTime')) {
    window.dashboardInstance = new Dashboard();
    window.addEventListener('beforeunload', () => dashboardInstance?.destroy());
  }
});
