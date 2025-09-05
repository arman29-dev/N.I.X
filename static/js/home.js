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
  var password = document.getElementById("password").value;
  var confirmPassword = document.getElementById("confirm-password").value;
  var error = document.getElementById("error");

  if (password !== confirmPassword) {
    error.textContent = "Passwords do not match";
    return false;
  } else {
    error.textContent = "";
    return true;
  }
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
