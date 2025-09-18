function togglePasswordVisibility(inputId, button) {
  const input = document.getElementById(inputId);
  const icon = button.querySelector('span');
  if (input.type === 'password') {
    input.type = 'text';
    icon.textContent = 'visibility_off';
  } else {
    input.type = 'password';
    icon.textContent = 'visibility';
  }
}

document.addEventListener('DOMContentLoaded', function() {
    const profileButton = document.querySelector('.group.relative button');
    const tooltip = document.querySelector('.tooltip');

    profileButton.addEventListener('click', function(e) {
        e.preventDefault();
        tooltip.classList.toggle('invisible');
        tooltip.classList.toggle('opacity-0');
    });

    document.addEventListener('click', function(e) {
        if (!profileButton.contains(e.target) && !tooltip.contains(e.target)) {
            tooltip.classList.add('invisible', 'opacity-0');
        }
    });
});

function showSuccessMessage(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);

    fetch(form.action, {
        method: 'POST',
        body: formData
    }).then(response => {
        if (response.ok) {
            const banner = document.getElementById('success-banner');
            const overlay = document.getElementById('success-overlay');

            overlay.style.display = 'block';
            overlay.style.opacity = '1';

            banner.style.display = 'flex';
            banner.style.opacity = '1';
            banner.style.transform = 'translate(-50%, -50%) scale(1)';
            banner.classList.add('success-banner');
        }
    });
}

function validatePassword(event){
  var password = document.getElementById("new-password").value;
  var confirmPassword = document.getElementById("confirm-new-password").value;
  var error = document.getElementById("error");

  if (password.length < 8) {
    error.textContent = "Password must be at least 8 characters long.";
    return false;
  }

  if (!/(?=.*[A-Z])/.test(password)) {
    error.textContent = "Password must contain at least one uppercase letter.";
    return false;
  }

  if (!/(?=.*[a-z])/.test(password)) {
    error.textContent = "Password must contain at least one lowercase letter.";
    return false;
  }

  if (!/(?=.*[0-9])/.test(password)) {
    error.textContent = "Password must contain at least one number.";
    return false;
  }

  if (!/(?=.*[-#?!@$ %^&*_])/.test(password)) {
    error.textContent = "Password must contain at least one special character.";
    return false;
  }

  if (password !== confirmPassword) {
    error.textContent = "Passwords do not match.";
    return false;
  }

  error.textContent = "";
  showSuccessMessage(event);
  return true;
}
