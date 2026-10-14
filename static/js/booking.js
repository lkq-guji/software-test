"use strict";

const venueSelect = document.getElementById("venue-id");
const venueHint = document.getElementById("venue-hint");
function showVenueFacts() {
  const option = venueSelect?.selectedOptions[0];
  if (option?.dataset.capacity && venueHint) {
    venueHint.textContent = `当前场馆容量：${option.dataset.capacity} 人 · 基础费率：${option.dataset.rate}/小时`;
  }
}
venueSelect?.addEventListener("change", showVenueFacts);
showVenueFacts();

document.querySelectorAll("button[data-hours]").forEach((button) => {
  button.addEventListener("click", () => {
    const hours = document.getElementById("cancel-hours");
    hours.value = button.dataset.hours;
    hours.form.requestSubmit();
  });
});
