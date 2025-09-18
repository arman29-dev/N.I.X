document.addEventListener("DOMContentLoaded", () => {
  const formContainer = document.getElementById("form-container");
  const showRegisterLink = document.getElementById("show-register");
  const showLoginLink = document.getElementById("show-login");

  showRegisterLink.addEventListener("click", (e) => {
    e.preventDefault();
    formContainer.classList.add("is-flipped");
  });

  showLoginLink.addEventListener("click", (e) => {
    e.preventDefault();
    formContainer.classList.remove("is-flipped");
  });
});


function validatePassword(){
  var password = document.getElementById("register-password").value;
  var confirmPassword = document.getElementById("confirm-password").value;
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
  return true;
}


function togglePasswordVisibility(inputId, button) {
  const passwordInput = document.getElementById(inputId);
  const icon = button.querySelector(".material-symbols-outlined");
  if (passwordInput.type === "password") {
    passwordInput.type = "text";
    icon.textContent = "visibility";
  } else {
    passwordInput.type = "password";
    icon.textContent = "visibility_off";
  }
}
