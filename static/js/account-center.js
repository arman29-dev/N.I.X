let currentAction = null;
let ws = null;

const { delDeviceUrl, delAccountUrl, toggle2FAUrl, logoutUrl, emailUrl } = API_DATA;

const toggle2FABtn = document.getElementById('toggle2FABtn');
const manage2FAModal = document.getElementById('manage-2fa-modal');
const cnf2FAdisableBtn = document.getElementById('confirm-2fa-disable')
const cncl2FAdisableBtn = document.getElementById('cancel-2fa-disable')

cnf2FAdisableBtn.addEventListener("click", () => {
  manage2FAModal.classList.add('hidden');
  cnf2FAdisableBtn.textContent = 'Do It Anyway';
  // Open 2FA code input for verification before disabling
  const modal = document.getElementById("twofa-modal");
  if (modal) {
    currentAction = "2fa_toggle";
    modal.classList.remove("hidden");
    const inputs = modal.querySelectorAll("input");
    if (inputs.length > 0) inputs[0].focus();
  }
});

cncl2FAdisableBtn.addEventListener("click", () => {
  manage2FAModal.classList.add('hidden');
  toggle2FABtn.disabled = false;
  toggle2FABtn.classList.remove('cursor-not-allowed');
})

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

function setWSStatus(connected) {
    const el = document.getElementById('ws-status');
    if (el) {
        el.className = `size-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`;
        el.title = connected ? 'WS Connected' : 'WS Disconnected';
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

            if (msg.event === '2fa_toggled') {
                const isEnabled = msg.data.is_enabled;
                toggle2FABtn.disabled = false;
                toggle2FABtn.classList.remove('cursor-not-allowed');
                manage2FAModal.classList.add('hidden');
                cnf2FAdisableBtn.textContent = 'Do It Anyway';

                const statusSpan = document.querySelector('.text-sm.font-medium');
                if (statusSpan) {
                    if (isEnabled) {
                        statusSpan.className = 'text-sm font-medium text-green-400 bg-green-900/50 px-3 py-1 rounded-full';
                        statusSpan.textContent = 'Enabled';
                        toggle2FABtn.textContent = 'Disable';
                        toggle2FABtn.className = 'flex items-center justify-center rounded-md h-10 px-4 bg-[#224949] text-white hover:bg-red-500 transition-colors text-sm font-bold';
                        toggle2FABtn.setAttribute('onclick', 'toggle2FA(true)');
                    } else {
                        statusSpan.className = 'text-sm font-medium text-red-400 bg-red-900/50 px-3 py-1 rounded-full';
                        statusSpan.textContent = 'Disabled';
                        toggle2FABtn.textContent = 'Enable';
                        toggle2FABtn.className = 'flex items-center justify-center rounded-md h-10 px-4 bg-[#224949] text-white hover:bg-green-500 transition-colors text-sm font-bold';
                        toggle2FABtn.setAttribute('onclick', 'toggle2FA(false)');
                    }
                }
            }
        } catch (e) {
            console.error('WS error:', e);
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

function sendToggle2FA(code) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'toggle_2fa', code: code }));
        return;
    }
    // WS not available — fall back to HTTP
    const token = getCookie('authToken');
    const params = code ? `?code=${encodeURIComponent(code)}` : '';
    fetch(toggle2FAUrl + params, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` },
    }).then(res => {
        if (res.ok) { location.reload(); return; }
        res.json().then(d => alert(d.message || 'Action failed'));
    }).catch(() => alert('Network error. Please try again.'))
    .finally(() => {
        toggle2FABtn.disabled = false;
        toggle2FABtn.classList.remove('cursor-not-allowed');
    });
}

function getToken() {
  return getCookie('authToken');
}

function updateEmailDisplay(email) {
  const el = document.getElementById('notification-email-display');
  if (el) el.textContent = email || 'Not set';
}

document.addEventListener("DOMContentLoaded", () => {

  const modal = document.getElementById("twofa-modal");
  const deleteDevicesBtn = document.getElementById("delete-devices-btn");
  const deleteAccountBtn = document.getElementById("delete-account-btn");
  const submitBtn = document.getElementById("submit-2fa");
  const cancelBtn = document.getElementById("cancel-2fa");
  const inputs = modal?.querySelectorAll("input") || [];

  if (cancelBtn && inputs.length === 0) {
    cancelBtn.addEventListener("click", () => {
      modal.classList.add("hidden");
    });
  }

  deleteDevicesBtn.addEventListener("click", () => openModal("devices"));
  deleteAccountBtn.addEventListener("click", () => openModal("account"));
  submitBtn.addEventListener("click", handleSubmit);
  cancelBtn.addEventListener("click", closeModal);

  // ── Email Notifications modal ──
  const emailModal = document.getElementById('email-modal');
  const manageEmailBtn = document.getElementById('manage-email-btn');
  const cancelEmailBtn = document.getElementById('cancel-email');
  const saveEmailBtn = document.getElementById('save-email');
  const emailInput = document.getElementById('email-input');

  manageEmailBtn.addEventListener('click', () => emailModal.classList.remove('hidden'));
  cancelEmailBtn.addEventListener('click', () => emailModal.classList.add('hidden'));
  saveEmailBtn.addEventListener('click', async () => {
    const email = emailInput.value.trim();
    try {
      const res = await fetch(emailUrl, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
        body: JSON.stringify({ notification_email: email }),
      });
      const data = await res.json();
      if (res.ok) {
        updateEmailDisplay(data.notification_email);
        showNotification('Notification email updated', 'success');
      } else {
        showNotification(data.message || 'Failed to update email');
      }
    } catch (e) {
      showNotification('Network error');
    }
    emailModal.classList.add('hidden');
  });

  inputs.forEach((input, index) => {
    input.addEventListener("input", (e) => {
      if (e.target.value && index < inputs.length - 1) {
        inputs[index + 1].focus();
      }
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !e.target.value && index > 0) {
        inputs[index - 1].focus();
      }
    });
  });

  function openModal(action) {
    currentAction = action;
    modal.classList.remove("hidden");
    inputs[0].focus();
  }

  function closeModal() {
    modal.classList.add("hidden");
    inputs.forEach((input) => (input.value = ""));
    currentAction = null;
  }

  async function handleSubmit() {
    const code = Array.from(inputs)
      .map((input) => input.value)
      .join("");

    if (code.length !== 6) {
      showNotification("Please enter all 6 digits");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.classList.add('cursor-not-allowed')
    submitBtn.textContent = 'Processing...';

    if (currentAction === "2fa_toggle") {
      closeModal();
      sendToggle2FA(code);
      return;
    }

    const endpoint = currentAction === "devices" ? delDeviceUrl : delAccountUrl;

    try {
      const token = getCookie('authToken');
      const response = await fetch(endpoint, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ twofa_code: code }),
      });

      const data = await response.json();

      if (response.ok) {
        const action = currentAction;
        closeModal();
        if (action === "devices") {
          showNotification("All devices deleted successfully", "success");
        } else {
          showNotification(
            "Your account has been deleted successfully",
            "success",
          );
          setTimeout(() => (window.location.href = logoutUrl), 3000);
        }
      } else {
        showNotification(data.message || "Invalid 2FA code");
      }
    } catch (error) {
      showNotification("Network error occurred");
    }
  }

  function showNotification(message, type = "error") {
    const notification = document.getElementById("notification");
    const messageEl = document.getElementById("notification-message");
    messageEl.textContent = message;

    notification.className = "fixed top-4 right-4 px-4 py-2 rounded shadow-lg z-50";
    if (type === "success") {
      notification.classList.add("bg-green-500", "text-white");
    } else {
      notification.classList.add("bg-red-500", "text-white");
    }

    notification.classList.remove("hidden");
    setTimeout(() => notification.classList.add("hidden"), 3000);
  }

  connectWS();
});

function toggle2FA(currentStatus) {
  toggle2FABtn.disabled = true;
  toggle2FABtn.classList.add('cursor-not-allowed');
  if (currentStatus) {
    manage2FAModal.classList.remove('hidden');
  } else {
    toggle2FABtn.textContent = "Enabling..."
    sendToggle2FA();
  }
}
