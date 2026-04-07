        // ============================================
        // STATE & ICONS
        // ============================================
        const ICON_COPY = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
        const ICON_CHECK = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;

        let ws = null;
        let currentSessionId = null;
        let sessions = [];
        let currentAgentMessage = null;
        let currentAgentContent = '';
        let lastUserMessage = '';
        let isConnected = false;
        let isGenerating = false;
        let activeSkill = null;
        let sessionStartTime = null;
        let sessionStats = { requests: 0, inputTokens: 0, outputTokens: 0 };
        let typingStartTime = 0;
        let pendingReplace = null;
        // Auto-reconnect state
        let reconnectAttempts = 0;
        let reconnectTimer = null;
        let disconnectOverlayTimer = null;

        // Security Token — support ?token=xxx URL param for easy injection
        (function() {
            const urlParams = new URLSearchParams(window.location.search);
            const urlToken = urlParams.get('token');
            if (urlToken) {
                localStorage.setItem('kyuraa_gateway_token', urlToken);
                // Remove token from URL bar without reloading
                const cleanUrl = window.location.pathname;
                window.history.replaceState({}, document.title, cleanUrl);
            }
        })();
        let gatewayToken = localStorage.getItem('kyuraa_gateway_token') || '';

        // ============================================
        // DOM ELEMENTS
        // ============================================
        const sessionsList = document.getElementById('sessions-list');
        const messagesContainer = document.getElementById('messages-container');
        const welcomeScreen = document.getElementById('welcome-screen');
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        const cancelBtn = document.getElementById('cancel-btn');
        const settingsOverlay = document.getElementById('settings-overlay');
        const settingsContent = document.getElementById('settings-content');
        const modelBadge = document.getElementById('model-badge');
        const toastContainer = document.getElementById('toast-container');
        const confirmModal = document.getElementById('confirm-modal');

        // ============================================
        // UTILITIES
        // ============================================
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function showToast(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            toastContainer.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
            
            if (message.includes('401') || message.includes('Token tidak valid')) {
                askForToken();
            }
        }

        // ============================================
        // TOKEN MODAL
        // ============================================
        (function initTokenModal() {
            const overlay  = document.getElementById('token-modal-overlay');
            const input    = document.getElementById('token-input');
            const submitBtn = document.getElementById('token-submit');
            const toggleBtn = document.getElementById('token-toggle-visibility');
            const errorEl  = document.getElementById('token-error');

            function showError(msg) {
                errorEl.textContent = '⚠ ' + msg;
                errorEl.classList.remove('hidden');
                input.classList.add('shake');
                input.addEventListener('animationend', () => input.classList.remove('shake'), { once: true });
            }

            function clearError() {
                errorEl.classList.add('hidden');
            }

            toggleBtn.addEventListener('click', () => {
                const isHidden = input.type === 'password';
                input.type = isHidden ? 'text' : 'password';
                toggleBtn.textContent = isHidden ? '🙈' : '👁';
            });

            submitBtn.addEventListener('click', submitToken);

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') submitToken();
                if (e.key !== 'Tab') clearError();
            });

            // Dismiss on overlay click (outside modal card)
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    input.focus();
                    showError('Token diperlukan untuk melanjutkan.');
                }
            });

            function submitToken() {
                const token = input.value.trim();
                if (!token) {
                    showError('Token tidak boleh kosong.');
                    return;
                }
                submitBtn.disabled = true;
                submitBtn.textContent = 'Menghubungkan...';
                localStorage.setItem('kyuraa_gateway_token', token);
                gatewayToken = token;
                location.reload();
            }

            window._showTokenModal = function() {
                overlay.classList.remove('hidden');
                setTimeout(() => input.focus(), 100);
            };

            window._hideTokenModal = function() {
                overlay.classList.add('hidden');
            };
        })();

        function askForToken() {
            window._showTokenModal();
        }

        function formatRelativeDate(dateStr) {
            const date = new Date(dateStr);
            const now = new Date();
            const diffMs = now - date;
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
            
            if (diffDays === 0) return 'Hari ini';
            if (diffDays === 1) return 'Kemarin';
            if (diffDays === 2) return '2 hari lalu';
            if (diffDays < 7) return `${diffDays} hari lalu`;
            return date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
        }

        function generateId() {
            return 's-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9);
        }

        function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        function copyToClipboard(text, btn) {
            navigator.clipboard.writeText(text).then(() => {
                // Change icon to checkmark temporarily
                if (btn) {
                    btn.innerHTML = ICON_CHECK;
                    btn.classList.add('copied');
                    setTimeout(() => {
                        btn.innerHTML = ICON_COPY;
                        btn.classList.remove('copied');
                    }, 2000);
                }
                showToast('Pesan disalin!', 'success');
            }).catch(err => {
                console.error('Failed to copy text: ', err);
                showToast('Gagal menyalin pesan', 'error');
            });
        }

        function getFormattedTime() {
            const now = new Date();
            return now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
        }

        // ============================================
        // SKILL MANAGEMENT
        // ============================================
        async function fetchSkillStatus() {
            try {
                const res = await fetch('/skills', {
                    headers: { 'X-API-Key': gatewayToken }
                });
                const data = await res.json();
                if (data.active_skill) {
                    showSkillBadge(data.active_skill);
                } else {
                    hideSkillBadge();
                }
            } catch (e) {
                console.error('Failed to fetch skill status');
            }
        }

        function showSkillBadge(skillName) {
            activeSkill = skillName;
            updateHeaderSkillIndicator(skillName);
        }

        function hideSkillBadge() {
            activeSkill = null;
            updateHeaderSkillIndicator(null);
        }

        function updateHeaderSkillIndicator(skillName) {
            const badge = document.getElementById('header-skill-badge');
            if (!badge) return;
            
            if (!skillName) {
                badge.classList.add('hidden');
            } else {
                document.getElementById('header-skill-name').textContent = skillName;
                badge.classList.remove('hidden');
            }
        }

        async function updateSkillBadgeFromServer() {
            try {
                const res = await fetch('/skills', {
                    headers: { 'X-API-Key': gatewayToken }
                });
                const data = await res.json();
                if (data.active_skill) {
                    showSkillBadge(data.active_skill);
                } else {
                    hideSkillBadge();
                }
            } catch (e) {
                console.error('Failed to fetch skill status');
            }
        }

        async function deactivateSkill() {
            try {
                await fetch('/skills/deactivate', { method: 'POST' });
                hideSkillBadge();
                showToast('Skill dinonaktifkan', 'info');
            } catch (e) {
                console.error('Failed to deactivate skill');
            }
        }

        // Add event listener cleared (moved to settings UI only)
        // ============================================
        // STATS BAR
        // ============================================
        function updateStatsBar() {
            const footer = document.getElementById('input-footer');
            const totalTokens = sessionStats.inputTokens + sessionStats.outputTokens;
            footer.innerHTML = `
                <span class="stats-bar">
                    <span>Req: ${sessionStats.requests}</span>
                    <span class="stat-divider">·</span>
                    <span>In: ${sessionStats.inputTokens}</span>
                    <span class="stat-divider">·</span>
                    <span>Out: ${sessionStats.outputTokens}</span>
                    <span class="stat-divider">·</span>
                    <span class="stat-total">∑ ${totalTokens}</span>
                    ${sessionStartTime ? `<span class="stat-divider">·</span><span>⏱ ${getElapsedTime()}</span>` : ''}
                </span>
            `;
        }

        function getElapsedTime() {
            if (!sessionStartTime) return '0s';
            const elapsed = Date.now() - sessionStartTime;
            if (elapsed < 1000) return elapsed + 'ms';
            return (elapsed / 1000).toFixed(1) + 's';
        }

        // ============================================
        // WEBSOCKET
        // ============================================
        let isIntentionalClose = false;

        function updateConnectionStatus(status) {
            const dot = document.querySelector('.status-dot');
            const text = document.querySelector('.status-text');
            if (!dot || !text) return;
            
            dot.className = 'status-dot ' + status;
            if (status === 'connected') {
                text.textContent = 'Online';
            } else if (status === 'disconnected') {
                text.textContent = 'Offline';
            } else if (status === 'connecting') {
                text.textContent = 'Menghubungi...';
            }
        }

        function connectWebSocket(sessionId) {
            const sid = sessionId || currentSessionId;
            if (!sid) {
                console.error('connectWebSocket called with invalid sessionId:', sid);
                return;
            }
            sessionId = sid; // normalize

            isIntentionalClose = false;
            updateConnectionStatus('connecting');

            if (ws) {
                ws.close();
                ws = null;
            }

            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${location.host}/ws/${sessionId}?token=${gatewayToken}`;

            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                isConnected = true;
                reconnectAttempts = 0;  // Reset backoff saat berhasil
                if (reconnectTimer) {
                    clearTimeout(reconnectTimer);
                    reconnectTimer = null;
                }
                // Cancel pending disconnect overlay timer
                if (disconnectOverlayTimer) {
                    clearTimeout(disconnectOverlayTimer);
                    disconnectOverlayTimer = null;
                }
                updateConnectionStatus('connected');
                hideDisconnectOverlay();
                fetchSkillStatus();
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleWsMessage(data);
            };

            ws.onerror = (event) => {
                console.error('WS Error:', event);
                isConnected = false;
                updateConnectionStatus('disconnected');
            };

            ws.onclose = (e) => {
                isConnected = false;
                isGenerating = false;
                cancelBtn.classList.add('hidden');
                sendBtn.classList.remove('hidden');
                console.log(`WebSocket Disconnected: ${e.code} ${e.reason}`);
                
                if (e.code === 4001) {
                    showToast('⌛ Token tidak valid atau kadaluarsa.', 'error');
                    localStorage.removeItem('kyuraa_gateway_token');
                    askForToken();
                } else {
                    const statusEl = document.getElementById('reconnect-status');
                    if (statusEl) {
                        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                        statusEl.textContent = `Mencoba menyambung dalam ${Math.round(delay/1000)}s...`;
                        reconnectTimer = setTimeout(() => {
                            reconnectTimer = null;
                            if (currentSessionId && !isConnected && !isIntentionalClose) {
                                connectWebSocket(currentSessionId);
                            }
                        }, delay);
                    }
                    // Debounced disconnect overlay — tunda 500ms agar WS baru sempat tersambung
                    if (!isIntentionalClose) {
                        if (disconnectOverlayTimer) {
                            clearTimeout(disconnectOverlayTimer);
                        }
                        disconnectOverlayTimer = setTimeout(() => {
                            disconnectOverlayTimer = null;
                            if (!isConnected) {
                                showDisconnectOverlay();
                            }
                        }, 500);
                    }
                }
                updateConnectionStatus('disconnected');
                isIntentionalClose = false;
            };
        }

        function disconnectWebSocket() {
            isIntentionalClose = true;
            reconnectAttempts = 0;  // Reset backoff
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
            if (disconnectOverlayTimer) {
                clearTimeout(disconnectOverlayTimer);
                disconnectOverlayTimer = null;
            }
            if (ws) {
                ws.close();
                ws = null;
            }
            isConnected = false;
        }

        function showDisconnectOverlay() {
            document.getElementById('disconnect-overlay').classList.remove('hidden');
        }

        function hideDisconnectOverlay() {
            document.getElementById('disconnect-overlay').classList.add('hidden');
        }

        function manualReconnect() {
            if (currentSessionId) connectWebSocket();
        }

        document.getElementById('reconnect-btn').addEventListener('click', manualReconnect);
        document.getElementById('reload-btn').addEventListener('click', () => window.location.reload());

        function handleWsMessage(data) {
            if (data.type === 'token') {
                appendToken(data.content);
            } else if (data.type === 'done') {
                finishAgentMessage(data);
            } else if (data.type === 'error') {
                showToast(data.message, 'error');
                finishAgentMessage(data);
            } else if (data.type === 'file_saved') {
                showToast('File disimpan', 'success');
            }
        }

        // ============================================
        // SESSIONS
        // ============================================
        async function loadSessions() {
            try {
                const res = await fetch('/sessions', {
                    headers: { 'X-API-Key': gatewayToken }
                });
                if (res.status === 401) {
                    askForToken();
                    return;
                }
                const data = await res.json();
                // Filter out __system__ session
                sessions = (data.sessions || []).filter(s => s.session_id !== '__system__');
                renderSessions();
            } catch (e) {
                console.error('Failed to load sessions:', e);
                showToast('Gagal memuat sesi', 'error');
            }
        }

        function renderSessions() {
            if (sessions.length === 0) {
                sessionsList.innerHTML = '<div class="no-sessions">Belum ada sesi</div>';
                return;
            }
            
            // Group sessions by time
            const now = new Date();
            const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            const yesterday = new Date(today.getTime() - 86400000);
            const weekAgo = new Date(today.getTime() - 7 * 86400000);
            
            const groups = {
                'Hari ini': [],
                'Kemarin': [],
                '7 Hari Terakhir': [],
                'Lebih Lama': []
            };
            
            sessions.forEach(s => {
                const date = new Date(s.updated_at);
                if (date >= today) {
                    groups['Hari ini'].push(s);
                } else if (date >= yesterday) {
                    groups['Kemarin'].push(s);
                } else if (date >= weekAgo) {
                    groups['7 Hari Terakhir'].push(s);
                } else {
                    groups['Lebih Lama'].push(s);
                }
            });
            
            let html = '';
            Object.entries(groups).forEach(([groupName, groupSessions]) => {
                if (groupSessions.length === 0) return;
                
                html += `<div class="session-group-label">${groupName}</div>`;
                html += groupSessions.map(s => `
                    <div class="session-item ${s.session_id === currentSessionId ? 'active' : ''}" 
                         data-id="${s.session_id}">
                        <div class="session-name">${escapeHtml(s.name || 'Sesi baru')}</div>
                        <div class="session-preview">
                            ${s.updated_at ? formatRelativeDate(s.updated_at) : ''} · ${s.message_count || 0} pesan
                        </div>
                        <button class="session-delete" onclick="event.stopPropagation(); deleteSession('${s.session_id}')" title="Hapus sesi">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18m-2 0v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6.5m3 0V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2.5M10 11v6m4-6v6"/></svg>
                        </button>
                    </div>
                `).join('');
            });
            
            sessionsList.innerHTML = html;
            
            // Add click handlers
            document.querySelectorAll('.session-item').forEach(item => {
                item.addEventListener('click', () => selectSession(item.dataset.id));
            });
        }

        async function selectSession(sessionId) {
            currentSessionId = sessionId;
            
            // Mark active in sidebar
            document.querySelectorAll('.session-item').forEach(item => {
                item.classList.toggle('active', item.dataset.id === sessionId);
            });

            try {
                const res = await fetch(`/sessions/${sessionId}/messages`, {
                    headers: { 'X-API-Key': gatewayToken }
                });
                const data = await res.json();
                
                welcomeScreen.classList.add('hidden');
                messagesContainer.classList.remove('hidden');
                
                renderMessages(data.messages);
                scrollToBottom();
                
                // Connect WS if not connected
                if (!isConnected) connectWebSocket();
                
            } catch (e) {
                showToast('Gagal memuat pesan', 'error');
            }
        }

        async function createNewSession() {
            const newId = generateId();
            currentSessionId = newId;
            
            // Disconnect any existing WS first (intentional)
            isIntentionalClose = true;
            if (ws) {
                ws.close();
                ws = null;
            }
            
            // Clear messages and show welcome screen
            messagesContainer.innerHTML = '';
            welcomeScreen.classList.remove('hidden');
            messagesContainer.classList.add('hidden');
            
            // Connect WebSocket to new session
            connectWebSocket();
            
            // Focus input
            messageInput.focus();
        }

        async function deleteSession(sessionId) {
            showConfirm('Hapus sesi ini? Semua pesan akan hilang.', async () => {
                try {
                    const res = await fetch(`/sessions/${sessionId}`, { 
                        method: 'DELETE',
                        headers: { 'X-API-Key': gatewayToken }
                    });
                    if (res.ok) {
                        showToast('Sesi dihapus', 'info');
                        loadSessions();
                        if (currentSessionId === sessionId) {
                            currentSessionId = null;
                            messagesContainer.innerHTML = '';
                            welcomeScreen.classList.remove('hidden');
                            messagesContainer.classList.add('hidden');
                        }
                    }
                } catch (e) {
                    showToast('Gagal menghapus sesi', 'error');
                }
            });
        }

        // ============================================
        // MESSAGES
        // ============================================
        function renderMessages(messages) {
            messagesContainer.innerHTML = '';
            
            messages.forEach(msg => {
                if (msg.role === 'user') {
                    appendUserMessage(msg.content);
                } else if (msg.role === 'assistant') {
                    appendAgentMessage(msg.content);
                }
            });
            
            scrollToBottom();
        }

        function appendUserMessage(text) {
            const div = document.createElement('div');
            div.className = 'message-user';
            const time = getFormattedTime();
            div.innerHTML = `
                <div class="bubble">
                    <button class="bubble-copy-btn" title="Salin pesan">${ICON_COPY}</button>
                    <div class="bubble-text">${renderContent(text)}</div>
                    <div class="bubble-footer">
                        <span class="bubble-time">${time}</span>
                    </div>
                </div>


            `;
            // Fix XSS: gunakan addEventListener bukan onclick attribute
            const copyBtn = div.querySelector('.bubble-copy-btn');
            copyBtn.addEventListener('click', () => copyToClipboard(text, copyBtn));
            messagesContainer.appendChild(div);
            scrollToBottom();
        }

        function appendAgentMessage(text, stats = null) {
            const div = document.createElement('div');
            div.className = 'message-agent';
            const time = getFormattedTime();

            let statsHtml = '';
            if (stats) {
                statsHtml = `
                    <div class="bubble-stats">
                        Req: <span>${stats.req || '-'}</span> · 
                        In: <span>${stats.in || '-'}</span> · 
                        Out: <span>${stats.out || '-'}</span> · 
                        ∑: <span>${stats.total || '-'}</span> · 
                        ⏱: <span>${stats.latency || '-'}s</span>
                    </div>
                `;
            }

            div.innerHTML = `
                <div class="avatar" style="font-weight: 600; font-size: 13px;">K</div>
                <div class="content">
                    <div class="bubble">
                        <button class="bubble-copy-btn" title="Salin pesan">${ICON_COPY}</button>
                        <div class="bubble-text">${renderContent(text)}</div>
                        <div class="bubble-footer">
                            ${statsHtml}
                            <span class="bubble-time">${time}</span>
                        </div>
                    </div>
                </div>


            `;
            // Fix XSS: gunakan addEventListener bukan onclick attribute
            const copyBtn = div.querySelector('.bubble-copy-btn');
            copyBtn.addEventListener('click', () => copyToClipboard(text, copyBtn));
            messagesContainer.appendChild(div);
            scrollToBottom();
        }

        function startAgentMessage() {
            currentAgentContent = '';
            typingStartTime = Date.now();
            currentAgentMessage = document.createElement('div');
            currentAgentMessage.className = 'message-agent';
            currentAgentMessage.innerHTML = `
                <div class="avatar" style="font-weight: 600; font-size: 13px;">K</div>
                <div class="content">
                    <div class="bubble loading-mode">
                        <div class="bubble-text">
                            <div class="typing-indicator">
                                <span></span><span></span><span></span>
                            </div>
                        </div>
                        <div class="bubble-footer">
                            <div class="bubble-stats hidden"></div>
                            <span class="bubble-time"></span>
                        </div>
                    </div>
                </div>


            `;
            messagesContainer.appendChild(currentAgentMessage);
            scrollToBottom();
        }

        function appendToken(token) {
            currentAgentContent += token;

            if (!currentAgentMessage) {
                // Fallback: bubble tidak dibuat di sendMessage() (e.g. dari pesan lama)
                startAgentMessage();
                typingStartTime = Date.now();
                replaceDotsWithText();
                return;
            }

            const bubble = currentAgentMessage.querySelector('.bubble');
            const indicator = bubble?.querySelector('.typing-indicator');

            if (indicator) {
                // Dots masih tampil — pastikan minimum 800ms sebelum replace
                const elapsed = Date.now() - typingStartTime;
                if (elapsed >= 800) {
                    replaceDotsWithText();
                } else if (!pendingReplace) {
                    pendingReplace = setTimeout(() => {
                        pendingReplace = null;
                        replaceDotsWithText();
                    }, 800 - elapsed);
                }
            } else {
                // Dots sudah hilang, langsung append teks
                const textContainer = bubble.querySelector('.bubble-text');
                textContainer.innerHTML = renderContent(currentAgentContent);
                scrollToBottom();
            }
        }

        function replaceDotsWithText() {
            const bubble = currentAgentMessage.querySelector('.bubble');
            const indicator = bubble.querySelector('.typing-indicator');
            if (indicator) {
                indicator.remove();
            }
            bubble.classList.remove('loading-mode');
            const textContainer = bubble.querySelector('.bubble-text');
            textContainer.innerHTML = renderContent(currentAgentContent);
            scrollToBottom();
        }

        function parseMarkdown(text) {
            return text
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
                .replace(/`(.+?)`/g, '<code>$1</code>');
        }

        function renderContent(text) {
            if (!text) return '';

            // First escape HTML to prevent XSS
            let html = escapeHtml(text);

            // Extract code blocks first (before markdown parsing)
            const codeBlockPattern = /```[\s\S]*?```/g;
            const codeBlocks = [];
            html = html.replace(codeBlockPattern, (match, offset) => {
                const idx = codeBlocks.length;
                const codeContent = match.slice(4, -3);
                codeBlocks.push(`<pre class="code-block">${codeContent}</pre>`);
                return `%%CODEBLOCK_${idx}%%`;
            });

            // Parse markdown: **bold**, *italic*, `inline code`
            html = parseMarkdown(html);

            // Restore code blocks
            html = html.replace(/%%CODEBLOCK_(\d+)%%/g, (_, i) => codeBlocks[parseInt(i)]);

            // Preserve newlines by converting to <br>
            html = html.replace(/\n/g, '<br>');

            // Preserve multiple spaces
            html = html.replace(/  /g, '&nbsp; ');

            // Detect Arabic text blocks and apply RTL styling
            const arabicPattern = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+/g;
            if (arabicPattern.test(html)) {
                html = html.replace(/([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+)/g, '<span class="arabic-text" dir="rtl" lang="ar">$1</span>');
            }

            return html;
        }

        function finishAgentMessage(data) {
            if (!currentAgentMessage) return;

            if (pendingReplace) {
                clearTimeout(pendingReplace);
                pendingReplace = null;
            }

            const bubble = currentAgentMessage.querySelector('.bubble');

            // Remove any residual typing indicator
            const indicator = bubble.querySelector('.typing-indicator');
            if (indicator) indicator.remove();

            // Set final content
            const textContainer = bubble.querySelector('.bubble-text');
            textContainer.innerHTML = renderContent(currentAgentContent);
            
            // Set the timestamp now that we've finished generating
            const timeContainer = bubble.querySelector('.bubble-time');
            if (timeContainer) {
                timeContainer.textContent = getFormattedTime();
            }
            
            // Add copy button if not present
            if (!bubble.querySelector('.bubble-copy-btn')) {
                const btn = document.createElement('button');
                btn.className = 'bubble-copy-btn';
                btn.title = 'Salin pesan';
                btn.innerHTML = ICON_COPY;
                // Fix XSS: gunakan addEventListener, capture content saat button dibuat
                const contentSnapshot = currentAgentContent;
                btn.addEventListener('click', () => copyToClipboard(contentSnapshot, btn));
                bubble.insertBefore(btn, bubble.firstChild);
            }

            // Update stats for the bubble
            const usage = data.usage || (data.usage_per_message);
            if (usage) {
                const latency = ((Date.now() - sessionStartTime) / 1000).toFixed(1);
                sessionStats.requests++;
                sessionStats.inputTokens += usage.prompt_tokens || usage.input_tokens || 0;
                sessionStats.outputTokens += usage.completion_tokens || usage.output_tokens || 0;
                
                const statsContainer = bubble.querySelector('.bubble-stats');
                if (statsContainer) {
                    statsContainer.classList.remove('hidden');
                    statsContainer.innerHTML = `
                        Req: <span>${sessionStats.requests}</span> · 
                        In: <span>${usage.prompt_tokens || usage.input_tokens || '-'}</span> · 
                        Out: <span>${usage.completion_tokens || usage.output_tokens || '-'}</span> · 
                        ∑: <span>${(usage.prompt_tokens || usage.input_tokens || 0) + (usage.completion_tokens || usage.output_tokens || 0)}</span> · 
                        ⏱: <span>${latency}s</span>
                    `;
                }
                updateStatsBar();
            }
            
            // Fetch global stats and update settings panel
            fetch('/stats', {
                headers: { 'X-API-Key': gatewayToken }
            }).then(r => r.json()).then(stats => {
                const reqEl = document.getElementById('usage-requests');
                const inEl = document.getElementById('usage-input');
                const outEl = document.getElementById('usage-output');
                const totEl = document.getElementById('usage-total');
                if (reqEl) reqEl.textContent = stats.total_requests || 0;
                if (inEl) inEl.textContent = stats.input_tokens || 0;
                if (outEl) outEl.textContent = stats.output_tokens || 0;
                if (totEl) totEl.textContent = stats.total_tokens || 0;
            });
            
            // Check for skill activation in response
            const activatedMatch = currentAgentContent.match(/✅\s*Skill\s*\*?\*?([^\s*]+)\*?\*?\s*aktif/);
            if (activatedMatch) {
                showSkillBadge(activatedMatch[1]);
            }
            if (currentAgentContent.includes('✅ Skill dinonaktifkan') || currentAgentContent.includes('Skill dinonaktifkan')) {
                hideSkillBadge();
            }
            
            // Update session name with first 50 chars of user message
            if (currentSessionId && lastUserMessage) {
                const session = sessions.find(s => s.session_id === currentSessionId);
                if (session && (!session.name || session.name === 'Sesi baru')) {
                    const newName = lastUserMessage.substring(0, 50).replace(/\n/g, ' ').trim() + (lastUserMessage.length > 50 ? '...' : '');
                    session.name = newName;
                    fetch(`/sessions/${currentSessionId}/name`, {
                        method: 'PATCH',
                        headers: { 
                            'Content-Type': 'application/json',
                            'X-API-Key': gatewayToken 
                        },
                        body: JSON.stringify({ name: newName })
                    }).then(() => {
                        renderSessions();
                    });
                }
                lastUserMessage = '';
            }
            
            currentAgentMessage = null;
            currentAgentContent = '';
            
            isGenerating = false;
            cancelBtn.classList.add('hidden');
            sendBtn.classList.remove('hidden');
            sendBtn.disabled = false;
            scrollToBottom();
        }

        async function sendMessage() {
            const text = messageInput.value.trim();
            if (!text) return;

            if (!currentSessionId) {
                currentSessionId = generateId();
                connectWebSocket();
            }

            // Ensure the session is visibly added to the sidebar if not already present
            if (!sessions.find(s => s.session_id === currentSessionId)) {
                sessions.unshift({
                    session_id: currentSessionId,
                    name: 'Sesi baru',
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    message_count: 0
                });
                renderSessions();
            }

            // Wait for WS to be connected (either newly created or reconnecting)
            if (!isConnected) {
                for (let i = 0; i < 15; i++) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                    if (isConnected) break;
                }
            }

            if (!isConnected) {
                showToast('Tidak terhubung ke server', 'error');
                return;
            }

            // Start timing
            sessionStartTime = Date.now();

            // If still on welcome screen, switch to messages container
            if (!welcomeScreen.classList.contains('hidden')) {
                welcomeScreen.classList.add('hidden');
                messagesContainer.classList.remove('hidden');
            }

            // Store user message for auto-naming
            lastUserMessage = text;

            // Add user message bubble immediately
            appendUserMessage(text);

            // Show typing indicator immediately — before server responds
            currentAgentContent = '';
            startAgentMessage();
            typingStartTime = Date.now();

            // Send via WebSocket
            ws.send(JSON.stringify({ type: 'message', content: text }));

            // Clear input
            messageInput.value = '';
            messageInput.style.height = 'auto';

            // Disable send button while waiting
            isGenerating = true;
            sendBtn.disabled = true;
            sendBtn.classList.add('hidden');
            cancelBtn.classList.remove('hidden');

            updateStatsBar();
            scrollToBottom();
        }

        async function cancelMessage() {
            if (!isGenerating) return;
            
            if (currentSessionId) {
                try {
                    fetch(`/sessions/${currentSessionId}/messages/last`, {
                        method: 'DELETE',
                        headers: { 'X-API-Key': gatewayToken }
                    });
                } catch (e) {
                    console.error("Cancel API error", e);
                }
            }
            
            disconnectWebSocket();
            
            if (currentAgentMessage) currentAgentMessage.remove();
            const chatNodes = messagesContainer.children;
            if (chatNodes.length > 0) {
                const lastNode = chatNodes[chatNodes.length - 1];
                if (lastNode.classList.contains('message-user')) {
                    lastNode.remove();
                } else if (chatNodes.length > 1) {
                    const secondLastNode = chatNodes[chatNodes.length - 2];
                    if (secondLastNode.classList.contains('message-user')) secondLastNode.remove();
                }
            }
            
            messageInput.value = lastUserMessage;
            messageInput.style.height = 'auto';
            
            isGenerating = false;
            currentAgentMessage = null;
            currentAgentContent = '';
            
            cancelBtn.classList.add('hidden');
            sendBtn.classList.remove('hidden');
            sendBtn.disabled = false;
            
            setTimeout(() => {
                if(currentSessionId) connectWebSocket(currentSessionId);
            }, 300);
        }

        // ============================================
        // SETTINGS
        // ============================================
        function toggleSettings(show = true) {
            if (show) {
                settingsOverlay.classList.remove('hidden');
                renderSettingsContent();
            } else {
                settingsOverlay.classList.add('hidden');
            }
        }

        function renderSettingsContent() {
            settingsContent.innerHTML = `
                <div class="settings-section">
                    <h3>Tampilan</h3>
                    <div class="theme-selector" id="theme-selector">
                        <div class="theme-card-wrapper" data-value="light" onclick="setAppTheme('light')">
                            <div class="theme-card">
                                <div class="theme-mockup-light">
                                    <div class="theme-mockup-light-header"></div>
                                    <div class="theme-mockup-light-body"></div>
                                </div>
                            </div>
                            <span class="theme-label">Ringan</span>
                        </div>
                        <div class="theme-card-wrapper" data-value="auto" onclick="setAppTheme('auto')">
                            <div class="theme-card">
                                <div class="theme-mockup-auto">
                                    <div class="theme-mockup-auto-left">
                                        <div style="height: 10px; margin-bottom: 8px;"></div>
                                        <div class="theme-mockup-auto-body-left"></div>
                                    </div>
                                    <div class="theme-mockup-auto-right">
                                        <div class="theme-mockup-auto-header"></div>
                                        <div class="theme-mockup-auto-body-right"></div>
                                    </div>
                                </div>
                            </div>
                            <span class="theme-label">Otomatis</span>
                        </div>
                        <div class="theme-card-wrapper" data-value="dark" onclick="setAppTheme('dark')">
                            <div class="theme-card">
                                <div class="theme-mockup-dark">
                                    <div class="theme-mockup-dark-header"></div>
                                    <div class="theme-mockup-dark-body"></div>
                                </div>
                            </div>
                            <span class="theme-label">Gelap</span>
                        </div>
                    </div>
                </div>

                
                <div class="settings-divider"></div>

                <div id="provider-openrouter" class="settings-section">
                    <h3>Konfigurasi OpenRouter <span class="active-indicator hidden">Aktif</span></h3>
                    <div class="settings-field">
                        <label>AI Model</label>
                        <input type="text" id="setting-or-model" placeholder="Contoh: qwen/qwen3.6-plus:free">
                    </div>
                    <div class="settings-field">
                        <label>OpenRouter API Key</label>
                        <div class="pw-input-wrapper">
                            <input type="password" id="setting-or-api-key" class="pw-input" placeholder="Masukkan API Key...">
                            <button type="button" class="pw-toggle-btn" title="Tampilkan/Sembunyikan" onclick="const i=document.getElementById('setting-or-api-key'); if(i.type==='password'){i.type='text';this.textContent='🙈';}else{i.type='password';this.textContent='👁';}">👁</button>
                        </div>
                    </div>
                    <button class="save-provider-btn" data-provider="openrouter">Simpan & Gunakan OpenRouter</button>
                </div>
                
                <div class="settings-divider"></div>

                <div id="provider-google" class="settings-section">
                    <h3>Konfigurasi Google AI <span class="active-indicator hidden">Aktif</span></h3>
                    <div class="settings-field">
                        <label>AI Model</label>
                        <input type="text" id="setting-google-model" placeholder="Contoh: gemini-1.5-flash">
                    </div>
                    <div class="settings-field">
                        <label>Google API Key</label>
                        <div class="pw-input-wrapper">
                            <input type="password" id="setting-google-api-key" class="pw-input" placeholder="Masukkan API Key...">
                            <button type="button" class="pw-toggle-btn" title="Tampilkan/Sembunyikan" onclick="const i=document.getElementById('setting-google-api-key'); if(i.type==='password'){i.type='text';this.textContent='🙈';}else{i.type='password';this.textContent='👁';}">👁</button>
                        </div>
                    </div>
                    <button class="save-provider-btn" data-provider="google">Simpan & Gunakan Google AI</button>
                </div>
                
                <div class="settings-divider"></div>
                
                <div class="settings-section">
                    <h3>Usage Statistics</h3>
                    <div id="usage-stats">
                        <div class="stat-row"><span>Total Requests</span><span id="usage-requests">0</span></div>
                        <div class="stat-row"><span>Input Tokens</span><span id="usage-input">0</span></div>
                        <div class="stat-row"><span>Output Tokens</span><span id="usage-output">0</span></div>
                        <div class="stat-row"><span>Total Tokens</span><span id="usage-total">0</span></div>
                    </div>
                </div>

                
                <div class="settings-section">
                    <h3> Skill Management</h3>
                    <div id="skills-count-badge">Memuat skills...</div>
                    <div id="skills-list"></div>
                    <div class="tools-action-row">
                        <button id="reload-skills-btn" class="settings-secondary-btn"> Reload Skills</button>
                        <button id="download-template-btn" class="settings-secondary-btn"> Download Template Skill</button>
                    </div>
                    <div style="font-size:11px;color:var(--text-muted);margin-top:10px;line-height:1.6;">
                         Skill memberikan instruksi khusus secara global. <strong>Maksimal 1 skill aktif</strong> pada satu waktu.
                    </div>
                </div>

                </div>

                <div class="settings-divider"></div>

                <div class="settings-section">
                    <h3> Tools Management</h3>
                    <div id="tools-count-badge">Memuat tools...</div>
                    <div id="tools-builtin-label" class="tools-section-label">Built-in Tools</div>
                    <div id="tools-builtin-list"></div>
                    <div id="tools-custom-label" class="tools-section-label" style="display:none">Custom Tools</div>
                    <div id="tools-custom-list"></div>
                    <div class="tools-action-row">
                        <button id="reload-tools-btn" class="settings-secondary-btn"> Reload Tools</button>
                        <button id="download-tool-template-btn" class="settings-secondary-btn"> Download Template Tool</button>
                    </div>
                    <div style="font-size:11px;color:var(--text-muted);margin-top:10px;line-height:1.6;">
                         Taruh file <code>.py</code> di <code>workspace/tools/</code> lalu klik Reload.
                    </div>
                </div>


            `;
            
            // Load settings
            fetch('/settings', {
                headers: { 'X-API-Key': gatewayToken }
            }).then(r => r.json()).then(data => {
                if (data.detail && data.detail.includes('Akses dilarang')) {
                    askForToken();
                    return;
                }
                // Populate OpenRouter
                document.getElementById('setting-or-model').value = data.openrouter.model || '';
                document.getElementById('setting-or-api-key').value = data.openrouter.api_key || '';
                
                // Populate Google
                document.getElementById('setting-google-model').value = data.google.model || '';
                document.getElementById('setting-google-api-key').value = data.google.api_key || '';
                
                // Highlight active
                const active = data.active_provider || 'openrouter';
                const activeCard = document.getElementById(`provider-${active}`);
                if (activeCard) {
                    activeCard.classList.add('active-provider');
                    activeCard.querySelector('.active-indicator').classList.remove('hidden');
                }
            });

            // Highlight active theme
            const activeTheme = localStorage.getItem('kyuraa_theme') || 'auto';
            document.querySelectorAll('.theme-card-wrapper').forEach(card => {
                if(card.dataset.value === activeTheme) {
                    card.classList.add('active');
                }
            });
            
            // Load stats
            fetch('/stats', {
                headers: { 'X-API-Key': gatewayToken }
            }).then(r => r.json()).then(data => {
                const reqEl = document.getElementById('usage-requests');
                const inEl = document.getElementById('usage-input');
                const outEl = document.getElementById('usage-output');
                const totEl = document.getElementById('usage-total');
                if (reqEl) reqEl.textContent = data.total_requests || 0;
                if (inEl) inEl.textContent = data.input_tokens || 0;
                if (outEl) outEl.textContent = data.output_tokens || 0;
                if (totEl) totEl.textContent = data.total_tokens || 0;
            });
            
            // --- Skills Management INIT ---
            loadSkillsSettings();

            const downloadBtn = document.getElementById('download-template-btn');
            if (downloadBtn) {
                downloadBtn.addEventListener('click', () => {
                    window.location.href = '/skills/template';
                });
            }

            const reloadSkillsBtn = document.getElementById('reload-skills-btn');
            if (reloadSkillsBtn) {
                reloadSkillsBtn.addEventListener('click', async () => {
                    reloadSkillsBtn.disabled = true;
                    reloadSkillsBtn.textContent = 'Memuat...';
                    try {
                        const res = await fetch('/skills/reload', {
                            method: 'POST',
                            headers: { 'X-API-Key': gatewayToken }
                        });
                        const data = await res.json();
                        showToast(data.message || 'Skills direload!', 'success');
                        loadSkillsSettings();
                    } catch (e) {
                        showToast('Gagal reload skills', 'error');
                    } finally {
                        reloadSkillsBtn.disabled = false;
                        reloadSkillsBtn.textContent = ' Reload Skills';
                    }
                });
            }

            // --- Tools Management INIT ---
            loadToolsSettings();

            const downloadToolBtn = document.getElementById('download-tool-template-btn');
            if (downloadToolBtn) {
                downloadToolBtn.addEventListener('click', () => {
                    window.location.href = '/tools/template';
                });
            }

            const reloadToolsBtn = document.getElementById('reload-tools-btn');
            if (reloadToolsBtn) {
                reloadToolsBtn.addEventListener('click', async () => {
                    reloadToolsBtn.disabled = true;
                    reloadToolsBtn.textContent = 'Memuat...';
                    try {
                        const res = await fetch('/tools/reload', {
                            method: 'POST',
                            headers: { 'X-API-Key': gatewayToken }
                        });
                        const data = await res.json();
                        showToast(data.message || 'Tools direload!', 'success');
                        loadToolsSettings();
                    } catch (e) {
                        showToast('Gagal reload tools', 'error');
                    } finally {
                        reloadToolsBtn.disabled = false;
                        reloadToolsBtn.textContent = ' Reload Tools';
                    }
                });
            }
            
            // Save button handlers (multiple buttons)
            document.querySelectorAll('.save-provider-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const provider = btn.dataset.provider;
                    const model = document.getElementById(`setting-${provider === 'openrouter' ? 'or' : 'google'}-model`).value.trim();
                    const apiKey = document.getElementById(`setting-${provider === 'openrouter' ? 'or' : 'google'}-api-key`).value.trim();
                    
                    if (!model || !apiKey) {
                        showToast('Mohon isi model dan API Key', 'error');
                        return;
                    }
                    
                    const payload = { provider, model, api_key: apiKey };
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
                            body: JSON.stringify(payload)
                        });
                        
                        const result = await res.json();
                        if (res.ok) {
                            showToast(result.message || `Koneksi ${provider} berhasil!`, 'success');
                            renderSettingsContent(); // Refresh UI to show active provider
                            fetchModelInfo();
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
        }

        // ============================================
        // CONFIRM MODAL
        // ============================================
        let confirmCallback = null;

        function showConfirm(message, onConfirm) {
            document.getElementById('confirm-message').textContent = message;
            confirmModal.classList.remove('hidden');
            confirmCallback = onConfirm;
        }

        function hideConfirm() {
            confirmModal.classList.add('hidden');
            confirmCallback = null;
        }

        document.getElementById('confirm-cancel').addEventListener('click', hideConfirm);
        document.getElementById('confirm-ok').addEventListener('click', () => {
            if (confirmCallback) confirmCallback();
            hideConfirm();
        });
        document.querySelector('.confirm-backdrop').addEventListener('click', hideConfirm);

        // ============================================
        // FETCH INITIAL STATE
        // ============================================
        async function fetchModelInfo() {
            try {
                const res = await fetch('/info');
                const data = await res.json();
                modelBadge.textContent = data.model || 'Unknown';
            } catch (e) {
                modelBadge.textContent = 'Offline';
            }
        }

        // ============================================
        // EVENT LISTENERS
        // ============================================
        document.getElementById('new-session-btn').addEventListener('click', createNewSession);
        document.getElementById('sidebar-toggle').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('collapsed');
        });
        document.getElementById('sidebar-settings-btn').addEventListener('click', () => toggleSettings(true));
        document.getElementById('settings-close').addEventListener('click', () => toggleSettings(false));
        settingsOverlay.addEventListener('click', (e) => {
            if (e.target === settingsOverlay) toggleSettings(false);
        });

        sendBtn.addEventListener('click', sendMessage);
        cancelBtn.addEventListener('click', cancelMessage);
        
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });


        // ============================================
        // INITIALIZE
        // ============================================
        async function init() {
            await loadSessions();
            await fetchModelInfo();
            updateStatsBar();
            updateSkillBadgeFromServer();
            
            if (sessions.length > 0) {
                selectSession(sessions[0].session_id);
            }
        }

        init();

        // ============================================
        // THEME MANAGEMENT
        // ============================================
        function setAppTheme(theme) {
            localStorage.setItem('kyuraa_theme', theme);
            let isDark = false;
            if (theme === 'dark') {
                isDark = true;
            } else if (theme === 'auto') {
                isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            }
            if (isDark) {
                document.documentElement.setAttribute('data-theme', 'dark');
            } else {
                document.documentElement.removeAttribute('data-theme');
            }
            
            // Update active state in UI if settings modal is open
            document.querySelectorAll('.theme-card-wrapper').forEach(card => {
                card.classList.toggle('active', card.dataset.value === theme);
            });
        }
        
        // Listen for OS theme changes for auto mode
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            const savedTheme = localStorage.getItem('kyuraa_theme') || 'auto';
            if (savedTheme === 'auto') {
                if (e.matches) document.documentElement.setAttribute('data-theme', 'dark');
                else document.documentElement.removeAttribute('data-theme');
            }
        });

        // ============================================
        // TOOLS MANAGEMENT LOGIC
        // ============================================
        async function loadToolsSettings() {
            const countBadge = document.getElementById('tools-count-badge');
            const builtinList = document.getElementById('tools-builtin-list');
            const customList = document.getElementById('tools-custom-list');
            const customLabel = document.getElementById('tools-custom-label');
            
            try {
                const res = await fetch('/tools', {
                    headers: { 'X-API-Key': gatewayToken }
                });
                const data = await res.json();
                
                if (countBadge) countBadge.textContent = `${data.enabled || 0} tool aktif dari total ${data.total || 0}`;
                
                const builtin = data.tools.filter(t => t.source === 'built-in');
                const custom = data.tools.filter(t => t.source === 'custom');
                
                if (builtinList) {
                    builtinList.innerHTML = builtin.map(t => renderToolItem(t)).join('');
                }
                
                if (customList) {
                    if (custom.length > 0) {
                        customList.innerHTML = custom.map(t => renderToolItem(t)).join('');
                        customLabel.style.display = 'block';
                    } else {
                        customList.innerHTML = '';
                        customLabel.style.display = 'none';
                    }
                }
            } catch (e) {
                if (countBadge) countBadge.textContent = 'Gagal memuat tools';
            }
        }

        function renderToolItem(tool) {
            return `
                <div class="tool-item">
                    <div class="tool-item-info">
                        <div class="tool-item-name">
                            ${tool.name}
                            <span class="tool-badge ${tool.source === 'built-in' ? 'builtin' : 'custom'}">
                                ${tool.source === 'built-in' ? 'Built-in' : 'Custom'}
                            </span>
                        </div>
                        <div class="tool-item-desc" title="${tool.description}">${tool.description}</div>
                    </div>
                    <label class="toggle-switch">
                        <input type="checkbox" ${tool.enabled ? 'checked' : ''} onchange="toggleTool('${tool.name}', this)">
                        <span class="toggle-slider"></span>
                    </label>
                </div>
            `;
        }

        async function toggleTool(name, checkbox) {
            checkbox.disabled = true;
            try {
                const res = await fetch(`/tools/${name}/toggle`, {
                    method: 'POST',
                    headers: { 'X-API-Key': gatewayToken }
                });
                const data = await res.json();
                if (res.ok) {
                    showToast(data.message, 'success');
                    // Refresh count badge
                    const res2 = await fetch('/tools', { headers: { 'X-API-Key': gatewayToken } });
                    const data2 = await res2.json();
                    const countBadge = document.getElementById('tools-count-badge');
                    if (countBadge) countBadge.textContent = `${data2.enabled || 0} tool aktif dari total ${data2.total || 0}`;
                } else {
                    checkbox.checked = !checkbox.checked;
                    showToast(data.detail || 'Gagal mengubah status tool', 'error');
                }
            } catch (e) {
                checkbox.checked = !checkbox.checked;
                showToast('Kesalahan koneksi', 'error');
            } finally {
                checkbox.disabled = false;
            }
        }

        // ============================================
        // SKILLS MANAGEMENT LOGIC
        // ============================================
        async function loadSkillsSettings() {
            const countBadge = document.getElementById('skills-count-badge');
            const skillsList = document.getElementById('skills-list');
            
            try {
                const res = await fetch('/skills', {
                    headers: { 'X-API-Key': gatewayToken }
                });
                const data = await res.json();
                
                if (countBadge) {
                    if (data.active_skill) {
                        countBadge.innerHTML = `Skill Aktif: <strong>${data.active_skill}</strong>`;
                    } else {
                        countBadge.textContent = `Tidak ada skill aktif (Mode Normal)`;
                    }
                }
                
                if (skillsList) {
                    if (data.skills && data.skills.length > 0) {
                        skillsList.innerHTML = data.skills.map(s => renderSkillItem(s)).join('');
                    } else {
                        skillsList.innerHTML = '<div class="no-skills">Belum ada skill terpasang</div>';
                    }
                }
            } catch (e) {
                if (countBadge) countBadge.textContent = 'Gagal memuat skills';
            }
        }

        function renderSkillItem(skill) {
            return `
                <div class="tool-item ${skill.is_active ? 'active-skill-item' : ''}">
                    <div class="tool-item-info">
                        <div class="tool-item-name">
                            ${skill.name}
                            ${skill.is_active ? '<span class="tool-badge builtin">Aktif</span>' : ''}
                            <span class="tool-badge custom" style="background:var(--bg-tertiary);color:var(--text-secondary)">v${skill.version || '1.0'}</span>
                        </div>
                        <div class="tool-item-desc">${skill.description}</div>
                        <div class="tool-item-desc" style="font-size:10px; margin-top:4px;">
                            Ref: ${skill.references_count || 0} file | By: ${skill.author || 'Unknown'} | Kat: ${skill.category || 'Umum'}
                        </div>
                    </div>
                    <div>
                        ${skill.is_active 
                            ? `<button class="settings-secondary-btn" onclick="setSkillActive(null)" style="color:var(--accent-danger);border-color:var(--accent-danger)">Nonaktifkan</button>`
                            : `<button class="settings-secondary-btn" onclick="setSkillActive('${skill.name}')">Aktifkan</button>`
                        }
                    </div>
                </div>
            `;
        }

        async function setSkillActive(skillName) {
            try {
                const url = skillName ? `/skills/${skillName}/activate` : '/skills/deactivate';
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'X-API-Key': gatewayToken }
                });
                const data = await res.json();
                
                if (res.ok) {
                    showToast(data.message, 'success');
                    loadSkillsSettings(); // Refresh UI list
                    updateSkillBadgeFromServer(); // Refresh badge on header
                } else {
                    showToast(data.detail || 'Gagal mengubah skill', 'error');
                }
            } catch (e) {
                showToast('Kesalahan koneksi', 'error');
            }
        }

        // Expose functions to global scope for onclick handlers
        window.toggleTool = toggleTool;
        window.setSkillActive = setSkillActive;
        window.deleteSession = deleteSession;
