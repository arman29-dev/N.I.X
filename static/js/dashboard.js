document.addEventListener('DOMContentLoaded', () => {
    const openModalBtn = document.getElementById('add-device-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modal = document.getElementById('device-modal');
    const modalContent = document.getElementById('modal-content');
    const radioButtons = document.querySelectorAll('input[name="device_type"]');
    const addButton = document.getElementById('add-device-final-btn');
    const labels = document.querySelectorAll('.device-option-label');

    // QR Modal elements
    const qrModal = document.getElementById('qr-modal');
    const qrModalContent = document.getElementById('qr-modal-content');
    const closeQrModalBtn = document.getElementById('close-qr-modal-btn');
    const closeQrModalFinalBtn = document.getElementById('close-qr-modal-final-btn');
    const qrCodeImage = document.getElementById('qr-code-image');

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
            // Reset form
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
            location.reload();
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

            const data = await response.json();

            if (response.ok) {
                closeModal();
                const qrPath = data.qr_path;
                openQrModal(qrPath);
            } else {
                alert('Error: ' + (data.message || data.error || 'Failed to add device'));
            }
        } catch (error) {
            alert('Error: ' + error.message);
        } finally {
            addButton.disabled = false;
            addButton.textContent = 'Add Device';
        }
    }

    // Event listeners
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
});

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
