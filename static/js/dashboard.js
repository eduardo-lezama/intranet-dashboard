class Dashboard {
  constructor() {
    this.intervals = new Set(); // Track all intervals for cleanup
    this.serviceCardConfigs = {
      menuProcessor: {
        badgeId: 'menuProcessorBadge',
        badgeTextId: 'menuProcessorBadgeText',
        buttonId: 'menuProcessorButton',
        activeLabel: 'Activo',
        inactiveLabel: 'Desactivado'
      }
    };
    this.init();
  }

  async init() {
    console.log('📊 Inicializando dashboard...');
    
    // Actualizar reloj y fecha
    this.updateDateTime();
    this.addInterval(() => this.updateDateTime(), 1000);

    // Cargar dashboard y documentos en paralelo para evitar bloqueos
    await Promise.allSettled([
      this.loadInitialData(),
      this.loadDocuments()
    ]);

    // Event listeners
    this.setupEventListeners();
    
    // Setup popup de servicios (hover/click)
    this.setupServicesPopup();
  }

  async loadInitialData() {
    console.log('🚀 Iniciando carga secuencial de datos...');
    
    try {
      // 1. Cargar datos rápidos primero (sin dependencias externas)
      await Promise.all([
        this.loadShoppingList(),
        this.loadDashboardStatus()
      ]);
      
      // 2. Cargar APIs externas en paralelo pero con timeout individual
      await Promise.allSettled([
        this.loadWeatherData(),
        this.loadMealieStats(),
        this.loadPiHoleStats(),
        this.loadEnergyData(),
        this.loadSettleUpData(),
        this.loadDevices()
      ]);
      
      console.log('✅ Todos los datos cargados');
    } catch (error) {
      console.error('❌ Error en carga inicial:', error);
    }
  }

  // ========== RELOJ Y FECHA ==========
  updateDateTime() {
    const now = new Date();
    
    const timeElement = document.getElementById('currentTime');
    const dateElement = document.getElementById('currentDate');
    
    if (timeElement) {
      timeElement.textContent = utils.formatTime(now);
    }
    
    if (dateElement) {
      dateElement.textContent = utils.formatDate(now);
    }
  }
  
  
  // ========== CLIMA ==========
  async loadWeatherData() {
    const weatherWidget = document.getElementById('weatherWidget');
    if (!weatherWidget) return;

    const apiKey  = weatherWidget.dataset.apiKey || '';
    const city    = weatherWidget.dataset.city || 'Manresa';
    const country = weatherWidget.dataset.country || 'ES';

    if (!apiKey || apiKey.trim() === '') {
      this.renderWeatherPlaceholder(weatherWidget);
      return;
    }

    try {
      // 1) Tiempo actual
      const currentUrl = `https://api.openweathermap.org/data/2.5/weather?q=${city},${country}&appid=${apiKey}&units=metric&lang=es`;

      // 2) Forecast 5 días (cada 3 horas)
      const forecastUrl = `https://api.openweathermap.org/data/2.5/forecast?q=${city},${country}&appid=${apiKey}&units=metric&lang=es`;

      const [currentRes, forecastRes] = await Promise.allSettled([
        fetch(currentUrl, {signal: AbortSignal.timeout(10000)}),
        fetch(forecastUrl, {signal: AbortSignal.timeout(10000)})
      ]);

      if (currentRes.status === 'rejected') throw new Error(`Current API failed: ${currentRes.reason}`);
      if (forecastRes.status === 'rejected') throw new Error(`Forecast API failed: ${forecastRes.reason}`);
      if (!currentRes.value.ok) throw new Error(`Current HTTP ${currentRes.value.status}`);
      if (!forecastRes.value.ok) throw new Error(`Forecast HTTP ${forecastRes.value.status}`);

      const currentData  = await currentRes.value.json();
      const forecastData = await forecastRes.value.json();

      // Condensar forecast en 5 días (aprox. mediodía de cada día)
      const dailyMap = {};
      forecastData.list.forEach(entry => {
        const date = new Date(entry.dt * 1000);
        const dayKey = date.toISOString().slice(0, 10); // YYYY-MM-DD

        // Elegimos las horas alrededor de las 12:00 para cada día
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

      const days = Object.keys(dailyMap)
        .slice(0, 5)
        .map(key => ({ date: key, ...dailyMap[key] }));

      // Render principal + 5 días con clases CSS
      weatherWidget.innerHTML = `
        <div class="weather-widget">
          <!-- Bloque actual -->
          <div class="weather-current">
            <div class="weather-current__icon">
              ${this.getWeatherEmoji(currentData.weather[0].icon)}
            </div>
            <div class="weather-current__info">
              <div class="weather-current__temp">
                ${Math.round(currentData.main.temp)}°C
              </div>
              <div class="weather-current__desc">
                ${currentData.weather[0].description}
              </div>
              <div class="weather-current__details">
                💧 ${currentData.main.humidity}% • 💨 ${Math.round(currentData.wind.speed * 3.6)} km/h
              </div>
            </div>
          </div>

          <!-- Mini predicción 5 días -->
          <div class="weather-forecast">
            ${days.map(d => {
              const date = new Date(d.date);
              const weekday = date.toLocaleDateString('es-ES', { weekday: 'short' });
              return `
                <div class="weather-forecast__day">
                  <div class="weather-forecast__weekday">
                    ${weekday}
                  </div>
                  <div class="weather-forecast__temp">
                    ${Math.round(d.temp)}°C
                  </div>
                  <div class="weather-forecast__icon">
                    ${this.getWeatherEmoji(d.weather.icon)}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;

      console.log('✅ Clima + forecast cargados');
    } catch (error) {
      console.error('❌ Error cargando clima:', error);
      utils.handleError(error, 'Weather API', weatherWidget);
    }
  }


renderWeatherPlaceholder(weatherWidget) {
  weatherWidget.innerHTML = `
    <div class="weather-state weather-state--warning">
      <div class="weather-state__icon">🌡️</div>
      <div class="weather-state__content">
        <div class="weather-state__title">Configura API key de OpenWeatherMap</div>
        <div class="weather-state__message">
          Añade <code>OPENWEATHER_API_KEY</code> en el archivo <code>.env</code>
        </div>
        <a href="https://openweathermap.org/api" target="_blank" class="weather-state__link">
          Obtener API key gratis
          <svg class="icon icon--sm" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
          </svg>
        </a>
      </div>
    </div>
  `;
}

// Eliminado - ahora usa utils.handleError

  getWeatherEmoji(iconCode) {
    const emojiMap = {
      '01d': '☀️', '01n': '🌙',
      '02d': '⛅', '02n': '☁️',
      '03d': '☁️', '03n': '☁️',
      '04d': '☁️', '04n': '☁️',
      '09d': '🌧️', '09n': '🌧️',
      '10d': '🌦️', '10n': '🌧️',
      '11d': '⛈️', '11n': '⛈️',
      '13d': '❄️', '13n': '❄️',
      '50d': '🌫️', '50n': '🌫️'
    };
    return emojiMap[iconCode] || '🌡️';
  }

  // ========== DOCUMENTOS ==========
  async loadDocuments() {
    const docsTree = document.getElementById('docsTree');
    if (!docsTree) return;

    try {
      const resp = await utils.fetchJSON('/api/docs/structure');
      const structure = resp || {};

      if (Object.keys(structure).length === 0) {
        docsTree.innerHTML = '<div class="text-muted">No hay documentos disponibles.</div>';
        return;
      }

      const html = Object.entries(structure).map(([folder, files]) => `
        <div class="docs-folder" data-folder="${folder}">
          <div class="docs-folder-header" onclick="dashboardInstance.toggleFolder('${folder}')">
            <i class="bi bi-chevron-down"></i>
            <span class="docs-folder-name">${folder}</span>
            <span class="docs-folder-count">${files.length}</span>
          </div>
          <div class="docs-file-list">
            ${this.renderDocumentsTree(files)}
          </div>
        </div>
      `).join('');

      docsTree.innerHTML = html;

      // Inicializar carpetas colapsadas por defecto
      document.querySelectorAll('.docs-folder').forEach(folder => {
        folder.classList.add('collapsed');
      });

      // Inicializar altura para animaciones
      document.querySelectorAll('.docs-file-list').forEach(list => {
        list.style.maxHeight = '0';
      });

      console.log('✅ Documentos cargados:', structure);
    } catch (error) {
      utils.handleError(error, 'Documents API', docsTree);
    }
  }

  toggleAllFolders() {
    const folders = document.querySelectorAll('.docs-folder');
    const button = document.querySelector('.docs-toggle');
    const icon = button.querySelector('i');
    
    if (!folders.length || !button || !icon) return;

    // Verificar si todas están colapsadas
    const allCollapsed = Array.from(folders).every(folder => folder.classList.contains('collapsed'));
    
    if (allCollapsed) {
      // Expandir todas
      folders.forEach(folder => {
        folder.classList.remove('collapsed');
        const list = folder.querySelector('.docs-file-list');
        if (list) {
          list.style.maxHeight = list.scrollHeight + 'px';
        }
      });
      icon.className = 'bi bi-chevron-up';
      button.setAttribute('aria-expanded', 'true');
    } else {
      // Colapsar todas
      folders.forEach(folder => {
        folder.classList.add('collapsed');
        const list = folder.querySelector('.docs-file-list');
        if (list) {
          list.style.maxHeight = '0';
        }
      });
      icon.className = 'bi bi-chevron-down';
      button.setAttribute('aria-expanded', 'false');
    }
  }

  getFileIcon(type) {
    const icons = {
      '.pdf': 'bi-file-earmark-pdf-fill',
      '.jpg': 'bi-file-earmark-image-fill',
      '.jpeg': 'bi-file-earmark-image-fill',
      '.png': 'bi-file-earmark-image-fill',
      '.txt': 'bi-file-earmark-text-fill'
    };
    return icons[type] || 'bi-file-earmark-fill';
  }

  renderDocumentsTree(files) {
    const tree = { files: [], folders: {} };

    files.forEach(file => {
      const rawName = file?.name || '';
      const parts = rawName.split('/').filter(Boolean);

      if (parts.length <= 1) {
        tree.files.push({ ...file, displayName: rawName || file.filename });
        return;
      }

      let node = tree;
      const folderParts = parts.slice(0, -1);
      const fileName = parts[parts.length - 1];

      folderParts.forEach(part => {
        if (!node.folders[part]) {
          node.folders[part] = { files: [], folders: {} };
        }
        node = node.folders[part];
      });

      node.files.push({ ...file, displayName: fileName });
    });

    return this.renderDocumentNode(tree, 0);
  }

  renderDocumentNode(node, level) {
    const foldersHtml = Object.entries(node.folders)
      .sort(([a], [b]) => a.localeCompare(b, 'es', { sensitivity: 'base' }))
      .map(([folderName, childNode]) => `
        <div class="docs-subfolder docs-subfolder--level-${level}">
          <div class="docs-subfolder-title">📁 ${folderName}</div>
          <div class="docs-subfolder-content">
            ${this.renderDocumentNode(childNode, level + 1)}
          </div>
        </div>
      `)
      .join('');

    const filesHtml = node.files
      .sort((a, b) => (a.displayName || '').localeCompare((b.displayName || ''), 'es', { sensitivity: 'base' }))
      .map(file => `
        <a href="${file.path}" target="_blank" class="docs-file-item">
          <i class="bi ${this.getFileIcon(file.type)}"></i>
          <span class="docs-file-name">${file.displayName || file.name}</span>
        </a>
      `)
      .join('');

    return `${foldersHtml}${filesHtml}`;
  }

  toggleFolder(folderName) {
    const folder = document.querySelector(`.docs-folder[data-folder="${folderName}"]`);
    if (!folder) return;
    
    const list = folder.querySelector('.docs-file-list');
    const icon = folder.querySelector('.docs-folder-header i');
    
    if (!list || !icon) return;
    
    folder.classList.toggle('collapsed');
    
    if (folder.classList.contains('collapsed')) {
      // Colapsar
      list.style.maxHeight = '0';
      icon.style.transform = 'rotate(-90deg)';
    } else {
      // Expandir
      list.style.maxHeight = list.scrollHeight + 'px';
      icon.style.transform = 'rotate(0deg)';
    }
  }

  toggleDocsTree() {
    const tree = document.getElementById('docsTree');
    const button = document.querySelector('.docs-toggle');
    if (!tree || !button) return;

    const isHidden = tree.style.display === 'none';
    
    // Toggle visibility
    tree.style.display = isHidden ? 'block' : 'none';
    
    // Update ARIA
    button.setAttribute('aria-expanded', isHidden);
    
    // Update icon
    const chevron = button.textContent.trim();
    button.textContent = isHidden ? '▼' : '▲';
  }

// ========== DASHBOARD STATUS ==========
async loadDashboardStatus() {
  try {
    // 1. WiFi devices (Pi-hole)
    const { raw_data: piholeData } = await utils.fetchJSON('/api/pihole') || {};
    
    const wifiEl = document.getElementById('wifiStatus');
    if (wifiEl) {
      const active = piholeData?.clients?.active ?? 0;
      wifiEl.textContent = `${active} dispositivos`;
    }
      
    // 2. Health check de todos los servicios
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
    
    // Mapear resultados con estado individual
    const serviceResults = serviceChecks.map((service, index) => {
      const check = checks[index];
      const isOk = check.status === 'fulfilled' && !check.value?.error;
      return {
        key: service.key,
        name: service.name,
        status: isOk ? 'ok' : 'error',
        error: !isOk ? (check.reason?.message || check.value?.error || 'Error') : null
      };
    });
      
    const okServices = serviceResults.filter(s => s.status === 'ok').length;
    const totalServices = serviceChecks.length;
    
    // Actualizar pill principal
    const servicesEl = document.getElementById('servicesStatus');
    if (servicesEl) {
      const statusText = okServices === totalServices ? 'OK' : 'WARN';
      servicesEl.textContent = `${okServices}/${totalServices} ${statusText}`;
      servicesEl.className = okServices === totalServices 
        ? 'status-pill__value status-pill__value--ok'
        : 'status-pill__value status-pill__value--warning';
    }
    
    // Renderizar popup con detalle de cada servicio
    this.renderServicesPopup(serviceResults);
    this.syncServiceCardsFromResults(serviceResults);
      
    // 3. QNAP status (simulado)
    const qnapEl = document.getElementById('qnapStatus');
    if (qnapEl) {
      qnapEl.textContent = 'Online';
    }
      
  } catch (error) {
    utils.handleError(error, 'Dashboard Status');
  }
}

// Renderizar popup de servicios
renderServicesPopup(services) {
  const listEl = document.getElementById('servicesPopupList');
  if (!listEl) return;
  
  listEl.innerHTML = services.map(service => `
    <li class="services-popup__item">
      <span class="services-popup__name">${service.name}</span>
      <span class="services-popup__status services-popup__status--${service.status}">
        ${service.status === 'ok' ? 'OK' : 'ERROR'}
      </span>
    </li>
  `).join('');
}

syncServiceCardsFromResults(serviceResults) {
  const statusByKey = new Map(
    serviceResults
      .filter(service => service.key)
      .map(service => [service.key, service])
  );

  Object.entries(this.serviceCardConfigs).forEach(([serviceKey, config]) => {
    const serviceState = statusByKey.get(serviceKey);
    const isActive = serviceState ? serviceState.status === 'ok' : false;
    this.updateServiceCardState(config, isActive);
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

  if (badgeText) {
    badgeText.textContent = isActive ? config.activeLabel : config.inactiveLabel;
  }

  this.setServiceActionState(button, isActive);
}

setServiceActionState(button, isActive) {
  if (!button) return;

  const originalHref = button.dataset.originalHref || button.getAttribute('href') || '';

  if (isActive) {
    if (originalHref) {
      button.setAttribute('href', originalHref);
    }
    button.classList.remove('btn--disabled');
    button.removeAttribute('aria-disabled');
    button.removeAttribute('tabindex');
    button.removeAttribute('title');
    return;
  }

  if (originalHref) {
    button.dataset.originalHref = originalHref;
  }
  button.removeAttribute('href');
  button.classList.add('btn--disabled');
  button.setAttribute('aria-disabled', 'true');
  button.setAttribute('tabindex', '-1');
  button.setAttribute('title', 'Servicio desactivado manualmente en NAS');
}

// Setup del popup de servicios (toggle para mobile)
setupServicesPopup() {
  const pill = document.getElementById('servicesPill');
  if (!pill) return;
  
  // Toggle para mobile (click)
  pill.addEventListener('click', (e) => {
    // Evitar que el click cierre inmediatamente
    e.stopPropagation();
    const isExpanded = pill.getAttribute('aria-expanded') === 'true';
    pill.setAttribute('aria-expanded', !isExpanded);
  });
  
  // Cerrar al hacer click fuera
  document.addEventListener('click', (e) => {
    if (!pill.contains(e.target)) {
      pill.setAttribute('aria-expanded', 'false');
    }
  });
  
  // Cerrar con Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      pill.setAttribute('aria-expanded', 'false');
      pill.blur();
    }
  });
}

  // ========== DISPOSITIVOS IoT ==========
  async loadDevices() {
    const listEl = document.getElementById('devicesList');
    const countEl = document.getElementById('devicesTotalCount');
    if (!listEl) return;

    try {
      const data = await utils.fetchJSON('/api/devices') || {};
      const { devices = [], total = 0 } = data;

      if (countEl) countEl.textContent = total.toString();

      if (devices.length === 0) {
        listEl.innerHTML = `
          <li class="devices-list__item">
            <span class="devices-list__name text-muted">No hay dispositivos configurados</span>
          </li>
        `;
        return;
      }

      listEl.innerHTML = devices.map(device => `
        <li class="devices-list__item">
          <div class="devices-list__info">
            <span class="devices-list__icon">${device.icon}</span>
            <span class="devices-list__name">${device.name}</span>
          </div>
          <span class="devices-list__state devices-list__state--${device.status}">
            ${device.state}
          </span>
        </li>
      `).join('');

    } catch (error) {
      console.error('Error cargando dispositivos:', error);
      listEl.innerHTML = `
        <li class="devices-list__item devices-list__item--error">
          <span class="devices-list__name text-muted">Error al cargar</span>
        </li>
      `;
    }
  }

  // ========== MEALIE ==========
  async loadMealieStats() {
    const mealieStats = document.getElementById('mealieStats');
    if (!mealieStats) return;

    try {
      const data = await utils.fetchJSON('/api/mealie') || {};
      const { total_recipes = 0, meals_today = {} } = data;

      const recipesEl = document.getElementById('mealieRecipesCount');
      const mealsCountEl = document.getElementById('mealieMealsTodayCount');
      const mealsListEl = document.getElementById('mealieMealsList');

      if (recipesEl) recipesEl.textContent = total_recipes.toString();

      const flatMeals = Object.entries(meals_today).flatMap(([type, titles]) =>
        titles.map(title => ({ type, title }))
      );
      
      if (mealsCountEl) mealsCountEl.textContent = flatMeals.length.toString();

      if (mealsListEl) {
        if (flatMeals.length === 0) {
          mealsListEl.innerHTML = `
            <div class="text-muted" style="font-size: var(--font-size-sm);">
              No hay comidas planificadas para hoy.
            </div>
          `;
        } else {
          mealsListEl.innerHTML = flatMeals.map(meal => `
            <div class="mealie-meal-item">
              <span class="mealie-meal-type">${meal.type}</span>
              <span class="mealie-meal-title">${meal.title}</span>
            </div>
          `).join('');
        }
      }

      console.log('✅ Mealie stats:', data);
    } catch (error) {
      utils.handleError(error, 'Mealie API');
    }
  }



  
  // ========== PI-HOLE ==========
  async loadPiHoleStats() {
    const piholeStats = document.getElementById('piholeStats');
    if (!piholeStats) return;

    try {
      const data = await utils.fetchJSON('/api/pihole');
      
      if (!data || data.error) {
        throw new Error(data?.error || 'Datos no disponibles');
      }
      
      // Renderizar con datos reales de Pi-hole v6
      piholeStats.innerHTML = `
        <div class="metric">
          <span class="metric__value">${data.ads_blocked_today.toLocaleString()}</span>
          <span class="metric__label">Bloqueados hoy</span>
          <span class="metric__change metric__change--positive">
            <svg class="icon icon--sm" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            ${data.ads_percentage_today}%
          </span>
        </div>
        <div class="metric">
          <span class="metric__value">${data.dns_queries_today.toLocaleString()}</span>
          <span class="metric__label">Queries DNS</span>
        </div>
      `;
      
      console.log('✅ Pi-hole datos reales:', data);
      
    } catch (error) {
      utils.handleError(error, 'Pi-hole API', piholeStats);
      
      // Fallback con placeholder
      piholeStats.innerHTML = `
        <div class="metric">
          <span class="metric__value">--</span>
          <span class="metric__label">Error conexión</span>
        </div>
        <div class="metric">
          <span class="metric__value">--</span>
          <span class="metric__label">Ver consola</span>
        </div>
      `;
    }
  }

  async loadSettleUpData() {
    try {
      const data = await utils.fetchJSON('/api/settleup') || {};

      const statusEl = document.getElementById('finMainStatus');
      const gastosEl = document.getElementById('finGastosMes');

      if (statusEl && data.status) {
        statusEl.textContent = data.status;
      }
      if (gastosEl) {
        gastosEl.textContent = `€ ${data.monthly_expenses?.toFixed(2) || '0.00'}`;
      }
    } catch (error) {
      utils.handleError(error, 'Settle Up API');
      const statusEl = document.getElementById('finMainStatus');
      if (statusEl) statusEl.textContent = 'Error al cargar';
    }
  }


  
  // ========== EVENT LISTENERS ==========
  setupEventListeners() {
    // Botón de añadir producto (LISTA COMPRA)
    const addShoppingBtn = document.getElementById('addShoppingBtn');
    if (addShoppingBtn) {
      addShoppingBtn.addEventListener('click', () => {
        this.addShoppingItem();
      });
    }
    
    // Refresh de datos optimizado con debounce fuerte
    this.addInterval(utils.debounce(() => {
      console.log('🔄 Actualizando datos del dashboard...');
      this.loadWeatherData();
      this.loadMealieStats();
      this.loadPiHoleStats();
      this.loadEnergyData();
    }, 2000), 10 * 60 * 1000); // 10 minutos en lugar de 5
    
    // Refresh estado red cada 2 minutos en lugar de 1
    this.addInterval(() => {
      this.loadDashboardStatus();  
    }, 2 * 60 * 1000);
  }
  

  // ========== ENERGY DATA ==========
  async loadEnergyData() {
    try {
      const data = await utils.fetchJSON('/api/energy', { timeout: 30000 }) || {};
      
      const consumptionEl = document.getElementById('energyConsumption');
      const costEl = document.getElementById('energyCost');
      const powerEl = document.getElementById('energyPower');

      if (data.consumption && consumptionEl) {
        consumptionEl.textContent = data.consumption.consumption_kwh || '--';
      }
      
      if (data.cost && costEl) {
        costEl.textContent = data.cost.cost_eur || '--';
      }
      
      if (data.current_power && powerEl) {
        powerEl.textContent = data.current_power.power_w || '--';
      }

      console.log('✅ Energy data loaded:', data);
    } catch (error) {
      console.error('❌ Energy API error:', error);
      utils.handleError(error, 'Energy API');
      
      // Evitar dejar estado de error fijo ante fallos transitorios
      const consumptionEl = document.getElementById('energyConsumption');
      const costEl = document.getElementById('energyCost');
      const powerEl = document.getElementById('energyPower');
      
      if (consumptionEl) consumptionEl.textContent = '--';
      if (costEl) costEl.textContent = '--';
      if (powerEl) powerEl.textContent = '--';
    }
  }

  //  LISTA DE LA COMPRA 
  async loadShoppingList() {
    const shoppingList = document.getElementById('shoppingList');
    if (!shoppingList) return;
    
    try {
      const items = await utils.fetchJSON('/api/shopping') || [];
      
      if (items.length === 0) {
        shoppingList.innerHTML = '<div style="text-align: center; color: var(--color-text-muted); padding: var(--space-md);">Lista vacía 😊<br><small>Añade tu primer producto</small></div>';
      } else {
        shoppingList.innerHTML = items.map((item, index) => `
          <li class="shopping-item">
            <span>${item.text}</span>
            <button class="btn btn--icon btn--ghost btn--sm" onclick="dashboardInstance.deleteShoppingItem(${index})" title="Eliminar">
              <svg class="icon icon--sm" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </li>
        `).join('');
      }
    } catch (error) {
      utils.handleError(error, 'Shopping List API', shoppingList);
    }
  }

  addShoppingItem() {
    const text = prompt('Producto para la compra:');
    if (!text?.trim()) return;
    
    utils.fetchJSON('/api/shopping', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: text.trim()})
    }).then(() => {
      this.loadShoppingList();
      utils.showToast('✅ Producto añadido', 'success');
    }).catch(error => {
      utils.handleError(error, 'Add Shopping Item');
    });
  }

  deleteShoppingItem(index) {
    utils.fetchJSON('/api/shopping', {
      method: 'DELETE',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({index})
    }).then(() => {
      this.loadShoppingList();
      utils.showToast('✅ Producto eliminado', 'success');
    }).catch(error => {
      utils.handleError(error, 'Delete Shopping Item');
    });
  }

  // ========== INTERVAL MANAGEMENT ==========
  addInterval(callback, delay) {
    const id = setInterval(callback, delay);
    this.intervals.add(id);
    return id;
  }

  // Cleanup mejorado
  destroy() {
    this.intervals.forEach(id => clearInterval(id));
    this.intervals.clear();
  }
}

// Inicializar dashboard cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
  // Solo inicializar si estamos en la página del dashboard
  if (document.getElementById('currentTime')) {
    window.dashboardInstance = new Dashboard();
    
    // Cleanup en navegación (SPA)
    window.addEventListener('beforeunload', () => {
      if (window.dashboardInstance) {
        window.dashboardInstance.destroy();
      }
    });
  }
});
