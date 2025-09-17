// Existing script from originalDashboard.html
const addDeviceBtn = document.getElementById('add-device-btn');
const modalDashboard = document.getElementById('add-device-modal');
const closeModalBtnDashboard = document.getElementById('close-modal-btn');

// addDeviceBtn.addEventListener('click', () => {
//     modalDashboard.classList.remove('modal-closing');
//     modalDashboard.style.display = 'flex';
// });

// const closeModalDashboard = () => {
//     modalDashboard.classList.add('modal-closing');
//     modalDashboard.addEventListener('animationend', () => {
//         modalDashboard.style.display = 'none';
//         modalDashboard.classList.remove('modal-closing');
//     }, { once: true });
// };

// closeModalBtnDashboard.addEventListener('click', closeModalDashboard);
// modalDashboard.addEventListener('click', (e) => {
//     if (e.target === modalDashboard) {
//         closeModalDashboard();
//     }
// });

// document.addEventListener('keydown', (e) => {
//     if (e.key === 'Escape' && modalDashboard.style.display === 'flex') {
//         closeModalDashboard();
//     }
// });

// New script from OriginalModal.html for the new modal
const openModalBtn = document.getElementById('add-device-btn'); // Use the same button from the dashboard
const closeModalBtn = document.getElementById('close-modal-btn');
const modal = document.getElementById('device-modal');
const modalContent = document.getElementById('modal-content');
const radioButtons = document.querySelectorAll('input[name="device-type"]');
const addButton = document.getElementById('add-device-final-btn');
const labels = document.querySelectorAll('.device-option-label');

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
    }, 300);
}

openModalBtn.addEventListener('click', openModal);
closeModalBtn.addEventListener('click', closeModal);

modal.addEventListener('click', (event) => {
    if (event.target === modal) {
        closeModal();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
        closeModal();
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
