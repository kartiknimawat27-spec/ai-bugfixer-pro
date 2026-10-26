// Shared behaviour: mobile nav toggle + auto-dismiss flash messages.

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".nav-toggle");
  const links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", () => {
      links.classList.toggle("open");
      links.style.display = links.classList.contains("open") ? "flex" : "";
    });
  }

  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity .3s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 300);
    }, 5000);
  });

  // Password strength meter (register page)
  const pwField = document.querySelector("[data-pw-strength]");
  const meter = document.querySelector("[data-pw-meter]");
  if (pwField && meter) {
    pwField.addEventListener("input", () => {
      const v = pwField.value;
      let score = 0;
      if (v.length >= 8) score++;
      if (/[A-Z]/.test(v)) score++;
      if (/[0-9]/.test(v)) score++;
      if (/[^A-Za-z0-9]/.test(v)) score++;
      const labels = ["Weak", "Fair", "Good", "Strong", "Very strong"];
      const colors = ["#f0616d", "#f0b429", "#f0b429", "#3ecf8e", "#3ecf8e"];
      meter.textContent = v ? labels[score] : "";
      meter.style.color = colors[score] || "";
    });
  }
});
