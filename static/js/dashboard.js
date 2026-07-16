function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ── Global state ──
let ws = null;
const connectedDevices = new Set(); // device UIDs with active WS connection

// ── Helpers ──
function getCard(uid) {
    return document.querySelector(`[data-device-uid="${uid}"]`);
}

function setCardName(card, name) {
    const el = card.querySelector('.device-name');
    if (el) el.textContent = name;
    card.dataset.deviceName = name;
}

function updateDeviceStatus(card) {
    const isActive = card.dataset.deviceActive === 'true';
    const wsConnected = connectedDevices.has(card.dataset.deviceUid);
    const online = isActive && wsConnected;
    const dot = card.querySelector('.device-status .size-2\\.5');
    const label = card.querySelector('.device-status .text-sm.font-medium');
    if (dot) {
        dot.className = `size-2.5 rounded-full ${online ? 'bg-green-500' : 'bg-red-500'}`;
    }
    if (label) {
        label.className = `text-sm font-medium ${online ? 'text-green-400' : 'text-red-400'}`;
        label.textContent = online ? 'Online' : 'Offline';
    }
}

function updateAllDeviceStatuses() {
    document.querySelectorAll('[data-device-uid]').forEach(card => updateDeviceStatus(card));
}

// ── Device card factory (matches server-rendered structure) ──
function createDeviceCard(device) {
    const icon = device.type === 'embedded' ? 'memory' : device.type;

    const div = document.createElement('div');
    div.className = 'flex flex-col rounded-lg bg-[#182C2C] p-6 shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-cyan-500/20';
    div.dataset.deviceUid = device.uid;
    div.dataset.deviceActive = device.is_active ? 'true' : 'false';
    div.dataset.deviceName = device.name || 'Unknown';
    div.innerHTML = `
        <div class="relative flex items-center justify-between">
            <div class="flex items-center gap-3">
                <span class="material-symbols-outlined text-[#3df5f5]">${icon}</span>
                <p class="text-lg font-bold device-name">${device.name || 'Unknown'}</p>
            </div>
            <button class="device-menu-btn text-gray-400 hover:text-white focus:outline-none rounded-full p-1">
                <span class="material-symbols-outlined">more_vert</span>
            </button>
            <div class="device-menu hidden origin-top-right absolute right-0 top-full mt-2 w-40 rounded-md bg-[#2A3C3C] p-2 shadow-lg ring-1 ring-black ring-opacity-5 z-50">
                <button class="menu-item block w-full text-left px-4 py-2 text-sm text-green-300 hover:bg-green-800/20 rounded-md" data-action="rename">Rename</button>
                <button class="menu-item block w-full text-left px-4 py-2 text-sm text-yellow-300 hover:bg-yellow-800/20 rounded-md" data-action="refresh">Refresh</button>
                <button class="menu-item block w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-800/20 rounded-md" data-action="delete">Delete</button>
            </div>
        </div>
        <div class="mt-3 flex-1">
            <p class="text-sm text-gray-400">${device.type || 'unknown'}</p>
            <div class="flex items-center justify-between">
                <p class="text-sm text-gray-400">IP : ${device.ip || 'N/A'}</p>
                <div class="flex items-center gap-2 device-status">
                    <div class="size-2.5 rounded-full bg-red-500"></div>
                    <p class="text-sm font-medium text-red-400">Offline</p>
                </div>
            </div>
        </div>
    `;
    return div;
}

// ── Menu toggle ──
function closeAllMenus() {
    document.querySelectorAll('.device-menu').forEach(m => m.classList.add('hidden'));
}

function toggleMenu(btn) {
    const menu = btn.parentElement.querySelector('.device-menu');
    if (!menu) return;
    const isOpen = !menu.classList.contains('hidden');
    closeAllMenus();
    if (!isOpen) menu.classList.remove('hidden');
}

// ── Inline rename ──
function startRename(card) {
    const nameEl = card.querySelector('.device-name');
    const currentName = card.dataset.deviceName || '';

    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentName;
    input.className = 'bg-[#2A3C3C] text-white text-lg font-bold rounded px-2 py-1 w-full outline-none border border-[#3df5f5]';
    input.dataset.renameInput = '';

    nameEl.replaceWith(input);
    input.focus();
    input.select();

    function cancelRename() {
        const p = document.createElement('p');
        p.className = 'text-lg font-bold device-name';
        p.textContent = currentName;
        input.replaceWith(p);
    }

    function saveRename() {
        const newName = input.value.trim();
        if (!newName || newName === currentName) {
            cancelRename();
            return;
        }
        const uid = card.dataset.deviceUid;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({action: 'rename_device', uid, name: newName}));
        }
        setCardName(card, newName);
        const p = document.createElement('p');
        p.className = 'text-lg font-bold device-name';
        p.textContent = newName;
        input.replaceWith(p);
    }

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); saveRename(); }
        if (e.key === 'Escape') { e.preventDefault(); cancelRename(); }
    });
    input.addEventListener('blur', saveRename);
}

// ── WebSocket ──
const wsIndicator = document.getElementById('ws-status');
function setWSStatus(connected) {
    if (wsIndicator) {
        wsIndicator.className = `size-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`;
        wsIndicator.title = connected ? 'WS Connected' : 'WS Disconnected';
    }
}
function toWsUrl(str) {
    if (/^https?:\/\//.test(str))
        return str.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
    if (/^wss?:\/\//.test(str))
        return str;
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${location.host}${str}`;
}
function connectWS() {
    const token = getCookie('authToken');
    if (!token) {
        setWSStatus(false);
        setTimeout(connectWS, 3000);
        return;
    }

    const wsUrl = toWsUrl(USER.ws_url);

    ws = new WebSocket(`${wsUrl}?token=${token}`);

    ws.onopen = () => {
        console.log('WS connected');
        setWSStatus(true);
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            console.log('WS received:', msg);
            if (msg.type !== 'event') return;

            switch (msg.event) {
                case 'device_added':
                    handleDeviceAdded(msg.data);
                    break;
                case 'device_status_change':
                    handleDeviceStatusChange(msg.data);
                    break;
                case 'device_removed':
                    handleDeviceRemoved(msg.data);
                    break;
                case 'device_online':
                    handleDeviceOnline(msg.data);
                    break;
                case 'device_offline':
                    handleDeviceOffline(msg.data);
                    break;
                case 'device_connectivity_snapshot':
                    handleConnectivitySnapshot(msg.data);
                    break;
                case 'device_renamed':
                    handleDeviceRenamed(msg.data);
                    break;
                case 'device_refresh':
                    handleDeviceRefresh(msg.data);
                    break;
            }
        } catch (e) {
            console.error('WS message error:', e);
        }
    };

    ws.onerror = () => {
        console.error('WS error');
        ws?.close();
    };

    ws.onclose = () => {
        console.log('WS disconnected');
        setWSStatus(false);
        setTimeout(connectWS, 3000);
    };
}

// ── WS Event Handlers ──

function handleDeviceAdded(data) {
    const grid = window.devicesGrid;
    if (!grid) return;
    const placeholder = grid.querySelector('p');
    if (placeholder && !grid.querySelector('[data-device-uid]')) {
        grid.innerHTML = '';
    }
    const card = createDeviceCard(data);
    grid.appendChild(card);
}

function handleDeviceStatusChange(data) {
    const card = getCard(data.uid);
    if (!card) return;
    card.dataset.deviceActive = data.is_active ? 'true' : 'false';
    updateDeviceStatus(card);
}

function handleDeviceRemoved(data) {
    const card = getCard(data.uid);
    if (card) card.remove();
}

function handleDeviceOnline(data) {
    connectedDevices.add(data.uid);
    const card = getCard(data.uid);
    if (card) updateDeviceStatus(card);
}

function handleDeviceOffline(data) {
    connectedDevices.delete(data.uid);
    const card = getCard(data.uid);
    if (card) updateDeviceStatus(card);
}

function handleConnectivitySnapshot(data) {
    connectedDevices.clear();
    if (Array.isArray(data.connected_uids)) {
        data.connected_uids.forEach(uid => connectedDevices.add(uid));
    }
    updateAllDeviceStatuses();
}

function handleDeviceRenamed(data) {
    const card = getCard(data.uid);
    if (card) setCardName(card, data.name);
}

function handleDeviceRefresh(data) {
    if (Array.isArray(data.devices)) {
        data.devices.forEach(d => {
            const card = getCard(d.uid);
            if (card) {
                card.dataset.deviceActive = d.is_active ? 'true' : 'false';
                setCardName(card, d.name);
                updateDeviceStatus(card);
            }
        });
    }
}

// ── DOM Event Listeners (delegated) ──
function handleDeviceMenuClick(e) {
    const btn = e.target.closest('.device-menu-btn');
    if (btn) { e.stopPropagation(); toggleMenu(btn); return; }

    const item = e.target.closest('.menu-item');
    if (!item) return;
    e.preventDefault();

    const card = item.closest('[data-device-uid]');
    if (!card) return;
    const uid = card.dataset.deviceUid;
    const action = item.dataset.action;
    closeAllMenus();

    switch (action) {
        case 'rename':
            startRename(card);
            break;
        case 'refresh':
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({action: 'refresh_devices'}));
            }
            break;
        case 'delete':
            if (confirm('Delete this device?\nThis cannot be undone.')) {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({action: 'delete_device', uid}));
                }
            }
            break;
    }
}

// Close menus on outside click
document.addEventListener('click', (e) => {
    if (!e.target.closest('.device-menu-btn') && !e.target.closest('.device-menu')) {
        closeAllMenus();
    }
});

// ── Modal Functions ──
document.addEventListener('DOMContentLoaded', () => {
    const openModalBtn = document.getElementById('add-device-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modal = document.getElementById('device-modal');
    const modalContent = document.getElementById('modal-content');
    const radioButtons = document.querySelectorAll('input[name="device_type"]');
    const addButton = document.getElementById('add-device-final-btn');
    const labels = document.querySelectorAll('.device-option-label');
    const devicesGridGlobal = document.querySelector('.grid.grid-cols-1');

    // QR Modal elements
    const qrModal = document.getElementById('qr-modal');
    const qrModalContent = document.getElementById('qr-modal-content');
    const closeQrModalBtn = document.getElementById('close-qr-modal-btn');
    const closeQrModalFinalBtn = document.getElementById('close-qr-modal-final-btn');
    const qrCodeImage = document.getElementById('qr-code-image');

    // Expose devicesGrid globally for helpers
    window.devicesGrid = devicesGridGlobal;

    // ── Menu delegation (on document so it always works) ──
    if (!window._menuHandlerAttached) {
        document.addEventListener('click', handleDeviceMenuClick);
        window._menuHandlerAttached = true;
    }

    function openModal() {
        modal.classList.remove('hidden');
        setTimeout(() => {
            modalContent.classList.remove('scale-95', 'opacity-0');
        }, 10);
    }

    function closeModal() {
        modalContent.classList.add('scale-95', 'opacity-0');
        setTimeout(() => {
            modal.classList.add('hidden');
            radioButtons.forEach(radio => radio.checked = false);
            labels.forEach(label => label.classList.remove('selected'));
            addButton.disabled = true;
        }, 300);
    }

    function openQrModal(qrImagePath) {
        qrCodeImage.src = qrImagePath;
        qrModal.classList.remove('hidden');
        setTimeout(() => {
            qrModalContent.classList.remove('scale-95', 'opacity-0');
        }, 10);
    }

    function closeQrModal() {
        qrModalContent.classList.add('scale-95', 'opacity-0');
        setTimeout(() => {
            qrModal.classList.add('hidden');
        }, 300);
    }

    async function submitDevice() {
        const selectedDevice = document.querySelector('input[name="device_type"]:checked');
        if (!selectedDevice) return;

        addButton.disabled = true;
        addButton.textContent = 'Adding...';

        try {
            const token = getCookie('authToken');
            const response = await fetch(API.route, {
                method: 'POST',
                headers: {
                  "Content-Type": "application/json",
                  'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ device_type: selectedDevice.value }),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                alert('Error: ' + (errData.message || errData.error || 'Failed to add device'));
                return;
            }

            closeModal();

            if (selectedDevice.value === 'laptop') {
                // Desktop: download encrypted config file
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const disposition = response.headers.get('Content-Disposition') || '';
                const match = disposition.match(/filename="?([^"]+)"?/);
                const filename = match ? match[1] : 'nix-config.nixconfig';
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
            } else {
                // Mobile/Embedded: show QR code
                const data = await response.json();
                openQrModal(data.qr_path);
            }
        } catch (error) {
            alert('Error: ' + error.message);
        } finally {
            addButton.disabled = false;
            addButton.textContent = 'Add Device';
        }
    }

    // ── Event listeners ──
    openModalBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);
    addButton.addEventListener('click', submitDevice);
    closeQrModalBtn.addEventListener('click', closeQrModal);
    closeQrModalFinalBtn.addEventListener('click', closeQrModal);

    modal.addEventListener('click', (event) => {
        if (event.target === modal) closeModal();
    });

    qrModal.addEventListener('click', (event) => {
        if (event.target === qrModal) closeQrModal();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (!modal.classList.contains('hidden')) {
                closeModal();
            } else if (!qrModal.classList.contains('hidden')) {
                closeQrModal();
            }
        }
    });

    radioButtons.forEach(radio => {
        radio.addEventListener('change', () => {
            addButton.disabled = false;
            labels.forEach(label => label.classList.remove('selected'));
            if (radio.checked) {
                radio.parentElement.classList.add('selected');
            }
        });
    });

    // ── Init WS connection ──
    connectWS();
});
