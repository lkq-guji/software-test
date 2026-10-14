"use strict";

// Only presentation and request UX. The server owns all business decisions.
document.querySelectorAll("form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    const button = event.submitter;
    if (!button || button.disabled) return;
    button.dataset.originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = form.dataset.busyLabel || "正在提交...";
    form.setAttribute("aria-busy", "true");
  });
});

window.addEventListener("pageshow", () => {
  document.querySelectorAll("button[data-original-label]").forEach((button) => {
    button.disabled = false;
    button.textContent = button.dataset.originalLabel;
  });
  document.querySelectorAll("form[aria-busy]").forEach((form) => form.removeAttribute("aria-busy"));
});

document.querySelectorAll("[data-field]").forEach((message) => {
  const field = document.querySelector(`main [name="${message.dataset.field}"]`) || document.querySelector(`[name="${message.dataset.field}"]`);
  if (!field) return;
  field.setAttribute("aria-invalid", "true");
  const error = document.getElementById(`error-${message.dataset.field}`);
  if (error) field.setAttribute("aria-describedby", error.id);
});
