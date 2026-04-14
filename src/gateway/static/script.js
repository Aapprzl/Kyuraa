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
        
        // File upload state
        let pendingFile = null;  // {file_id, filename, text, script, page_count, word_count}
        let sessionFiles = []; // Array berkas untuk sidebar kanan
        let totalInputTokensThisSession = 0; // Tracking untuk suggestion sesi baru

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
        const modelBadge = document.getElementById('model-badge');
        const toastContainer = document.getElementById('toast-container');
        const confirmModal = document.getElementById('confirm-modal');
        const sidebarRight = document.getElementById('sidebar-right');
        const sidebarRightToggle = document.getElementById('sidebar-right-toggle');
        const sidebarRightClose = document.getElementById('sidebar-right-close');
        const sessionFilesList = document.getElementById('session-files-list');

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

        function renderFileCard(metadata) {
            if (!metadata || !metadata.filename) return '';
            const pageInfo = metadata.page_count ? `${metadata.page_count} halaman` : '';
            const scriptInfo = metadata.script ? ` · ${metadata.script}` : '';
            
            const hasText = metadata.text && metadata.text.trim().length > 0;
            const viewScanBtn = hasText ? `
                <div class="bubble-file-actions">
                    <button class="btn-view-scan">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
                        Lihat Hasil Scan
                    </button>
                </div>
            ` : '';

            return `
                <div class="bubble-file-card">
                    <div class="bubble-file-icon">PDF</div>
                    <div class="bubble-file-info">
                        <div class="bubble-file-name" title="${escapeHtml(metadata.filename)}">${escapeHtml(metadata.filename)}</div>
                        <div class="bubble-file-meta">${pageInfo}${scriptInfo}</div>
                    </div>
                    ${viewScanBtn}
                </div>
            `;
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

        // ============================================
        // FILE UPLOAD
        // ============================================
        function showFilePreview(file) {
            const preview = document.getElementById('file-preview');
            const nameEl = preview.querySelector('.file-name');
            const metaEl = preview.querySelector('.file-meta');
            
            nameEl.textContent = file.filename;
            metaEl.textContent = `${file.page_count} halaman · ${file.script}`;
            
            preview.classList.remove('hidden');
        }

        function hideFilePreview() {
            const preview = document.getElementById('file-preview');
            preview.classList.add('hidden');
        }

        function showLargeFileWarning(data) {
            const modal = document.getElementById('large-file-modal');
            const nameEl = modal.querySelector('.large-file-name');
            const pagesEl = document.getElementById('large-file-pages');
            const wordsEl = document.getElementById('large-file-words');
            const tokensEl = document.getElementById('large-file-tokens');
            
            nameEl.textContent = data.filename;
            pagesEl.textContent = `${data.page_count} halaman`;
            wordsEl.textContent = `${data.word_count.toLocaleString()} kata`;
            tokensEl.textContent = `~${data.estimated_tokens.toLocaleString()} tokens`;
            
            modal.classList.remove('hidden');
        }

        function hideLargeFileWarning() {
            const modal = document.getElementById('large-file-modal');
            modal.classList.add('hidden');
        }

        // File input handler
        const fileInput = document.getElementById('file-input');
        const uploadBtn = document.getElementById('upload-btn');
        const removeFileBtn = document.getElementById('remove-file-btn');
        const lfSendAll = document.getElementById('lf-send-all');
        const lfSendPartial = document.getElementById('lf-send-partial');
        const lfCancel = document.getElementById('lf-cancel');

        if (fileInput) {
            fileInput.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                
                if (!file.name.toLowerCase().endsWith('.pdf')) {
                    showToast('Hanya file PDF yang diizinkan', 'error');
                    e.target.value = '';
                    return;
                }
                
                const MAX_SIZE = 5 * 1024 * 1024; // 5MB
                if (file.size > MAX_SIZE) {
                    showToast('File terlalu besar (max 5MB)', 'error');
                    e.target.value = '';
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', file);
                
                showToast('Mengunggah & memindai PDF (Mohon tunggu, ada OCR jika file berupa scan)...', 'info', 0);
                
                // UI Loading State
                const originalUploadHTML = uploadBtn.innerHTML;
                uploadBtn.classList.add('uploading');
                uploadBtn.innerHTML = `<svg class="spin-anim" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>`;
                fileInput.disabled = true;
                if (window.sendBtn) sendBtn.disabled = true;
                
                try {
                    const res = await fetch('/upload', {
                        method: 'POST',
                        headers: { 'X-API-Key': gatewayToken },
                        body: formData
                    });
                    
                    if (!res.ok) {
                        const err = await res.json();
                        showToast(err.detail || 'Upload gagal', 'error');
                        return;
                    }
                    
                    const data = await res.json();
                    
                    pendingFile = {
                        file_id: data.file_id,
                        filename: data.filename,
                        text: data.text,
                        script: data.script,
                        page_count: data.page_count,
                        word_count: data.word_count,
                        estimated_tokens: data.estimated_tokens
                    };
                    
                    if (data.exceeds_limit) {
                        showLargeFileWarning(data);
                    } else {
                        showFilePreview(pendingFile);
                        if (!data.text || data.text.trim().length === 0) {
                            showToast(`File "${data.filename}" berupa gambar/scan, teks tidak terbaca`, 'warn', 5000);
                        } else {
                            showToast(`PDF "${data.filename}" siap dikirim`, 'success');
                        }
                    }
                    
                } catch (e) {
                    showToast('Gagal upload file', 'error');
                } finally {
                    // Restore UI
                    uploadBtn.classList.remove('uploading');
                    uploadBtn.innerHTML = originalUploadHTML;
                    fileInput.disabled = false;
                    if (window.sendBtn) sendBtn.disabled = false;
                }
                
                e.target.value = '';
            };
        }

        // Upload button handler
        if (uploadBtn) {
            uploadBtn.onclick = () => {
                fileInput.click();
            };
        }

        // Remove file button handler
        if (removeFileBtn) {
            removeFileBtn.onclick = () => {
                pendingFile = null;
                hideFilePreview();
            };
        }

        // Large file modal handlers
        if (lfSendAll) {
            lfSendAll.onclick = () => {
                hideLargeFileWarning();
                showFilePreview(pendingFile);
                showToast(`PDF "${pendingFile.filename}" siap dikirim`, 'success');
            };
        }

        if (lfSendPartial) {
            lfSendPartial.onclick = async () => {
                hideLargeFileWarning();
                showToast('Memuat halaman (Mohon tunggu, ada OCR jika file berupa scan)...', 'info', 0);
                
                const originalUploadHTML = uploadBtn.innerHTML;
                uploadBtn.classList.add('uploading');
                uploadBtn.innerHTML = `<svg class="spin-anim" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>`;
                fileInput.disabled = true;
                if (window.sendBtn) sendBtn.disabled = true;

                try {
                    const res = await fetch('/upload/partial', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                            'X-API-Key': gatewayToken
                        },
                        body: JSON.stringify({
                            file_id: pendingFile.file_id,
                            page_start: 1,
                            page_end: 10
                        })
                    });
                    
                    if (!res.ok) {
                        const err = await res.json();
                        showToast(err.detail || 'Gagal mengambil halaman', 'error');
                        return;
                    }
                    
                    const data = await res.json();
                    
                    pendingFile.text = data.text;
                    pendingFile.page_count = data.page_count;
                    pendingFile.word_count = data.word_count;
                    pendingFile.estimated_tokens = data.estimated_tokens;
                    
                    showFilePreview(pendingFile);
                    showToast(`Halaman 1-10 dimuat (~${data.estimated_tokens} tokens)`, 'success');
                    
                } catch (e) {
                    showToast('Gagal mengambil halaman', 'error');
                } finally {
                    uploadBtn.classList.remove('uploading');
                    uploadBtn.innerHTML = originalUploadHTML;
                    fileInput.disabled = false;
                    if (window.sendBtn) sendBtn.disabled = false;
                }
            };
        }

        if (lfCancel) {
            lfCancel.onclick = () => {
                hideLargeFileWarning();
                pendingFile = null;
                hideFilePreview();
                showToast('Upload dibatalkan', 'info');
            };
        }

        // Add event listener cleared (moved to settings UI only)
        // ============================================
        // STATS BAR
        // ============================================
        function updateStatsBar() {
            const footer = document.getElementById('input-footer');
            footer.innerHTML = `Enter untuk kirim · Shift+Enter baris baru`;
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
                
                // Track input tokens to check context window fullness
                if (data.usage && data.usage.input_tokens) {
                    totalInputTokensThisSession += data.usage.input_tokens;
                    checkContextFullness();
                }
            } else if (data.type === 'error') {
                showToast(data.message, 'error');
                finishAgentMessage(data);
            } else if (data.type === 'info') {
                showToast(data.message, 'info');
            } else if (data.type === 'file_saved') {
                showToast('File disimpan', 'success');
            } else if (data.type === 'approval_request') {
                handleApprovalRequest(data);
            }
        }

        function handleApprovalRequest(data) {
            const tool = data.tool;
            const params = data.params;
            
            const div = document.createElement('div');
            div.className = 'approval-card';
            div.innerHTML = `
                <div class="approval-header">
                    <span>🛡️ Izin Diperlukan</span>
                </div>
                <div class="approval-body">
                    <p style="font-size: 13px; margin-bottom: 8px;">Kyuraa ingin menjalankan aksi sensitif:</p>
                    <div class="approval-tool-info">
                        <strong>Tool:</strong> ${tool}<br>
                        <strong>Params:</strong> ${JSON.stringify(params)}
                    </div>
                </div>
                <div class="approval-actions">
                    <button class="btn-deny">Tolak</button>
                    <button class="btn-approve">Izinkan</button>
                </div>
            `;

            const approveBtn = div.querySelector('.btn-approve');
            const denyBtn = div.querySelector('.btn-deny');

            approveBtn.addEventListener('click', () => {
                ws.send(JSON.stringify({ type: 'approval_response', approved: true }));
                div.innerHTML = '<div style="color: #27ae60; font-size: 12px; font-weight: 600;">✅ Aksi Diizinkan</div>';
                setTimeout(() => div.remove(), 2000);
            });

            denyBtn.addEventListener('click', () => {
                ws.send(JSON.stringify({ type: 'approval_response', approved: false }));
                div.innerHTML = '<div style="color: #e74c3c; font-size: 12px; font-weight: 600;">❌ Aksi Ditolak</div>';
                setTimeout(() => div.remove(), 2000);
            });

            messagesContainer.appendChild(div);
            scrollToBottom();
        }

        function checkContextFullness() {
            // Threshold: 25.000 tokens (limit is ~30k)
            const THRESHOLD = 25000;
            if (totalInputTokensThisSession > THRESHOLD) {
                showFullContextSuggestion();
            }
        }

        function showFullContextSuggestion() {
            // Hanya tampilkan jika belum ada suggestion di layar
            if (document.querySelector('.session-suggestion')) return;

            const div = document.createElement('div');
            div.className = 'session-suggestion';
            div.innerHTML = `
                <div class="suggestion-title">⚠️ Memori Hampir Penuh</div>
                <div class="suggestion-text">Percakapan ini sudah cukup panjang. Untuk menjaga ketajaman ingatan Agen, sebaiknya lanjutkan di sesi baru. Agen akan tetap membawa ringkasan diskusi ini ke sana.</div>
                <button class="btn-connect-session" onclick="createConnectedSession()">Lanjutkan di Sesi Baru</button>
            `;
            messagesContainer.appendChild(div);
            scrollToBottom();
        }

        async function createConnectedSession() {
            if (!currentSessionId) return;
            
            showToast('Menyiapkan estafet sesi (Merangkum diskusi)...', 'info', 0);
            
            try {
                const res = await fetch(`/sessions/${currentSessionId}/connected`, {
                    method: 'POST',
                    headers: { 'X-API-Key': gatewayToken }
                });
                
                if (!res.ok) throw new Error('Gagal membuat sesi terhubung');
                
                const data = await res.json();
                
                // Berhasil! Pindah ke sesi baru
                loadSessions(); // Refresh list sidebar kiri
                selectSession(data.session_id);
                showToast('Berhasil pindah ke sesi baru dengan rangkuman!', 'success');
                
            } catch (e) {
                showToast('Gagal memproses estafet sesi', 'error');
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
            totalInputTokensThisSession = 0; // Reset tracking
            
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
                
                // Track total tokens from previous messages
                totalInputTokensThisSession = data.messages.reduce((sum, m) => sum + (m.token_count || 0), 0);
                
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
            sessionFiles = []; // Reset file list
            
            messages.forEach((msg, index) => {
                if (msg.role === 'user') {
                    // Assign temporary ID for scrolling if it doesn't have one
                    const msgId = `msg-${index}`;
                    appendUserMessage(msg.content, msg.metadata, msgId);
                    
                    if (msg.metadata && msg.metadata.file_id && !msg.metadata.deleted) {
                        sessionFiles.push({
                            ...msg.metadata,
                            msgId: msgId
                        });
                    }
                } else if (msg.role === 'assistant') {
                    appendAgentMessage(msg.content);
                }
            });
            
            updateFileSidebar();
            scrollToBottom();
        }

        function appendUserMessage(text, metadata = null, id = null) {
            const div = document.createElement('div');
            div.className = 'message-user';
            if (id) div.id = id;
            const time = getFormattedTime();
            
            // Cek apakah ini pesan file (baik aktif maupun sudah dihapus)
            const isFileEntry = metadata && metadata.file_id;
            const isJustFile = text === '(PDF attached)' || !text;
            const cleanText = text ? text.replace('(PDF attached)', '').trim() : '';
            
            let displayHtml = '';
            
            if (metadata && !metadata.deleted) {
                // Berkas aktif
                const fileHtml = renderFileCard(metadata);
                const textHtml = cleanText ? `<div class="bubble-text">${renderContent(cleanText)}</div>` : '';
                displayHtml = fileHtml + textHtml;
            } else if (metadata && metadata.deleted) {
                // Berkas sudah dihapus (info tetap ada di metadata)
                const fileName = metadata.filename || 'Berkas';
                const deletedNotice = `<div class="file-deleted-notice">📂 Berkas <strong>${escapeHtml(fileName)}</strong> telah dihapus</div>`;
                const textHtml = cleanText ? `<div class="bubble-text">${renderContent(cleanText)}</div>` : '';
                displayHtml = deletedNotice + textHtml;
            } else {
                // Pesan teks biasa
                displayHtml = `<div class="bubble-text">${renderContent(text)}</div>`;
            }

            div.innerHTML = `
                <div class="bubble ${isJustFile && metadata && !metadata.deleted ? 'file-only' : ''}">
                    <button class="bubble-copy-btn" title="Salin pesan">${ICON_COPY}</button>
                    ${displayHtml}
                    <div class="bubble-footer">
                        <span class="bubble-time">${time}</span>
                    </div>
                </div>
            `;
            // Fix XSS
            const copyBtn = div.querySelector('.bubble-copy-btn');
            copyBtn.addEventListener('click', () => copyToClipboard(text || '', copyBtn));

            const viewBtn = div.querySelector('.btn-view-scan');
            if (viewBtn && metadata) {
                viewBtn.addEventListener('click', () => showOCRModal(metadata));
            }

            messagesContainer.appendChild(div);

            // Jika ini pesan baru (bukan dari render history), tambahkan ke sidebar
            if (!id && metadata && metadata.file_id) {
                const newId = `msg-${Date.now()}`;
                div.id = newId;
                sessionFiles.push({ ...metadata, msgId: newId });
                updateFileSidebar();
            }

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

            // Add Smart Continue button if truncated
            if (data.finish_reason === 'length') {
                const continueBtn = document.createElement('button');
                continueBtn.className = 'continue-btn';
                continueBtn.title = 'Lanjutkan Pesan';
                continueBtn.innerHTML = `Lanjutkan Pesan <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>`;
                continueBtn.addEventListener('click', () => {
                    continueBtn.remove();
                    document.getElementById('user-input').value = 'Lanjut';
                    sendMessage();
                });
                
                // insert below the bubble-text inside the bubble
                bubble.appendChild(continueBtn);
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
            if (!text && !pendingFile) return;

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
            lastUserMessage = text || '(PDF attached)';

            // Build file context if present
            let fileContext = null;
            if (pendingFile) {
                fileContext = {
                    file_id: pendingFile.file_id,
                    filename: pendingFile.filename,
                    text: pendingFile.text,
                    script: pendingFile.script,
                    page_count: pendingFile.page_count,
                    word_count: pendingFile.word_count
                };
            }

            // Add user message bubble immediately
            appendUserMessage(text, fileContext);

            // Show typing indicator immediately — before server responds
            currentAgentContent = '';
            startAgentMessage();
            typingStartTime = Date.now();

            // Send via WebSocket with file context
            ws.send(JSON.stringify({ 
                type: 'message', 
                content: text || '(PDF attached)',
                file_context: fileContext
            }));

            // Clear input and file
            messageInput.value = '';
            messageInput.style.height = 'auto';
            pendingFile = null;
            hideFilePreview();

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

        // SETTINGS NAVIGATION
        function openSettings() {
            window.location.href = `/settings-page?token=${gatewayToken}`;
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
        document.getElementById('sidebar-settings-btn').addEventListener('click', openSettings);

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


        // OCR Modal Logic
        const ocrModal = document.getElementById('ocr-modal');
        const ocrContent = document.getElementById('ocr-content');
        const ocrFilename = document.getElementById('ocr-filename');
        const ocrCloseBtn = document.getElementById('ocr-close-btn');
        const ocrCloseTop = document.getElementById('ocr-close-top');
        const ocrCopyBtn = document.getElementById('ocr-copy-btn');

        function showOCRModal(metadata) {
            if (!metadata || !metadata.text) return;
            
            ocrFilename.textContent = metadata.filename || 'Berkas Tanpa Nama';
            ocrContent.textContent = metadata.text;
            
            // Set direction based on script
            if (metadata.script === 'arabic') {
                ocrContent.setAttribute('dir', 'rtl');
            } else {
                ocrContent.setAttribute('dir', 'ltr');
            }
            
            ocrModal.classList.remove('hidden');
            document.body.style.overflow = 'hidden'; // Prevent scroll
        }

        function hideOCRModal() {
            ocrModal.classList.add('hidden');
            document.body.style.overflow = '';
        }

        ocrCloseBtn.addEventListener('click', hideOCRModal);
        ocrCloseTop.addEventListener('click', hideOCRModal);
        ocrModal.querySelector('.ocr-backdrop').addEventListener('click', hideOCRModal);

        ocrCopyBtn.addEventListener('click', () => {
            const text = ocrContent.textContent;
            copyToClipboard(text, ocrCopyBtn);
            
            const originalText = ocrCopyBtn.textContent;
            ocrCopyBtn.textContent = 'Teks Berhasil Disalin!';
            setTimeout(() => {
                ocrCopyBtn.textContent = originalText;
            }, 2000);
        });

        // Initialize
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

        // Theme Management
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
        }
        
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            const savedTheme = localStorage.getItem('kyuraa_theme') || 'auto';
            if (savedTheme === 'auto') {
                if (e.matches) document.documentElement.setAttribute('data-theme', 'dark');
                else document.documentElement.removeAttribute('data-theme');
            }
        });

        // Expose functions to global scope
        window.deleteSession = deleteSession;
        window.setAppTheme = setAppTheme;
        window.openSettings = openSettings;
        window.showOCRModal = showOCRModal;
        window.createConnectedSession = createConnectedSession;
        window.deleteFilePermanently = deleteFilePermanently;
        window.jumpToMessage = jumpToMessage;

        // ============================================
        // SIDEBAR RIGHT (FILE LIST)
        // ============================================
        function updateFileSidebar() {
            if (sessionFiles.length === 0) {
                sessionFilesList.innerHTML = `
                    <div class="empty-sidebar-state">
                        <p>Belum ada berkas terunggah di sesi ini.</p>
                    </div>
                `;
                return;
            }

            sessionFilesList.innerHTML = sessionFiles.map(file => `
                <div class="sidebar-file-item" id="sidebar-file-${file.file_id}">
                    <div class="sidebar-file-main">
                        <div class="sidebar-file-icon">PDF</div>
                        <div class="sidebar-file-info">
                            <div class="sidebar-file-name" title="${escapeHtml(file.filename)}">${escapeHtml(file.filename)}</div>
                            <div class="sidebar-file-meta">${file.page_count || '?'} hlm · ${file.script || 'text'}</div>
                        </div>
                    </div>
                    <div class="sidebar-file-actions">
                        <button class="btn-sidebar-jump" onclick="jumpToMessage('${file.msgId}')">Lihat</button>
                        <button class="btn-sidebar-delete" onclick="deleteFilePermanently('${file.file_id}')">Hapus</button>
                    </div>
                </div>
            `).join('');
        }

        function toggleSidebarRight() {
            sidebarRight.classList.toggle('collapsed');
        }

        function jumpToMessage(msgId) {
            const el = document.getElementById(msgId);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                const bubble = el.querySelector('.bubble');
                if (bubble) {
                    bubble.classList.add('highlight-pulse');
                    setTimeout(() => bubble.classList.remove('highlight-pulse'), 2000);
                }
            }
        }

        async function deleteFilePermanently(fileId) {
            showConfirm('Hapus berkas ini secara permanen dari server dan riwayat?', async () => {
                try {
                    const res = await fetch(`/upload/${fileId}`, { 
                        method: 'DELETE',
                        headers: { 'X-API-Key': gatewayToken }
                    });
                    
                    if (res.ok) {
                        showToast('Berkas dihapus permanen', 'success');
                        // Update UI
                        sessionFiles = sessionFiles.filter(f => f.file_id !== fileId);
                        updateFileSidebar();
                        // Optional: reload current session messages to hide the file cards in chat
                        selectSession(currentSessionId);
                    }
                } catch (e) {
                    showToast('Gagal menghapus berkas', 'error');
                }
            });
        }

        sidebarRightToggle.addEventListener('click', toggleSidebarRight);
        sidebarRightClose.addEventListener('click', () => sidebarRight.classList.add('collapsed'));
