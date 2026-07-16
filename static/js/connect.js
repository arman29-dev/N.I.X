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

function toWsUrl(str) {
    if (/^https?:\/\//.test(str))
        return str.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
    if (/^wss?:\/\//.test(str))
        return str;
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${location.host}${str}`;
}

function showNotification(message, isError) {
    const notif = document.getElementById('cmd-notification');
    const msg = document.getElementById('cmd-notification-message');
    if (!notif || !msg) return;
    msg.textContent = message;
    notif.className = `fixed top-4 right-4 z-50 px-4 py-2 rounded shadow-lg text-white ${isError ? 'bg-red-500' : 'bg-green-500'}`;
    notif.classList.remove('hidden');
    setTimeout(() => notif.classList.add('hidden'), 4000);
}

let _hasInteracted = false;

const COMMANDS = [
  { cmd: 'help',    desc: 'Show available commands' },
  { cmd: 'clear',   desc: 'Clear terminal' },
  { cmd: 'status',  desc: 'Show connection status' },
  { cmd: 'devices', desc: 'List connected devices' },
  { cmd: 'echo',    desc: 'Echo text' },
  { cmd: 'ws',      desc: 'Send message to a device' },
];

let cachedDevices = [];
let _wsCommandStage = 'idle'; // 'idle' | 'device_selected'

const output = document.getElementById('terminal-output');
const input = document.getElementById('cmd-input');
const suggestionsEl = document.getElementById('cmd-suggestions');

function printLine(text, className) {
    const line = document.createElement('div');
    line.textContent = text;
    if (className) line.className = className;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
}

function printError(text) {
    printLine(text, 'text-red-400');
}

function printSuccess(text) {
    printLine(text, 'text-green-400');
}

function printInfo(text) {
    printLine(text, 'text-[#3df5f5]');
}

function printOutput(text) {
    printLine(text, 'text-gray-200');
}

document.addEventListener('DOMContentLoaded', () => {
    let ws = null;
    const wsIndicator = document.getElementById('ws-status');

    function setWSStatus(connected) {
        if (wsIndicator) {
            wsIndicator.className = `size-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`;
            wsIndicator.title = connected ? 'WS Connected' : 'WS Disconnected';
        }
    }

    function connectWS() {
        const token = getCookie('authToken');
        if (!token) {
            setWSStatus(false);
            printInfo('Waiting for auth token...');
            setTimeout(connectWS, 3000);
            return;
        }

        const wsUrl = toWsUrl(USER.ws_url);
        ws = new WebSocket(`${wsUrl}?token=${token}`);

        ws.onopen = () => {
            setWSStatus(true);
            printSuccess('Connected to N.I.X');
            ws.send(JSON.stringify({action: 'get_devices'}));
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'event') {
                    const data = msg.data || {};
                    switch (msg.event) {
                        case 'device_status_change':
                            printInfo(`[${data.uid}] status: ${data.is_active ? 'Online' : 'Offline'}`);
                            break;
                        case 'device_added':
                            printInfo(`[${data.uid}] device added: ${data.name} (${data.type})`);
                            break;
                        case 'device_removed':
                            printInfo(`[${data.uid}] device removed`);
                            break;
                        case '2fa_toggled':
                            printInfo(`2FA ${data.is_enabled ? 'enabled' : 'disabled'}`);
                            break;
                        case 'device_message':
                            const from = data.from_device || 'device';
                            const target = data.target_device;
                            if (target) {
                                printOutput(`[→ ${target}] ${data.message}`);
                            } else {
                                printOutput(`[${from}] ${data.message}`);
                            }
                            break;
                        case 'device_list':
                            cachedDevices = (data.devices || []).filter(d => d.is_online);
                            printInfo(`Loaded ${cachedDevices.length} online device(s)`);
                            break;
                        case 'device_connectivity_snapshot':
                            break;
                        default:
                            printInfo(`Event: ${msg.event}`);
                    }
                }
            } catch (e) {
                printError('Parse error: ' + e.message);
            }
        };

        ws.onerror = () => {
            printError('Connection error');
            ws?.close();
        };

        ws.onclose = () => {
            setWSStatus(false);
            printInfo('Disconnected. Reconnecting...');
            setTimeout(connectWS, 3000);
        };
    }

    function processCommand(raw) {
        const trimmed = raw.trim();
        if (!trimmed.startsWith('/')) {
            printError("Use '/' for commands. Type '/help' for available commands.");
            return;
        }
        const cmd = trimmed.slice(1).trim();
        const parts = cmd.split(/\s+/);
        const command = parts[0].toLowerCase();

        switch (command) {
            case 'help':
                printInfo('Available commands:');
                printOutput('  /help                   - Show this message');
                printOutput('  /clear                  - Clear terminal');
                printOutput('  /status                 - Show connection status');
                printOutput('  /devices                - List connected devices');
                printOutput('  /echo <text>            - Echo text');
                printOutput('  /ws <device> <message>  - Send message to a device');
                break;

            case 'clear':
                output.innerHTML = '';
                break;

            case 'status':
                printInfo(`WS Status: ${ws && ws.readyState === WebSocket.OPEN ? 'Connected' : 'Disconnected'}`);
                break;

            case 'devices':
                if (cachedDevices.length === 0) {
                    printInfo('No online devices. Use /ws to send messages.');
                } else {
                    printInfo('Online devices:');
                    cachedDevices.forEach(d => {
                        printOutput(`  ${d.name || 'Unknown'} (${d.uid}) — ${d.type}`);
                    });
                }
                break;

            case 'echo':
                printOutput(parts.slice(1).join(' ') || '');
                break;

            case 'ws':
                if (_wsCommandStage === 'device_selected') {
                    _wsCommandStage = 'idle';
                    const message = parts.slice(1).join(' ');
                    if (!message) {
                        printError('Usage: /ws <device> <message>');
                        break;
                    }
                    const targetUid = command;
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({action: 'send_direct_message', target_device: targetUid, message}));
                        const device = cachedDevices.find(d => d.uid === targetUid);
                        const name = device ? device.name : targetUid;
                        printSuccess(`[→ ${name}] ${message}`);
                    } else {
                        printError('Not connected.');
                    }
                } else {
                    if (cachedDevices.length === 0) {
                        printError('No online devices found. Wait for devices to connect.');
                        break;
                    }
                    const deviceQuery = parts.slice(1).join(' ').toLowerCase();
                    const matched = cachedDevices.filter(d => {
                        const name = (d.name || '').toLowerCase();
                        const uid = (d.uid || '').toLowerCase();
                        return !deviceQuery || name.includes(deviceQuery) || uid.includes(deviceQuery);
                    });
                    if (matched.length === 1 && deviceQuery) {
                        _wsCommandStage = 'device_selected';
                        input.value = `/ws ${matched[0].uid} `;
                        printInfo(`Target: ${matched[0].name || matched[0].uid} — type your message and press Enter`);
                    } else {
                        printInfo('Select a device:');
                        matched.forEach(d => {
                            printOutput(`  ${d.name || 'Unknown'} (${d.uid})`);
                        });
                        printInfo('Type /ws <device_name> to select, then your message.');
                    }
                }
                break;

            default:
                printError(`Unknown command: /${command}. Type '/help' for available commands.`);
        }
    }

    function submitCommand() {
        const cmd = input.value;
        input.value = '';
        if (cmd.trim()) {
            if (!_hasInteracted) {
                output.innerHTML = '';
                _hasInteracted = true;
            }
            printOutput(`$ ${cmd}`);
            processCommand(cmd);
            const cleaned = cmd.trim().toLowerCase();
            if (cleaned !== '/clear') {
                const sep = document.createElement('div');
                sep.className = 'h-px bg-[#2A3C3C] my-4';
                output.appendChild(sep);
                output.scrollTop = output.scrollHeight;
            }
        }
        if (!cmd.trim().startsWith('/ws')) {
            _wsCommandStage = 'idle';
        }
    }

    // ── Command Suggestions ──
    const prefixWarning = document.getElementById('cmd-prefix-warning');
    let _selectedSuggestionIndex = -1;

    function renderSuggestions(filter) {
        const filtered = filter
            ? COMMANDS.filter(c => c.cmd.startsWith(filter.toLowerCase()))
            : COMMANDS;
        if (filtered.length === 0) {
            suggestionsEl.classList.add('hidden');
            suggestionsEl.innerHTML = '';
            _selectedSuggestionIndex = -1;
            return;
        }
        suggestionsEl.innerHTML = '';
        suggestionsEl.classList.remove('hidden');
        filtered.forEach((c, i) => {
            const row = document.createElement('div');
            row.className = 'flex items-center gap-2 px-3 py-2 cursor-pointer text-sm font-mono border-b border-[#2A3C3C] last:border-b-0 hover:bg-[#182C2C] transition-colors';
            row.dataset.index = i;
            const cmdSpan = document.createElement('span');
            cmdSpan.className = 'text-[#3df5f5] font-medium';
            cmdSpan.textContent = '/' + c.cmd;
            const descSpan = document.createElement('span');
            descSpan.className = 'text-gray-400 text-xs';
            descSpan.textContent = c.desc;
            row.appendChild(cmdSpan);
            row.appendChild(descSpan);
            row.addEventListener('click', () => {
                insertCommand(c.cmd);
            });
            row.addEventListener('mouseenter', () => {
                if (_selectedSuggestionIndex >= 0 && _selectedSuggestionIndex < filtered.length) {
                    suggestionsEl.children[_selectedSuggestionIndex]?.classList.remove('bg-[#182C2C]');
                }
                _selectedSuggestionIndex = i;
                row.classList.add('bg-[#182C2C]');
            });
            suggestionsEl.appendChild(row);
        });
        _selectedSuggestionIndex = 0;
        suggestionsEl.children[0]?.classList.add('bg-[#182C2C]');
    }

    function insertCommand(cmd) {
        input.value = '/' + cmd;
        suggestionsEl.classList.add('hidden');
        suggestionsEl.innerHTML = '';
        _selectedSuggestionIndex = -1;
        input.focus();
    }

    function dismissSuggestions() {
        suggestionsEl.classList.add('hidden');
        suggestionsEl.innerHTML = '';
        _selectedSuggestionIndex = -1;
    }

    input.addEventListener('input', () => {
        const val = input.value;
        // prefix warning
        if (val.length > 0 && !val.startsWith('/')) {
            prefixWarning.classList.remove('hidden');
        } else {
            prefixWarning.classList.add('hidden');
        }
        // suggestions
        if (val.startsWith('/')) {
            const partial = val.slice(1);
            renderSuggestions(partial);
        } else {
            dismissSuggestions();
        }
    });

    input.addEventListener('keydown', (e) => {
        const showingSuggestions = !suggestionsEl.classList.contains('hidden') && suggestionsEl.children.length > 0;

        if (e.key === 'Escape') {
            if (showingSuggestions) dismissSuggestions();
            return;
        }

        if (showingSuggestions) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                const items = suggestionsEl.children;
                items[_selectedSuggestionIndex]?.classList.remove('bg-[#182C2C]');
                _selectedSuggestionIndex = Math.min(_selectedSuggestionIndex + 1, items.length - 1);
                items[_selectedSuggestionIndex]?.classList.add('bg-[#182C2C]');
                items[_selectedSuggestionIndex]?.scrollIntoView({ block: 'nearest' });
                return;
            }
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                const items = suggestionsEl.children;
                items[_selectedSuggestionIndex]?.classList.remove('bg-[#182C2C]');
                _selectedSuggestionIndex = Math.max(_selectedSuggestionIndex - 1, 0);
                items[_selectedSuggestionIndex]?.classList.add('bg-[#182C2C]');
                items[_selectedSuggestionIndex]?.scrollIntoView({ block: 'nearest' });
                return;
            }
            if (e.key === 'Enter' || e.key === 'Tab') {
                e.preventDefault();
                const items = suggestionsEl.children;
                if (_selectedSuggestionIndex >= 0 && _selectedSuggestionIndex < items.length) {
                    const cmd = COMMANDS.filter(c => c.cmd.startsWith(input.value.slice(1).toLowerCase()))[_selectedSuggestionIndex]?.cmd;
                    if (cmd) insertCommand(cmd);
                }
                return;
            }
        }

        if (e.key === 'Enter') {
            submitCommand();
        }
    });

    input.addEventListener('blur', () => {
        setTimeout(dismissSuggestions, 200);
    });

    // ── New Command Request Modal ──
    const requestBtn = document.getElementById('request-cmd-btn');
    const cmdModal = document.getElementById('cmd-request-modal');
    const cancelBtn = document.getElementById('cmd-request-cancel');
    const submitBtn = document.getElementById('cmd-request-submit');
    const nameInput = document.getElementById('cmd-name-input');
    const descInput = document.getElementById('cmd-desc-input');

    function openCmdModal() {
        cmdModal.classList.remove('hidden');
        cmdModal.classList.add('flex');
        nameInput.focus();
    }

    function closeCmdModal() {
        cmdModal.classList.add('hidden');
        cmdModal.classList.remove('flex');
        nameInput.value = '';
        descInput.value = '';
    }

    if (requestBtn && cmdModal) {
        requestBtn.addEventListener('click', openCmdModal);
        cancelBtn.addEventListener('click', closeCmdModal);
        submitBtn.addEventListener('click', async () => {
            let name = nameInput.value.trim();
            const desc = descInput.value.trim();
            if (!name) { nameInput.focus(); return; }
            if (!desc) { descInput.focus(); return; }
            name = name.startsWith('/') ? name.slice(1) : name;
            const token = getCookie('authToken');
            if (!token) {
                showNotification('Not authenticated. Please log in.', true);
                return;
            }
            try {
                const res = await fetch('/api/v1/cmd-requests', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                    body: JSON.stringify({ name, description: desc }),
                });
                const data = await res.json();
                if (data.success) {
                    showNotification(`Command request submitted: /${name}`, false);
                    closeCmdModal();
                } else {
                    showNotification(data.message || 'Failed to submit request', true);
                }
            } catch (e) {
                showNotification('Network error. Please try again.', true);
            }
        });
        cmdModal.addEventListener('click', (e) => {
            if (e.target === cmdModal) closeCmdModal();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !cmdModal.classList.contains('hidden')) closeCmdModal();
        });
    }

    printInfo('Welcome to N.I.X CMD Line.');
    printInfo("Type '/help' for available commands.");
    connectWS();
});
