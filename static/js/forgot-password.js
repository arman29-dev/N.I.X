document.getElementById("send-code-btn").addEventListener("click", async function () {
  const sendCodeBtn = document.getElementById("send-code-btn");
  const sendCodeText = document.getElementById("send-code-text");
  const spinner = document.getElementById("spinner");

  const errorMessage = document.getElementById("errorMsg");
  const successMessage = document.getElementById("successMsg");

  const emailInputField = document.getElementById('email-address');

  sendCodeText.classList.add("hidden");
  spinner.classList.remove("hidden");

  sendCodeBtn.disabled = true;
  sendCodeBtn.classList.add('cursor-not-allowed');

  try {
    const formData = new FormData();
    formData.append('email', emailInputField.value);

    const response = await fetch(API.endpoint, {
      method: "POST",
      body: formData
    })

    let responseData;
    try {
      responseData = await response.json();
    } catch (jsonError) {
      throw new Error("Server returned invalid response");
    }

    if (response.ok) {
      spinner.classList.add("hidden");
      sendCodeText.classList.remove("hidden");
      successMessage.innerText = "Verification code sent to your email";
      successMessage.classList.add("show");
      setTimeout(() => window.location.href = responseData.endpoint, 3000);
    } else {
      spinner.classList.add("hidden");
      sendCodeText.classList.remove("hidden");
      errorMessage.innerText = responseData.error;
      errorMessage.classList.add("show");
    }
  } catch (error) {
    spinner.classList.add("hidden");
    sendCodeText.classList.remove("hidden");
    errorMessage.innerText = error.message || "An error occurred";
    errorMessage.classList.add("show");
  }

  sendCodeBtn.disabled = false;
  sendCodeBtn.classList.remove('cursor-not-allowed');
});
