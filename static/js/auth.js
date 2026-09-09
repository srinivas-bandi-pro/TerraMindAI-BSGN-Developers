document.addEventListener("DOMContentLoaded", () => {
  // Dark Mode Toggle
  const themeButton = document.querySelector("[data-auth-theme]");
  if (themeButton) {
    themeButton.addEventListener("click", () => {
      document.body.classList.toggle("auth-dark");
      const span = themeButton.querySelector("span");
      if (span) {
        span.textContent = document.body.classList.contains("auth-dark") ? "Light Mode" : "Dark Mode";
      }
    });
  }

  // Password Visibility Toggle for all password fields
  const eyeBtns = document.querySelectorAll(".eye-toggle-btn");
  eyeBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const wrapper = btn.closest(".input-wrapper");
      const pwdInput = wrapper ? wrapper.querySelector("input") : null;
      if (pwdInput) {
        const isPassword = pwdInput.type === "password";
        pwdInput.type = isPassword ? "text" : "password";
        btn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
        btn.style.opacity = isPassword ? "0.5" : "1";
      }
    });
  });
});



