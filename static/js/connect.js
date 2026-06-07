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

const output = document.getElementById('terminal-output');
const input = document.getElementById('cmd-input');

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
                            printOutput(`[${data.from}] ${data.message}`);
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
                printOutput('  /help             - Show this message');
                printOutput('  /clear            - Clear terminal');
                printOutput('  /status           - Show connection status');
                printOutput('  /devices          - List connected devices');
                printOutput('  /echo <text>      - Echo text');
                printOutput('  /ws <message>     - Send raw WS message');
                break;

            case 'clear':
                output.innerHTML = '';
                break;

            case 'status':
                printInfo(`WS Status: ${ws && ws.readyState === WebSocket.OPEN ? 'Connected' : 'Disconnected'}`);
                break;

            case 'devices':
                printInfo('Device listing not implemented in CMD interface.');
                printOutput('Use the Dashboard to manage devices.');
                break;

            case 'echo':
                printOutput(parts.slice(1).join(' ') || '');
                break;

            case 'ws':
                const payload = parts.slice(1).join(' ');
                if (payload && ws && ws.readyState === WebSocket.OPEN) {
                    try {
                        const obj = JSON.parse(payload);
                        ws.send(JSON.stringify(obj));
                        printSuccess('Sent: ' + payload);
                    } catch {
                        printError('Invalid JSON. Use valid JSON format.');
                    }
                } else if (!payload) {
                    printError('Usage: /ws <json>');
                } else {
                    printError('Not connected.');
                }
                break;

            default:
                printError(`Unknown command: /${command}. Type '/help' for available commands.`);
        }
    }

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
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
        }
    });

    // Live prefix warning on keystroke
    const prefixWarning = document.getElementById('cmd-prefix-warning');
    input.addEventListener('input', () => {
        const val = input.value;
        if (val.length > 0 && !val.startsWith('/')) {
            prefixWarning.classList.remove('hidden');
        } else {
            prefixWarning.classList.add('hidden');
        }
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
