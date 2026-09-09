document.addEventListener("DOMContentLoaded", () => {
  const reveal = new IntersectionObserver((entries) => entries.forEach((entry) => {
    if (entry.isIntersecting) entry.target.classList.add("is-visible");
  }), { threshold: 0.12 });
  document.querySelectorAll("[data-contact-reveal]").forEach((element) => reveal.observe(element));
  const form = document.querySelector("#contact-form");
  if (!form) return;
  const fields = ["name", "email", "subject", "message"];
  const count = document.querySelector("#contact-message-count");
  const validate = (name) => {
    const input = form.elements[name]; const error = document.querySelector(`#contact-${name}-error`); const value = input.value.trim();
    let message = !value ? `${name[0].toUpperCase() + name.slice(1)} is required.` : "";
    if (name === "email" && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) message = "Enter a valid email address.";
    input.setAttribute("aria-invalid", Boolean(message)); error.textContent = message; return !message;
  };
  fields.forEach((name) => form.elements[name].addEventListener("blur", () => validate(name)));
  form.elements.message.addEventListener("input", () => { count.textContent = `${form.elements.message.value.length} / 1000`; });
  form.addEventListener("submit", (event) => { event.preventDefault(); if (!fields.map(validate).every(Boolean)) return; if (window.AgriSmartToast) window.AgriSmartToast.show("Your message is ready to send.", "success", "Thank you"); form.reset(); count.textContent = "0 / 1000"; });
  form.addEventListener('reset', () => fields.forEach((name) => document.querySelector(`#contact-${name}-error`).textContent = ""));
});
