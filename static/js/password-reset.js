function togglePasswordVisibility(inputId, button) {
  const input = document.getElementById(inputId);
  const icon = button.querySelector("span");
  if (input.type === "password") {
    input.type = "text";
    icon.textContent = "visibility_off";
  } else {
    input.type = "password";
    icon.textContent = "visibility";
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const profileButton = document.querySelector(".group.relative button");
  const tooltip = document.querySelector(".tooltip");

  profileButton.addEventListener("click", function (e) {
    e.preventDefault();
    tooltip.classList.toggle("invisible");
    tooltip.classList.toggle("opacity-0");
  });

  document.addEventListener("click", function (e) {
    if (!profileButton.contains(e.target) && !tooltip.contains(e.target)) {
      tooltip.classList.add("invisible", "opacity-0");
    }
  });
});

const newPswdInput = document.getElementById('new-pswd');
const cnfNewPswdInput = document.getElementById('cnf-new-pswd');
const verificationCodeInput = document.getElementById('verification-code');
const verificationCodeHashInput = document.getElementById('verification-code-hash');
const changePswdBtn = document.getElementById("change-pswd-btn");
const error = document.getElementById("error");

changePswdBtn.addEventListener('click', async () => {
  const newPswd = newPswdInput.value;
  const cnfNewPswd = cnfNewPswdInput.value;
  const verificationCode = verificationCodeInput.value;
  const verificationCodeHash = verificationCodeHashInput.value;

  const pswdChangeForm = new FormData();

  if (validatePassword(newPswd, cnfNewPswd)){
    try{
      changePswdBtn.disabled = true;
      changePswdBtn.innerText = "Setting New Password...";
      changePswdBtn.classList.add('cursor-not-allowed');

      pswdChangeForm.append('new_pswd', newPswd);
      pswdChangeForm.append('cnfm_pswd', cnfNewPswd);
      pswdChangeForm.append('verification_code', verificationCode);
      pswdChangeForm.append('verification_code_hash', verificationCodeHash);

      const res = await fetch(API.endpoint, {
        method: "PUT",
        body: pswdChangeForm
      })

      const resData = await res.json();
      if (res.status === 200){
        showSuccessMessage();
      } else {
        changePswdBtn.disabled = false;
        changePswdBtn.innerText = "Change Password";
        changePswdBtn.classList.remove('cursor-not-allowed');

        error.innerText = resData.msg || "Unable to set new password";
        console.log(resData.error);
      }

    } catch (error) {
      changePswdBtn.disabled = false;
      changePswdBtn.innerText = "Change Password";
      changePswdBtn.classList.remove('cursor-not-allowed');
      error.innerText = error || "Unable to set new password";
    }
  }
})


function showSuccessMessage() {
  const banner = document.getElementById("success-banner");
  const overlay = document.getElementById("success-overlay");

  overlay.style.display = "block";
  overlay.style.opacity = "1";

  banner.style.display = "flex";
  banner.style.opacity = "1";
  banner.style.transform = "translate(-50%, -50%) scale(1)";
  banner.classList.add("success-banner");
}

function validatePassword(password, confirmPassword) {
  if (password.length < 8) {
    error.innerText = "Password must be at least 8 characters long.";
    return false;
  }

  if (!/(?=.*[A-Z])/.test(password)) {
    error.innerText = "Password must contain at least one uppercase letter.";
    return false;
  }

  if (!/(?=.*[a-z])/.test(password)) {
    error.innerText = "Password must contain at least one lowercase letter.";
    return false;
  }

  if (!/(?=.*[0-9])/.test(password)) {
    error.innerText = "Password must contain at least one number.";
    return false;
  }

  if (!/(?=.*[-#?!@$ %^&*_])/.test(password)) {
    error.innerText = "Password must contain at least one special character.";
    return false;
  }

  if (password !== confirmPassword) {
    error.innerText = "Passwords do not match.";
    return false;
  }

  error.innerText = "";
  return true;
}
