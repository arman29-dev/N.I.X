document.getElementById("send-code-btn").addEventListener("click", function () {
  const sendCodeBtn = document.getElementById("send-code-btn");
  const sendCodeText = document.getElementById("send-code-text");
  const spinner = document.getElementById("spinner");
  const successMessage = document.getElementById("success-message");
  sendCodeText.classList.add("hidden");
  spinner.classList.remove("hidden");
  sendCodeBtn.disabled = true;
  setTimeout(() => {
    spinner.classList.add("hidden");
    successMessage.textContent = "Verification code sent to your email.";
    successMessage.classList.add("show");
    setTimeout(() => {
      const emailSection = document.getElementById("email-section");
      const resetSection = document.getElementById("reset-section");
      emailSection.style.transition = "opacity 0.5s ease-out";
      emailSection.style.opacity = "0";
      setTimeout(() => {
        emailSection.classList.add("hidden");
        resetSection.classList.remove("hidden");
        setTimeout(() => {
          resetSection.classList.add("show");
        }, 10);
      }, 500);
    }, 1000);
  }, 1500);
});
document.querySelectorAll(".password-toggle-icon").forEach((item) => {
  item.addEventListener("click", (event) => {
    const icon = event.currentTarget;
    const input = icon.previousElementSibling;
    if (input.type === "password") {
      input.type = "text";
      icon.textContent = "visibility";
    } else {
      input.type = "password";
      icon.textContent = "visibility_off";
    }
  });
});
