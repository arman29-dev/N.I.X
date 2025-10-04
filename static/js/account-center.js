let currentAction = null;

const { delDeviceUrl, delAccountUrl, manage2FAUrl, logoutUrl } = API_DATA;

const manage2FABtn = document.getElementById('manage2FABtn');
const manage2FAModal = document.getElementById('manage-2fa-modal');
const cnf2FAdisableBtn = document.getElementById('confirm-2fa-disable')
const cncl2FAdisableBtn = document.getElementById('cancel-2fa-disable')

cnf2FAdisableBtn.addEventListener("click", () => {
  cnf2FAdisableBtn.textContent = 'Disabling...';
  exeManage2FA(false);
});

cncl2FAdisableBtn.addEventListener("click", () => {
  manage2FAModal.classList.add('hidden');
  manage2FABtn.disabled = false;
  manage2FABtn.classList.remove('cursor-not-allowed');
})

document.addEventListener("DOMContentLoaded", () => {

  const modal = document.getElementById("twofa-modal");
  const deleteDevicesBtn = document.getElementById("delete-devices-btn");
  const deleteAccountBtn = document.getElementById("delete-account-btn");
  const submitBtn = document.getElementById("submit-2fa");
  const cancelBtn = document.getElementById("cancel-2fa");
  const inputs = modal?.querySelectorAll("input") || [];

  // Handle warning modal (no input fields)
  if (cancelBtn && inputs.length === 0) {
    cancelBtn.addEventListener("click", () => {
      modal.classList.add("hidden");
    });
  }

  deleteDevicesBtn.addEventListener("click", () => openModal("devices"));
  deleteAccountBtn.addEventListener("click", () => openModal("account"));
  submitBtn.addEventListener("click", handleSubmit);
  cancelBtn.addEventListener("click", closeModal);

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

    const endpoint = currentAction === "devices" ? delDeviceUrl : delAccountUrl;

    try {
      const response = await fetch(endpoint, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
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

});

async function exeManage2FA(action) {
  const endpoint = `${manage2FAUrl}?action=${action}`;

  try {
    const response = await fetch(endpoint, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
    });

    const responseData = response.json();
    if (response.ok) {
      location.reload();
      showNotification(responseData.message, 'success')
    } else {
      showNotification("Unable to perform the action" || responseData.message)
    }
  } catch (error) {
    showNotification(error)
  }
}

function manage2FA(action) {
  manage2FABtn.disabled = true;
  manage2FABtn.classList.add('cursor-not-allowed');
  if (action === true) {
    manage2FABtn.textContent = "Enabling..."
    exeManage2FA(action);
  } else {
    manage2FAModal.classList.remove('hidden');
  }
}
