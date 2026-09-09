document.addEventListener("DOMContentLoaded", () => {
  const reveal = new IntersectionObserver((entries) => entries.forEach((entry) => {
    if (entry.isIntersecting) entry.target.classList.add("is-visible");
  }), { threshold: 0.12 });
  document.querySelectorAll("[data-about-reveal]").forEach((element) => reveal.observe(element));
});
