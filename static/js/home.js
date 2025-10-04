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

const loginErrorMsg = document.getElementById('login-error-msg');

const emailInput = document.getElementById('login-email');
const pswdInput = document.getElementById('login-password');
const sbmtLoginDataBtn = document.getElementById('submit-login-data-btn');

const twoFAinputDiv = document.getElementById('2fa-input-div');
const twoFAinput = document.getElementById('2fa-input');
const twoFAVerifyBtn = document.getElementById('2fa-verify-btn');

twoFAinput.disabled = true;
twoFAVerifyBtn.disabled = true;

sbmtLoginDataBtn.addEventListener('click', async () => {
  const email = emailInput.value;
  const pswd = pswdInput.value;
  const formData = new FormData();

  sbmtLoginDataBtn.disabled = true;
  sbmtLoginDataBtn.innerText = "Verifying Credencials...";
  sbmtLoginDataBtn.classList.add('cursor-not-allowed');
  sbmtLoginDataBtn.classList.remove('hover:scale-105');

  formData.append('email', email);
  formData.append('password', pswd);

  try {
    const loginResponse = await fetch(API_ENDPOINT.login, {
      method: "POST",
      body: formData
    })

    const loginResponseData = await loginResponse.json();

    if (loginResponse.status === 302){
      loginErrorMsg.innerText = "";
      sbmtLoginDataBtn.innerText = "Credencials Verified ✔️"
      if (loginResponseData.is2FAenabled) {
        emailInput.ariaPlaceholder = email; emailInput.disabled = true; emailInput.classList.add('cursor-not-allwoed')
        pswdInput.ariaPlaceholder = pswd; pswdInput.disabled = true; pswdInput.classList.add('cursor-not-allwoed')

        twoFAinput.disabled = false;
        twoFAVerifyBtn.disabled = false;
        twoFAinputDiv.classList.remove('hidden');

        twoFAVerifyBtn.addEventListener('click', () => {
          twoFAVerifyBtn.disabled = true;
          twoFAVerifyBtn.innerText = "Verifying...";
          twoFAVerifyBtn.classList.add('cursor-not-allowed');
          twoFAVerifyBtn.classList.remove('hover:scale-105', 'hover:cursor-pointer');
          verify2FA(email, twoFAinput.value, loginResponseData.twoFAverificationEndpoint);
        })
      } else {
        window.location.href = loginResponseData.redirectUrl;
      }
    } else if (loginResponse.status === 404) {
      document.getElementById('animated-arrow').classList.remove('hidden');

      sbmtLoginDataBtn.disabled = false;
      sbmtLoginDataBtn.innerText = "Login";
      sbmtLoginDataBtn.classList.remove('cursor-not-allowed');
      sbmtLoginDataBtn.classList.add('hover:scale-105');

      loginErrorMsg.innerText = loginResponseData.loginError;
    } else {
      sbmtLoginDataBtn.disabled = false;
      sbmtLoginDataBtn.innerText = "Try Again";
      sbmtLoginDataBtn.classList.remove('cursor-not-allowed');
      sbmtLoginDataBtn.classList.add('hover:scale-105');

      loginErrorMsg.innerText = loginResponseData.loginError;
    }
  } catch (error) {
    loginErrorMsg.innerText = error || "Unable to log you in.";
  }
})


async function verify2FA(email, code, endpoint) {
  try {
    const verificationRes = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code, email: email }),
    })

    const verificationResData = await verificationRes.json();

    if (verificationRes.ok) {
      window.location.href = verificationResData.redirectUrl;
    } else {
      twoFAVerifyBtn.disabled = false;
      twoFAVerifyBtn.classList.remove('cursor-not-allowed');
      twoFAVerifyBtn.innerText = "Verify Again"
      loginErrorMsg.innerText = verificationResData.loginError;
    }
  } catch (error) {
    loginErrorMsg.innerText = error || "Unable to verify you!";
  }
}


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
