/**
 * Kyuraa Settings Page Logic
 * Handles API Configuration, Skill Management, and Stats
 */

(function() {
    // 1. Get Gateway Token (Mandatory)
    let gatewayToken = localStorage.getItem('kyuraa_gateway_token');
    
    // Fallback search in URL if just redirected
    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get('token');
    if (urlToken) {
        gatewayToken = urlToken;
        localStorage.setItem('kyuraa_gateway_token', urlToken);
    }

    if (!gatewayToken) {
        // Redirect back to chat if no token, chat will ask for it
        window.location.href = '/';
        return;
    }

    // 2. DOM Elements
    const backBtn = document.getElementById('back-to-chat');
    const themeOptions = document.querySelectorAll('.theme-option');
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.settings-page-section');
    const toastContainer = document.getElementById('toast-container');

    let usageChart = null;

    // 3. Navigation Logic
    backBtn.addEventListener('click', () => {
        window.location.href = `/?token=${gatewayToken}`;
    });

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = item.getAttribute('href').substring(1);
            
            // Update active nav
            navItems.forEach(ni => ni.classList.remove('active'));
            item.classList.add('active');
            
            // Show target section
            sections.forEach(sec => {
                if (sec.id === targetId) {
                    sec.classList.remove('hidden');
                    if (targetId === 'section-stats') {
                        loadUsageChart();
                        loadModelStats();
                    } else if (targetId === 'section-tools') {
                        loadTools();
                    }
                }
                else sec.classList.add('hidden');
            });
        });
    });

    // 4. Utility: Toast
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 500);
        }, 3000);
    }

    // 4b. Utility: Confirm Modal
    function showConfirm(title, message, onConfirm) {
        const existing = document.getElementById('confirm-modal');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'confirm-modal';
        overlay.className = 'modal-overlay';

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const bgSurface = isDark ? '#252525' : '#ffffff';
        const borderColor = isDark ? '#404040' : '#e5e5e5';

        overlay.innerHTML = `
            <div class="modal-box" style="background:${bgSurface};border:1px solid ${borderColor};">
                <h3 style="margin:0 0 8px;font-size:16px;font-weight:600;color:var(--text-primary);">${escapeHtml(title)}</h3>
                <p style="margin:0 0 20px;font-size:14px;color:var(--text-secondary);">${escapeHtml(message)}</p>
                <div class="modal-actions">
                    <button class="btn-modal-cancel">Batal</button>
                    <button class="btn-modal-confirm">Hapus</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        overlay.querySelector('.btn-modal-cancel').onclick = () => overlay.remove();
        overlay.querySelector('.btn-modal-confirm').onclick = () => {
            overlay.remove();
            onConfirm();
        };
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

        requestAnimationFrame(() => overlay.classList.add('show'));
    }

    // 5. Theme Logic
    function setAppTheme(theme) {
        localStorage.setItem('kyuraa_theme', theme);
        let isDark = false;
        if (theme === 'dark') isDark = true;
        else if (theme === 'auto') isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (isDark) document.documentElement.setAttribute('data-theme', 'dark');
        else document.documentElement.removeAttribute('data-theme');
        
        updateThemeUI(theme);
        if (usageChart) loadUsageChart(); // Update chart colors
    }

    function updateThemeUI(theme) {
        themeOptions.forEach(opt => {
            opt.classList.toggle('active', opt.dataset.value === theme);
        });
    }

    // Initialize Theme UI
    const currentTheme = localStorage.getItem('kyuraa_theme') || 'auto';
    updateThemeUI(currentTheme);
    window.setAppTheme = setAppTheme; // Expose to onclick

    // 6. API Configuration Logic
    async function loadApiSettings() {
        try {
            const res = await fetch('/settings', {
                headers: { 'X-API-Key': gatewayToken }
            });
            const data = await res.json();
            
            // Populate Inputs
            document.getElementById('setting-or-model').value = data.openrouter.model || '';
            document.getElementById('setting-or-api-key').value = data.openrouter.api_key || '';
            document.getElementById('setting-google-model').value = data.google.model || '';
            document.getElementById('setting-google-api-key').value = data.google.api_key || '';
            
            // Indicators
            const active = data.active_provider || 'google';
            document.querySelectorAll('.active-indicator').forEach(el => el.classList.add('hidden'));
            const activeCard = document.getElementById(`provider-${active}`);
            if (activeCard) {
                activeCard.querySelector('.active-indicator').classList.remove('hidden');
            }
        } catch (e) {
            showToast('Gagal memuat konfigurasi API', 'error');
        }
    }

    document.querySelectorAll('.save-provider-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const provider = btn.dataset.provider;
            const model = document.getElementById(`setting-${provider === 'openrouter' ? 'or' : 'google'}-model`).value.trim();
            const apiKey = document.getElementById(`setting-${provider === 'openrouter' ? 'or' : 'google'}-api-key`).value.trim();
            
            if (!model || !apiKey) {
                showToast('Mohon isi model dan API Key', 'error');
                return;
            }
            
            const originalText = btn.textContent;
            btn.textContent = '⏳ Memvalidasi...';
            btn.disabled = true;
            
            try {
                const res = await fetch('/settings/validate-and-save', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-API-Key': gatewayToken 
                    },
                    body: JSON.stringify({ provider, model, api_key: apiKey })
                });
                
                const result = await res.json();
                if (res.ok) {
                    showToast(result.message || `Koneksi ${provider} berhasil!`, 'success');
                    loadApiSettings();
                } else {
                    showToast(result.detail || 'Gagal menyimpan settings', 'error');
                }
            } catch (e) {
                showToast('Kesalahan koneksi ke server', 'error');
            } finally {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        });
    });

    // 7. Skills & Tools Logic
    async function loadSkills() {
        const list = document.getElementById('skills-list');
        const badge = document.getElementById('skills-count-badge');
        try {
            const res = await fetch('/skills', { headers: { 'X-API-Key': gatewayToken } });
            const data = await res.json();
            
            badge.innerHTML = data.active_skill ? `Aktif: <strong>${data.active_skill}</strong>` : 'Mode Normal (Asisten)';
            
            list.innerHTML = data.skills.map(s => `
                <div class="skill-item ${s.is_active ? 'active' : ''}">
                    <div style="font-weight:600; font-size:15px; margin-bottom:4px;">${s.name}</div>
                    <div style="font-size:12px; color:var(--text-secondary); margin-bottom:12px;">${s.description}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:10px; color:var(--text-muted);">v${s.version}</span>
                        ${s.is_active 
                            ? `<button class="btn-secondary" onclick="setSkillActive(null)" style="color:var(--danger-text)">Nonaktif</button>`
                            : `<button class="btn-secondary" onclick="setSkillActive('${s.name}')" style="color:var(--accent)">Aktifkan</button>`
                        }
                    </div>
                </div>
            `).join('');
        } catch (e) {
            badge.textContent = 'Gagal memuat skills';
        }
    }

    async function setSkillActive(name) {
        const url = name ? `/skills/${name}/activate` : '/skills/deactivate';
        try {
            const res = await fetch(url, { method: 'POST', headers: { 'X-API-Key': gatewayToken } });
            const data = await res.json();
            showToast(data.message, res.ok ? 'success' : 'error');
            loadSkills();
        } catch (e) { showToast('Gagal mengubah skill', 'error'); }
    }
    window.setSkillActive = setSkillActive;

    // 7b. Tools Logic
    async function loadTools() {
        const list = document.getElementById('tools-list');
        const badge = document.getElementById('tools-count-badge');
        try {
            const res = await fetch('/tools', { headers: { 'X-API-Key': gatewayToken } });
            const data = await res.json();
            
            badge.innerHTML = `${data.enabled || 0} / ${data.total || 0} tools aktif`;
            
            list.innerHTML = data.tools.map(t => `
                <div class="tool-item ${t.enabled ? 'active' : ''}">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <div style="font-weight:600; font-size:15px; margin-bottom:4px;">${t.name}</div>
                            <div style="font-size:12px; color:var(--text-secondary); margin-bottom:8px;">${t.description || 'Tidak ada deskripsi'}</div>
                            <div style="display:flex; gap:8px; align-items:center;">
                                <span class="tool-badge ${t.source || 'built-in'}">${t.source || 'built-in'}</span>
                                <span style="font-size:10px; color:var(--text-muted);">v${t.version || '1.0'}</span>
                            </div>
                        </div>
                        <button class="btn-secondary" onclick="setToolEnabled('${t.name}')" 
                            style="${t.enabled ? 'color:var(--danger-text);' : 'color:var(--accent);'}">
                            ${t.enabled ? 'Nonaktif' : 'Aktifkan'}
                        </button>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            badge.textContent = 'Gagal memuat tools';
        }
    }

    async function setToolEnabled(name) {
        try {
            const res = await fetch(`/tools/${name}/toggle`, { 
                method: 'POST',
                headers: { 'X-API-Key': gatewayToken } 
            });
            const data = await res.json();
            showToast(data.message, res.ok ? 'success' : 'error');
            loadTools();
        } catch (e) { showToast('Gagal mengubah tool', 'error'); }
    }
    window.setToolEnabled = setToolEnabled;

    // 8. Stats Logic
    async function loadStats() {
        try {
            const res = await fetch('/stats', { headers: { 'X-API-Key': gatewayToken } });
            const data = await res.json();
            document.getElementById('usage-requests').textContent = data.total_requests || 0;
            document.getElementById('usage-input').textContent = data.input_tokens || 0;
            document.getElementById('usage-output').textContent = data.output_tokens || 0;
            document.getElementById('usage-total').textContent = data.total_tokens || 0;
        } catch (e) {}
    }

    async function loadUsageChart() {
        const ctx = document.getElementById('usageChart');
        if (!ctx) return;

        try {
            const res = await fetch('/stats/history?days=7', { headers: { 'X-API-Key': gatewayToken } });
            const data = await res.json();

            // Prepare labels and datasets (force some labels even if data is short)
            const labels = data.map(d => {
                const date = new Date(d.date);
                return date.toLocaleDateString('id-ID', { weekday: 'short' });
            });
            const tokens = data.map(d => d.total_tokens || (d.input_tokens + d.output_tokens));
            const requests = data.map(d => d.requests);

            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const textColor = isDark ? '#a0a0a0' : '#666';
            const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';

            if (usageChart) usageChart.destroy();

            usageChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels.length ? labels : ['-'],
                    datasets: [
                        {
                            label: 'Total Tokens',
                            data: tokens.length ? tokens : [0],
                            borderColor: '#D97757',
                            backgroundColor: 'rgba(217, 119, 87, 0.1)',
                            borderWidth: 3,
                            pointBackgroundColor: '#D97757',
                            pointRadius: 4,
                            fill: true,
                            tension: 0.4,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Requests',
                            data: requests.length ? requests : [0],
                            type: 'bar',
                            backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
                            borderColor: isDark ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.2)',
                            borderWidth: 2,
                            borderRadius: 6,
                            pointBackgroundColor: isDark ? '#ffffff' : '#333333',
                            pointBorderColor: isDark ? '#ffffff' : '#333333',
                            pointRadius: 5,
                            pointHoverRadius: 7,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: isDark ? '#2a2a2a' : '#fff',
                            titleColor: isDark ? '#fff' : '#000',
                            bodyColor: isDark ? '#ccc' : '#444',
                            borderColor: isDark ? '#444' : '#e0e0e0',
                            borderWidth: 1,
                            padding: 10,
                            displayColors: true
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: gridColor, drawBorder: false },
                            ticks: { color: textColor, font: { size: 11 } }
                        },
                        y1: {
                            beginAtZero: true,
                            position: 'right',
                            grid: { display: false },
                            ticks: { color: textColor, font: { size: 11 } }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: textColor, font: { size: 11 } }
                        }
                    }
                }
            });
        } catch (e) { console.error('Failed to load chart:', e); }
    }

    async function loadModelStats() {
        const container = document.getElementById('model-stats-list');
        const badge = document.getElementById('model-stats-count');
        if (!container) return;
        
        try {
            const res = await fetch('/stats/by-model', { headers: { 'X-API-Key': gatewayToken } });
            const data = await res.json();
            
            if (!data || data.length === 0) {
                container.innerHTML = '<div style="color:var(--text-muted); font-size:13px; padding:12px 0;">Belum ada data penggunaan per model.</div>';
                badge.textContent = '0 model';
                return;
            }
            
            badge.textContent = data.length + ' model';
            
            container.innerHTML = data.map(m => `
                <div class="model-stat-item">
                    <div class="model-name">${escapeHtml(m.model)}</div>
                    <div class="model-stat">
                        <div class="label">Requests</div>
                        <div class="value">${m.requests}</div>
                    </div>
                    <div class="model-stat">
                        <div class="label">Input</div>
                        <div class="value">${m.input_tokens}</div>
                    </div>
                    <div class="model-stat">
                        <div class="label">Output</div>
                        <div class="value">${m.output_tokens}</div>
                    </div>
                    <div class="model-stat total">
                        <div class="label">Total</div>
                        <div class="value">${m.total_tokens}</div>
                    </div>
                    <button class="btn-delete-model" onclick="deleteModel('${escapeHtml(m.model)}')">Hapus</button>
                </div>
            `).join('');
        } catch (e) {
            container.innerHTML = '<div style="color:var(--danger-text); font-size:13px;">Gagal memuat statistik model.</div>';
        }
    }
    
    async function deleteModel(modelName) {
        showConfirm(
            'Hapus Data Model',
            `Hapus semua data untuk model "${modelName}"?`,
            async () => {
                try {
                    const res = await fetch('/stats/clear-models', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                            'X-API-Key': gatewayToken
                        },
                        body: JSON.stringify({ models: [modelName] })
                    });
                    const result = await res.json();
                    showToast(`Data "${modelName}" dihapus (${result.deleted} record)`, 'success');
                    loadModelStats();
                    loadStats();
                } catch (e) {
                    showToast('Gagal menghapus data', 'error');
                }
            }
        );
    }
    window.deleteModel = deleteModel;
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 9. Initial Load
    function init() {
        loadApiSettings();
        loadSkills();
        loadTools();
        loadStats();
        loadModelStats();
        
        // Cek jika hash ada di URL dan aktifkan section yang sesuai
        const hash = window.location.hash;
        if (hash) {
            const navItem = document.querySelector(`.nav-item[href="${hash}"]`);
            if (navItem) {
                navItem.click();
            }
        } else {
            // Load chart dan model stats jika Statistik adalah default
            loadUsageChart();
            loadModelStats();
        }
        
        // Setup Button Handlers
        document.getElementById('reload-skills-btn').onclick = async () => {
            try {
                const res = await fetch('/skills/reload', { 
                    method: 'POST',
                    headers: { 'X-API-Key': gatewayToken }
                });
                const data = await res.json();
                showToast(data.message, res.ok ? 'success' : 'error');
                loadSkills();
            } catch (e) { showToast('Gagal me-refresh skills', 'error'); }
        };
        document.getElementById('reload-tools-btn').onclick = async () => {
            try {
                const res = await fetch('/tools/reload', { 
                    method: 'POST',
                    headers: { 'X-API-Key': gatewayToken }
                });
                const data = await res.json();
                showToast(data.message, res.ok ? 'success' : 'error');
                loadTools();
            } catch (e) { showToast('Gagal me-refresh tools', 'error'); }
        };
        document.getElementById('download-template-btn').onclick = () => window.location.href = '/skills/template';
        document.getElementById('download-tool-template-btn').onclick = () => window.location.href = '/tools/template';
        
        // PW Toggle logic
        document.querySelectorAll('.toggle-pw').forEach(btn => {
            btn.onclick = (e) => {
                const input = e.target.previousElementSibling;
                if (input.type === 'password') {
                    input.type = 'text';
                    btn.textContent = '🙈';
                } else {
                    input.type = 'password';
                    btn.textContent = '👁';
                }
            };
        });
    }

    init();

})();
