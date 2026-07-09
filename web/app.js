(() => {
  'use strict';

  const AUTH_KEY = 'tg.auth';
  const OLD_PLAYER_KEY = 'tradingGamePlayer';
  const MARKET_POLL_MS = 18000;
  const PORTFOLIO_POLL_MS = 15000;

  const state = {
    auth: null,
    player: null,
    assets: [],
    assetBySymbol: new Map(),
    portfolio: null,
    activeTab: 'market',
    marketFilter: 'all',
    addAssetClass: 'stock',
    addAssetSearchResults: [],
    tradeSide: 'buy',
    chart: null,
    chartSymbol: null,
    chartRange: '1mo',
    timers: []
  };

  const el = {};

  document.addEventListener('DOMContentLoaded', init);

  async function init() {
    cacheElements();
    bindEvents();
    await restoreSession();
  }

  function cacheElements() {
    Object.assign(el, {
      toastRegion: document.getElementById('toast-region'),
      startScreen: document.getElementById('start-screen'),
      appShell: document.getElementById('app-shell'),
      authTabs: Array.from(document.querySelectorAll('.auth-tab')),
      authForms: Array.from(document.querySelectorAll('.auth-form')),
      signinForm: document.getElementById('signin-form'),
      registerForm: document.getElementById('register-form'),
      recoverForm: document.getElementById('recover-form'),
      authStatus: document.getElementById('auth-status'),
      playerName: document.getElementById('player-name'),
      summaryCash: document.getElementById('summary-cash'),
      summaryNetWorth: document.getElementById('summary-net-worth'),
      summaryPl: document.getElementById('summary-pl'),
      switchPlayer: document.getElementById('switch-player'),
      tabButtons: Array.from(document.querySelectorAll('.tab-button')),
      tabPanels: Array.from(document.querySelectorAll('.tab-panel')),
      assetFilters: document.getElementById('asset-filters'),
      addAssetOpen: document.getElementById('add-asset-open'),
      addAssetModal: document.getElementById('add-asset-modal'),
      addAssetClasses: document.getElementById('add-asset-classes'),
      addAssetForm: document.getElementById('add-asset-form'),
      addAssetQueryLabel: document.getElementById('add-asset-query-label'),
      addAssetQuery: document.getElementById('add-asset-query'),
      addAssetSearch: document.getElementById('add-asset-search'),
      addAssetHelp: document.getElementById('add-asset-help'),
      addAssetResults: document.getElementById('add-asset-results'),
      addAssetSubmit: document.getElementById('add-asset-submit'),
      addAssetMessage: document.getElementById('add-asset-message'),
      marketStatus: document.getElementById('market-status'),
      marketBody: document.getElementById('market-body'),
      portfolioSummary: document.getElementById('portfolio-summary'),
      portfolioEmpty: document.getElementById('portfolio-empty'),
      holdingsBody: document.getElementById('holdings-body'),
      historyEmpty: document.getElementById('history-empty'),
      historyBody: document.getElementById('history-body'),
      leaderboardEmpty: document.getElementById('leaderboard-empty'),
      leaderboardBody: document.getElementById('leaderboard-body'),
      tradeModal: document.getElementById('trade-modal'),
      tradeForm: document.getElementById('trade-form'),
      tradeTitle: document.getElementById('trade-title'),
      tradeSymbol: document.getElementById('trade-symbol'),
      tradeQuantity: document.getElementById('trade-quantity'),
      tradeEstimate: document.getElementById('trade-estimate'),
      tradePriceNote: document.getElementById('trade-price-note'),
      tradeSubmit: document.getElementById('trade-submit'),
      tradeMessage: document.getElementById('trade-message'),
      sideToggles: Array.from(document.querySelectorAll('[data-side]')),
      chartModal: document.getElementById('chart-modal'),
      chartTitle: document.getElementById('chart-title'),
      chartStatus: document.getElementById('chart-status'),
      rangeButtons: document.getElementById('range-buttons'),
      chartCanvas: document.getElementById('price-chart')
    });
  }

  function bindEvents() {
    el.authTabs.forEach((button) => button.addEventListener('click', () => setAuthMode(button.dataset.authMode)));
    el.signinForm.addEventListener('submit', handleSignIn);
    el.registerForm.addEventListener('submit', handleRegister);
    el.recoverForm.addEventListener('submit', handleRecover);
    el.switchPlayer.addEventListener('click', logoutPlayer);
    el.tabButtons.forEach((button) => button.addEventListener('click', () => setActiveTab(button.dataset.tab)));
    el.assetFilters.addEventListener('click', handleFilterClick);
    el.addAssetOpen.addEventListener('click', openAddAssetModal);
    el.addAssetClasses.addEventListener('click', handleAddAssetClassClick);
    el.addAssetForm.addEventListener('submit', handleAddAssetSubmit);
    el.addAssetSearch.addEventListener('click', handleAddAssetSearch);
    el.addAssetResults.addEventListener('click', handleAddAssetResultClick);
    el.addAssetQuery.addEventListener('input', handleAddAssetQueryInput);
    el.marketBody.addEventListener('click', handleAssetAction);
    el.holdingsBody.addEventListener('click', handleAssetAction);
    el.leaderboardBody.addEventListener('click', () => {});
    el.tradeSymbol.addEventListener('change', updateTradeEstimate);
    el.tradeQuantity.addEventListener('input', updateTradeEstimate);
    el.tradeForm.addEventListener('submit', handleTradeSubmit);
    el.sideToggles.forEach((button) => button.addEventListener('click', () => setTradeSide(button.dataset.side)));
    el.rangeButtons.addEventListener('click', handleRangeClick);
    document.querySelectorAll('[data-close="trade"]').forEach((button) => button.addEventListener('click', closeTradeModal));
    document.querySelectorAll('[data-close="add-asset"]').forEach((button) => button.addEventListener('click', closeAddAssetModal));
    document.querySelectorAll('[data-close="chart"]').forEach((button) => button.addEventListener('click', closeChartModal));
    [el.tradeModal, el.addAssetModal, el.chartModal].forEach((modal) => {
      modal.addEventListener('click', (event) => {
        if (event.target !== modal) return;
        if (modal === el.tradeModal) closeTradeModal();
        if (modal === el.addAssetModal) closeAddAssetModal();
        if (modal === el.chartModal) closeChartModal();
      });
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeTradeModal();
        closeAddAssetModal();
        closeChartModal();
      }
    });
  }

  async function restoreSession() {
    const saved = loadSavedAuth();
    if (!saved) {
      clearAuth();
      showStart();
      return;
    }

    state.auth = saved;
    try {
      const me = await apiRequest('/api/me');
      saveAuth({ ...saved, id: me.id, username: me.username });
      showApp();
    } catch (error) {
      if (error.status === 401) {
        clearAuth();
      } else {
        state.auth = null;
        state.player = null;
        state.portfolio = null;
      }
      showStart();
      if (error.status && error.status !== 401) showToast(`Sign-in check failed: ${error.message}`, 'bad');
    }
  }

  function loadSavedAuth() {
    try {
      const raw = localStorage.getItem(AUTH_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed || !parsed.token || !parsed.id || !parsed.username) return null;
      return { token: parsed.token, id: parsed.id, username: parsed.username };
    } catch {
      localStorage.removeItem(AUTH_KEY);
      return null;
    }
  }

  function saveAuth(auth) {
    const clean = { token: auth.token, id: auth.id, username: auth.username };
    localStorage.setItem(AUTH_KEY, JSON.stringify(clean));
    localStorage.removeItem(OLD_PLAYER_KEY);
    state.auth = clean;
    state.player = { id: clean.id, username: clean.username };
  }

  function clearAuth() {
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(OLD_PLAYER_KEY);
    state.auth = null;
    state.player = null;
    state.portfolio = null;
  }

  async function handleSignIn(event) {
    event.preventDefault();
    await submitAuthForm(el.signinForm, '/api/login', ['username', 'password'], 'Signing in...');
  }

  async function handleRegister(event) {
    event.preventDefault();
    await submitAuthForm(el.registerForm, '/api/register', ['username', 'password', 'recovery_word'], 'Creating account...');
  }

  async function handleRecover(event) {
    event.preventDefault();
    await submitAuthForm(el.recoverForm, '/api/recover', ['username', 'recovery_word', 'new_password'], 'Resetting password...');
  }

  async function submitAuthForm(form, endpoint, fields, pendingMessage) {
    const body = {};
    const formData = new FormData(form);
    for (const field of fields) {
      body[field] = String(formData.get(field) || '').trim();
      if (!body[field]) {
        setStatus(el.authStatus, 'Please fill in every field.', 'bad');
        return;
      }
    }
    const password = body.password || body.new_password;
    if (password.length < 4) {
      setStatus(el.authStatus, 'Password must be at least 4 characters.', 'bad');
      return;
    }

    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    setStatus(el.authStatus, pendingMessage, '');
    try {
      const auth = await apiRequest(endpoint, {
        method: 'POST',
        body: JSON.stringify(body)
      });
      saveAuth(auth);
      setStatus(el.authStatus, '', '');
      form.reset();
      showApp();
    } catch (error) {
      setStatus(el.authStatus, error.message, 'bad');
      showToast(error.message, 'bad');
    } finally {
      button.disabled = false;
    }
  }

  function showStart() {
    clearTimers();
    el.startScreen.classList.remove('hidden');
    el.appShell.classList.add('hidden');
    setAuthMode('signin');
  }

  function showApp() {
    el.startScreen.classList.add('hidden');
    el.appShell.classList.remove('hidden');
    el.playerName.textContent = state.player.username;
    setActiveTab(state.activeTab || 'market');
    refreshAll();
    clearTimers();
    state.timers.push(window.setInterval(loadAssets, MARKET_POLL_MS));
    state.timers.push(window.setInterval(loadPortfolio, PORTFOLIO_POLL_MS));
  }

  async function logoutPlayer() {
    try {
      await apiRequest('/api/logout', { method: 'POST' });
    } catch {
      // Local logout should still succeed if the server is unreachable.
    } finally {
      clearAuth();
      state.activeTab = 'market';
      closeTradeModal();
      closeAddAssetModal();
      closeChartModal();
      showStart();
    }
  }

  function handleSessionExpired() {
    clearAuth();
    state.activeTab = 'market';
    closeTradeModal();
    closeAddAssetModal();
    closeChartModal();
    showStart();
    showToast('Session expired, please sign in again.', 'bad');
  }

  function setAuthMode(mode) {
    const nextMode = ['signin', 'register', 'recover'].includes(mode) ? mode : 'signin';
    el.authTabs.forEach((button) => button.classList.toggle('active', button.dataset.authMode === nextMode));
    el.authForms.forEach((form) => form.classList.toggle('hidden', form.dataset.authForm !== nextMode));
    setStatus(el.authStatus, '', '');
    const firstInput = document.querySelector(`[data-auth-form="${nextMode}"] input`);
    if (firstInput) firstInput.focus();
  }

  function clearTimers() {
    state.timers.forEach((timer) => window.clearInterval(timer));
    state.timers = [];
  }

  async function refreshAll() {
    await Promise.allSettled([loadAssets(), loadPortfolio(), loadLeaderboard()]);
    if (state.activeTab === 'history') loadTransactions();
  }

  async function loadAssets() {
    setStatus(el.marketStatus, state.assets.length ? 'Updating prices...' : 'Loading market...', '');
    try {
      const data = await apiRequest('/api/assets');
      state.assets = Array.isArray(data.assets) ? data.assets : [];
      state.assetBySymbol = new Map(state.assets.map((asset) => [asset.symbol, asset]));
      populateTradeSymbols();
      renderMarket();
      setStatus(el.marketStatus, `Updated ${formatTime(data.as_of)} · ${state.assets.length} assets`, 'good');
      updateTradeEstimate();
    } catch (error) {
      setStatus(el.marketStatus, state.assets.length ? 'Market update failed. Showing last prices.' : 'Market unavailable.', 'bad');
      showToast(`Market: ${error.message}`, 'bad');
    }
  }

  async function loadPortfolio() {
    if (!state.player) return;
    try {
      const data = await apiRequest(`/api/players/${encodeURIComponent(state.player.id)}/portfolio`);
      state.portfolio = data;
      renderSummary(data);
      renderPortfolio(data);
    } catch (error) {
      if (error.status === 401) return;
      if (error.status === 404) {
        showToast('Player not found. Please sign in again.', 'bad');
        clearAuth();
        showStart();
        return;
      }
      showToast(`Portfolio: ${error.message}`, 'bad');
      renderPortfolioError(error.message);
    }
  }

  async function loadTransactions() {
    if (!state.player) return;
    el.historyBody.innerHTML = rowLoading(6, 'Loading trades...');
    el.historyEmpty.classList.add('hidden');
    try {
      const data = await apiRequest(`/api/players/${encodeURIComponent(state.player.id)}/transactions?limit=100`);
      renderTransactions(data.transactions || []);
    } catch (error) {
      if (error.status === 401) return;
      el.historyBody.innerHTML = rowMessage(6, `History unavailable: ${escapeHtml(error.message)}`);
      showToast(`History: ${error.message}`, 'bad');
    }
  }

  async function loadLeaderboard() {
    el.leaderboardEmpty.classList.add('hidden');
    try {
      const data = await apiRequest('/api/leaderboard');
      renderLeaderboard(data.leaderboard || []);
    } catch (error) {
      el.leaderboardBody.innerHTML = rowMessage(4, `Leaderboard unavailable: ${escapeHtml(error.message)}`);
      showToast(`Leaderboard: ${error.message}`, 'bad');
    }
  }

  function setActiveTab(tabName) {
    state.activeTab = tabName;
    el.tabButtons.forEach((button) => button.classList.toggle('active', button.dataset.tab === tabName));
    el.tabPanels.forEach((panel) => panel.classList.toggle('active', panel.id === tabName));
    if (tabName === 'history') loadTransactions();
    if (tabName === 'leaderboard') loadLeaderboard();
    if (tabName === 'portfolio' && state.portfolio) renderPortfolio(state.portfolio);
  }

  function handleFilterClick(event) {
    const button = event.target.closest('[data-filter]');
    if (!button) return;
    setMarketFilter(button.dataset.filter);
    renderMarket();
  }

  function setMarketFilter(filter) {
    state.marketFilter = ['all', 'stock', 'crypto', 'fiat'].includes(filter) ? filter : 'all';
    el.assetFilters.querySelectorAll('.pill').forEach((pill) => {
      pill.classList.toggle('active', pill.dataset.filter === state.marketFilter);
    });
  }

  function openAddAssetModal() {
    resetAddAssetModal();
    el.addAssetModal.classList.remove('hidden');
    el.addAssetQuery.focus();
  }

  function closeAddAssetModal() {
    el.addAssetModal.classList.add('hidden');
  }

  function resetAddAssetModal() {
    state.addAssetSearchResults = [];
    el.addAssetForm.reset();
    setAddAssetClass(state.addAssetClass || 'stock');
    setStatus(el.addAssetMessage, '', '');
    renderAddAssetResults([]);
  }

  function handleAddAssetClassClick(event) {
    const button = event.target.closest('[data-add-class]');
    if (!button) return;
    setAddAssetClass(button.dataset.addClass);
  }

  function setAddAssetClass(assetClass) {
    const nextClass = ['stock', 'crypto', 'fiat'].includes(assetClass) ? assetClass : 'stock';
    state.addAssetClass = nextClass;
    state.addAssetSearchResults = [];
    el.addAssetClasses.querySelectorAll('[data-add-class]').forEach((button) => {
      button.classList.toggle('active', button.dataset.addClass === nextClass);
    });
    const copy = {
      stock: {
        label: 'Ticker (e.g. BABA)',
        placeholder: 'BABA',
        help: 'Enter a ticker and add it directly.',
        submit: 'Add stock',
        showSearch: false
      },
      crypto: {
        label: 'Search CoinGecko (e.g. pepe)',
        placeholder: 'pepe',
        help: 'Search, then pick a coin from the results.',
        submit: 'Add selected coin',
        showSearch: true
      },
      fiat: {
        label: 'Currency code (e.g. SEK)',
        placeholder: 'SEK',
        help: 'Enter a currency code directly, or search supported currencies.',
        submit: 'Add currency',
        showSearch: true
      }
    }[nextClass];
    el.addAssetQueryLabel.textContent = copy.label;
    el.addAssetQuery.placeholder = copy.placeholder;
    el.addAssetHelp.textContent = copy.help;
    el.addAssetSubmit.textContent = copy.submit;
    el.addAssetSubmit.classList.toggle('hidden', nextClass === 'crypto');
    el.addAssetSearch.classList.toggle('hidden', !copy.showSearch);
    renderAddAssetResults([]);
    setStatus(el.addAssetMessage, '', '');
  }

  function handleAddAssetQueryInput() {
    state.addAssetSearchResults = [];
    renderAddAssetResults([]);
    setStatus(el.addAssetMessage, '', '');
  }

  async function handleAddAssetSearch() {
    const assetClass = state.addAssetClass;
    const query = el.addAssetQuery.value.trim();
    if (!query) {
      setStatus(el.addAssetMessage, assetClass === 'fiat' ? 'Enter a currency name or code.' : 'Enter a search term.', 'bad');
      return;
    }

    setAddAssetBusy(true, true);
    setStatus(el.addAssetMessage, 'Searching...', '');
    renderAddAssetResults([], 'Loading results...');
    try {
      const url = `/api/assets/search?class=${encodeURIComponent(assetClass)}&q=${encodeURIComponent(query)}`;
      const data = await apiRequest(url);
      const results = Array.isArray(data.results) ? data.results : [];
      state.addAssetSearchResults = results;
      setStatus(el.addAssetMessage, results.length ? `Found ${results.length} result${results.length === 1 ? '' : 's'}.` : 'No matches found.', results.length ? 'good' : '');
      renderAddAssetResults(results);
    } catch (error) {
      state.addAssetSearchResults = [];
      renderAddAssetResults([]);
      setStatus(el.addAssetMessage, error.message, 'bad');
    } finally {
      setAddAssetBusy(false, true);
    }
  }

  async function handleAddAssetSubmit(event) {
    event.preventDefault();
    const assetClass = state.addAssetClass;
    if (assetClass === 'crypto') {
      setStatus(el.addAssetMessage, 'Search CoinGecko and pick a coin to add.', 'bad');
      return;
    }
    const symbol = normalizeAssetSymbol(el.addAssetQuery.value);
    if (!symbol) {
      setStatus(el.addAssetMessage, assetClass === 'fiat' ? 'Enter a currency code.' : 'Enter a ticker.', 'bad');
      return;
    }
    const payload = assetClass === 'fiat'
      ? { asset_class: 'fiat', symbol, provider_id: symbol }
      : { asset_class: 'stock', symbol };
    await addCustomAsset(payload);
  }

  async function handleAddAssetResultClick(event) {
    const button = event.target.closest('[data-result-index]');
    if (!button) return;
    const result = state.addAssetSearchResults[Number(button.dataset.resultIndex)];
    if (!result) return;
    const assetClass = state.addAssetClass;
    const symbol = normalizeAssetSymbol(result.symbol);
    if (!symbol) {
      setStatus(el.addAssetMessage, 'That result does not include a symbol.', 'bad');
      return;
    }
    const payload = {
      asset_class: assetClass,
      symbol,
      provider_id: result.provider_id || symbol,
      name: result.name || symbol
    };
    await addCustomAsset(payload);
  }

  async function addCustomAsset(payload) {
    setAddAssetBusy(true);
    setStatus(el.addAssetMessage, `Adding ${payload.symbol}...`, '');
    try {
      const result = await apiRequest('/api/assets', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      const asset = result.asset || payload;
      showToast(`Added ${asset.symbol || payload.symbol}`, 'good');
      closeAddAssetModal();
      setMarketFilter(asset.asset_class || payload.asset_class);
      await loadAssets();
    } catch (error) {
      if (error.status === 401) return;
      setStatus(el.addAssetMessage, error.message, 'bad');
    } finally {
      setAddAssetBusy(false);
    }
  }

  function setAddAssetBusy(isBusy, searchOnly = false) {
    el.addAssetSearch.disabled = isBusy;
    if (!searchOnly) {
      el.addAssetSubmit.disabled = isBusy;
      el.addAssetQuery.disabled = isBusy;
      el.addAssetClasses.querySelectorAll('button').forEach((button) => {
        button.disabled = isBusy;
      });
      el.addAssetResults.querySelectorAll('button').forEach((button) => {
        button.disabled = isBusy;
      });
    }
  }

  function renderAddAssetResults(results, message = '') {
    if (message) {
      el.addAssetResults.classList.remove('hidden');
      el.addAssetResults.innerHTML = `<div class="search-result-empty">${escapeHtml(message)}</div>`;
      return;
    }
    if (!results.length) {
      el.addAssetResults.classList.add('hidden');
      el.addAssetResults.innerHTML = '';
      return;
    }
    el.addAssetResults.classList.remove('hidden');
    el.addAssetResults.innerHTML = results.map((result, index) => {
      const symbol = normalizeAssetSymbol(result.symbol);
      const name = result.name || '';
      return `<button class="search-result" type="button" data-result-index="${index}" role="option">
        <span class="symbol-cell">${escapeHtml(symbol)}</span>
        <span>${escapeHtml(name)}</span>
      </button>`;
    }).join('');
  }

  function normalizeAssetSymbol(value) {
    return String(value || '').trim().toUpperCase();
  }

  function renderMarket() {
    const filtered = state.assets.filter((asset) => state.marketFilter === 'all' || asset.asset_class === state.marketFilter);
    if (!filtered.length) {
      el.marketBody.innerHTML = rowMessage(4, 'No assets match this filter.');
      return;
    }
    el.marketBody.innerHTML = filtered.map((asset) => {
      const tone = numberValue(asset.change_pct) >= 0 ? 'good' : 'bad';
      return `<tr>
        <td>${assetLabel(asset)}</td>
        <td class="num">${formatPrice(asset.price)}</td>
        <td class="num ${tone}">${formatPercent(asset.change_pct, true)}</td>
        <td class="action-buttons">
          <button type="button" data-action="trade" data-symbol="${escapeAttr(asset.symbol)}" data-side="buy">Trade</button>
          <button type="button" data-action="chart" data-symbol="${escapeAttr(asset.symbol)}">Chart</button>
        </td>
      </tr>`;
    }).join('');
  }

  function renderSummary(portfolio) {
    el.summaryCash.textContent = formatMoney(portfolio.cash);
    el.summaryNetWorth.textContent = formatMoney(portfolio.net_worth);
    const tone = numberValue(portfolio.total_pl) >= 0 ? 'good' : 'bad';
    el.summaryPl.className = tone;
    el.summaryPl.textContent = `${formatMoney(portfolio.total_pl)} (${formatPercent(portfolio.total_pl_pct, true)})`;
  }

  function renderPortfolio(portfolio) {
    el.portfolioSummary.innerHTML = `
      <div class="summary-card"><span>Cash</span><strong>${formatMoney(portfolio.cash)}</strong></div>
      <div class="summary-card"><span>Holdings</span><strong>${formatMoney(portfolio.holdings_value)}</strong></div>
      <div class="summary-card"><span>Net worth</span><strong>${formatMoney(portfolio.net_worth)}</strong></div>
      <div class="summary-card"><span>Total P/L</span><strong class="${numberValue(portfolio.total_pl_pct) >= 0 ? 'good' : 'bad'}">${formatPercent(portfolio.total_pl_pct, true)}</strong></div>`;

    const holdings = Array.isArray(portfolio.holdings) ? portfolio.holdings : [];
    el.portfolioEmpty.classList.toggle('hidden', holdings.length > 0);
    if (!holdings.length) {
      el.holdingsBody.innerHTML = '';
      return;
    }

    el.holdingsBody.innerHTML = holdings.map((holding) => {
      const tone = numberValue(holding.pl) >= 0 ? 'good' : 'bad';
      return `<tr>
        <td>${assetLabel(holding)}</td>
        <td class="num">${formatQuantity(holding.quantity)}</td>
        <td class="num">${formatPrice(holding.avg_cost)}</td>
        <td class="num">${formatPrice(holding.price)}</td>
        <td class="num">${formatMoney(holding.value)}</td>
        <td class="num ${tone}">${formatMoney(holding.pl)}<br><small>${formatPercent(holding.pl_pct, true)}</small></td>
        <td class="action-buttons">
          <button type="button" data-action="trade" data-symbol="${escapeAttr(holding.symbol)}" data-side="sell">Sell</button>
          <button type="button" data-action="chart" data-symbol="${escapeAttr(holding.symbol)}">Chart</button>
        </td>
      </tr>`;
    }).join('');
  }

  function renderPortfolioError(message) {
    if (!state.portfolio) {
      el.portfolioSummary.innerHTML = `<div class="empty-state">Portfolio unavailable: ${escapeHtml(message)}</div>`;
      el.holdingsBody.innerHTML = '';
    }
  }

  function renderTransactions(transactions) {
    el.historyEmpty.classList.toggle('hidden', transactions.length > 0);
    if (!transactions.length) {
      el.historyBody.innerHTML = '';
      return;
    }
    el.historyBody.innerHTML = transactions.map((tx) => {
      const side = String(tx.side || '').toLowerCase();
      const tone = side === 'buy' ? 'buy' : 'sell';
      return `<tr>
        <td>${formatDateTime(tx.ts)}</td>
        <td><span class="side-badge ${tone}">${escapeHtml(side || '?')}</span></td>
        <td class="symbol-cell">${escapeHtml(tx.symbol)}</td>
        <td class="num">${formatQuantity(tx.quantity)}</td>
        <td class="num">${formatPrice(tx.price)}</td>
        <td class="num">${formatMoney(tx.total)}</td>
      </tr>`;
    }).join('');
  }

  function renderLeaderboard(rows) {
    el.leaderboardEmpty.classList.toggle('hidden', rows.length > 0);
    if (!rows.length) {
      el.leaderboardBody.innerHTML = '';
      return;
    }
    el.leaderboardBody.innerHTML = rows.map((row) => {
      const current = state.player && Number(row.player_id) === Number(state.player.id);
      const tone = numberValue(row.total_pl_pct) >= 0 ? 'good' : 'bad';
      return `<tr class="${current ? 'current-player' : ''}">
        <td class="rank-cell">#${escapeHtml(row.rank)}</td>
        <td>${escapeHtml(row.username)}${current ? ' <span class="you-badge">you</span>' : ''}</td>
        <td class="num">${formatMoney(row.net_worth)}</td>
        <td class="num ${tone}">${formatPercent(row.total_pl_pct, true)}</td>
      </tr>`;
    }).join('');
  }

  function populateTradeSymbols() {
    const selected = el.tradeSymbol.value;
    el.tradeSymbol.innerHTML = state.assets.map((asset) => `<option value="${escapeAttr(asset.symbol)}">${escapeHtml(asset.symbol)} · ${escapeHtml(asset.name)}</option>`).join('');
    if (selected && state.assetBySymbol.has(selected)) el.tradeSymbol.value = selected;
  }

  function handleAssetAction(event) {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    const symbol = button.dataset.symbol;
    if (button.dataset.action === 'trade') {
      openTradeModal(symbol, button.dataset.side || 'buy');
    } else if (button.dataset.action === 'chart') {
      openChartModal(symbol);
    }
  }

  function openTradeModal(symbol, side = 'buy') {
    if (!state.assets.length) {
      showToast('Market prices are not loaded yet.', 'bad');
      return;
    }
    populateTradeSymbols();
    el.tradeSymbol.value = symbol || state.assets[0].symbol;
    setTradeSide(side);
    el.tradeQuantity.value = '';
    el.tradeMessage.textContent = '';
    el.tradeMessage.className = 'form-status';
    el.tradeModal.classList.remove('hidden');
    updateTradeEstimate();
    el.tradeQuantity.focus();
  }

  function closeTradeModal() {
    el.tradeModal.classList.add('hidden');
  }

  function setTradeSide(side) {
    state.tradeSide = side === 'sell' ? 'sell' : 'buy';
    el.sideToggles.forEach((button) => button.classList.toggle('active', button.dataset.side === state.tradeSide));
    el.tradeSubmit.textContent = state.tradeSide === 'buy' ? 'Submit buy order' : 'Submit sell order';
  }

  function updateTradeEstimate() {
    const asset = state.assetBySymbol.get(el.tradeSymbol.value);
    const quantity = Number.parseFloat(el.tradeQuantity.value);
    const total = asset && quantity > 0 ? asset.price * quantity : 0;
    el.tradeTitle.textContent = asset ? `${state.tradeSide === 'buy' ? 'Buy' : 'Sell'} ${asset.symbol}` : 'Trade';
    el.tradeEstimate.textContent = formatMoney(total);
    el.tradePriceNote.textContent = asset ? `${formatPrice(asset.price)} per ${asset.symbol}` : 'Waiting for market price';
  }

  async function handleTradeSubmit(event) {
    event.preventDefault();
    const quantity = Number.parseFloat(el.tradeQuantity.value);
    const symbol = el.tradeSymbol.value;
    if (!symbol) {
      setStatus(el.tradeMessage, 'Choose an asset first.', 'bad');
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setStatus(el.tradeMessage, 'Quantity must be greater than zero.', 'bad');
      return;
    }

    el.tradeSubmit.disabled = true;
    setStatus(el.tradeMessage, 'Sending order...', '');
    try {
      const result = await apiRequest('/api/trade', {
        method: 'POST',
        body: JSON.stringify({
          symbol,
          side: state.tradeSide,
          quantity
        })
      });
      setStatus(el.tradeMessage, result.message || 'Trade complete.', 'good');
      showToast(result.message || 'Trade complete.', 'good');
      await Promise.allSettled([loadPortfolio(), loadAssets(), loadTransactions(), loadLeaderboard()]);
    } catch (error) {
      if (error.status === 401) return;
      setStatus(el.tradeMessage, error.message, 'bad');
      showToast(error.message, 'bad');
    } finally {
      el.tradeSubmit.disabled = false;
    }
  }

  async function openChartModal(symbol) {
    state.chartSymbol = symbol;
    state.chartRange = '1mo';
    el.chartTitle.textContent = `${symbol} chart`;
    el.chartModal.classList.remove('hidden');
    updateRangeButtons();
    await loadChart();
  }

  function closeChartModal() {
    el.chartModal.classList.add('hidden');
  }

  function handleRangeClick(event) {
    const button = event.target.closest('[data-range]');
    if (!button) return;
    state.chartRange = button.dataset.range;
    updateRangeButtons();
    loadChart();
  }

  function updateRangeButtons() {
    el.rangeButtons.querySelectorAll('.pill').forEach((button) => {
      button.classList.toggle('active', button.dataset.range === state.chartRange);
    });
  }

  async function loadChart() {
    if (!state.chartSymbol) return;
    setStatus(el.chartStatus, 'Loading chart...', '');
    try {
      const url = `/api/assets/${encodeURIComponent(state.chartSymbol)}/history?range=${encodeURIComponent(state.chartRange)}`;
      const data = await apiRequest(url);
      drawChart(data.points || []);
      setStatus(el.chartStatus, `${state.chartSymbol} · ${state.chartRange} · ${data.points ? data.points.length : 0} points`, 'good');
    } catch (error) {
      setStatus(el.chartStatus, `Chart unavailable: ${error.message}`, 'bad');
      showToast(`Chart: ${error.message}`, 'bad');
    }
  }

  function drawChart(points) {
    if (!window.Chart) {
      setStatus(el.chartStatus, 'Chart.js is unavailable.', 'bad');
      return;
    }
    const labels = points.map((point) => new Date(point.t * 1000));
    const values = points.map((point) => Number(point.price));
    const first = values[0] || 0;
    const last = values[values.length - 1] || 0;
    const color = last >= first ? '#27f58a' : '#ff5c7a';
    const ctx = el.chartCanvas.getContext('2d');

    if (state.chart) state.chart.destroy();
    state.chart = new window.Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: `${state.chartSymbol} price`,
          data: values,
          borderColor: color,
          backgroundColor: 'rgba(39, 245, 138, 0.12)',
          borderWidth: 2,
          tension: 0.25,
          pointRadius: values.length > 80 ? 0 : 2,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => items[0] ? formatDateTime(items[0].label || labels[items[0].dataIndex] / 1000) : '',
              label: (item) => `Price: ${formatPrice(item.parsed.y)}`
            }
          }
        },
        scales: {
          x: {
            ticks: {
              color: '#8ea0bd',
              maxTicksLimit: 6,
              callback: function tickLabel(value) {
                const date = this.getLabelForValue(value);
                return formatShortDate(date);
              }
            },
            grid: { color: 'rgba(142, 160, 189, 0.12)' }
          },
          y: {
            ticks: { color: '#8ea0bd', callback: (value) => formatCompactPrice(value) },
            grid: { color: 'rgba(142, 160, 189, 0.12)' }
          }
        }
      }
    });
  }

  async function apiRequest(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    const method = String(options.method || 'GET').toUpperCase();
    if ((options.body || method === 'POST') && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
    if (state.auth && state.auth.token && !headers.Authorization) headers.Authorization = `Bearer ${state.auth.token}`;
    const response = await fetch(path, { ...options, headers });
    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    if (!response.ok) {
      const message = data && (data.message || data.detail) ? (data.message || data.detail) : `Request failed (${response.status})`;
      const error = new Error(message);
      error.status = response.status;
      error.data = data;
      if (response.status === 401 && shouldExpireSession(path)) {
        handleSessionExpired();
      }
      throw error;
    }
    return data || {};
  }

  function shouldExpireSession(path) {
    const publicAuthPaths = ['/api/login', '/api/register', '/api/recover'];
    return Boolean(state.auth && state.auth.token && !publicAuthPaths.includes(path));
  }

  function showToast(message, tone = '') {
    const toast = document.createElement('div');
    toast.className = `toast ${tone}`.trim();
    toast.innerHTML = `<span>${escapeHtml(message)}</span><button type="button" aria-label="Dismiss">×</button>`;
    toast.querySelector('button').addEventListener('click', () => toast.remove());
    el.toastRegion.appendChild(toast);
    window.setTimeout(() => toast.remove(), tone === 'bad' ? 7000 : 4500);
  }

  function setStatus(node, message, tone) {
    node.textContent = message;
    node.className = `${node.className.split(' ')[0]} ${tone || ''}`.trim();
  }

  function assetLabel(asset) {
    const klass = asset.asset_class || '';
    const customBadge = asset.custom === true ? ' <span class="custom-badge">custom</span>' : '';
    return `<div class="asset-label"><span class="symbol-cell">${escapeHtml(asset.symbol)}${customBadge}</span><span>${escapeHtml(asset.name || '')}</span><small>${escapeHtml(klass.toUpperCase())}</small></div>`;
  }

  function rowLoading(colspan, message) {
    return rowMessage(colspan, `<span class="loader"></span>${escapeHtml(message)}`);
  }

  function rowMessage(colspan, message) {
    return `<tr><td colspan="${colspan}" class="table-message">${message}</td></tr>`;
  }

  function numberValue(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  function formatMoney(value) {
    return numberValue(value).toLocaleString(undefined, {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }

  function formatPrice(value) {
    const number = numberValue(value);
    const abs = Math.abs(number);
    if (abs >= 1000) return formatMoney(number);
    if (abs >= 1) {
      return `$${number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
    }
    return `$${number.toLocaleString(undefined, { minimumFractionDigits: 0, maximumSignificantDigits: 6 })}`;
  }

  function formatCompactPrice(value) {
    const number = numberValue(value);
    if (Math.abs(number) >= 1000) return `$${Math.round(number).toLocaleString()}`;
    return formatPrice(number);
  }

  function formatQuantity(value) {
    return numberValue(value).toLocaleString(undefined, { maximumFractionDigits: 8 });
  }

  function formatPercent(value, signed = false) {
    const number = numberValue(value);
    const sign = signed && number > 0 ? '+' : '';
    return `${sign}${number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  }

  function formatTime(ts) {
    if (!ts) return 'now';
    return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function formatDateTime(ts) {
    const date = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
    if (Number.isNaN(date.getTime())) return 'Unknown';
    return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function formatShortDate(value) {
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[char]));
  }

  function escapeAttr(value) {
    return escapeHtml(value);
  }
})();
