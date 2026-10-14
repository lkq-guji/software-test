"use strict";

// Query and aggregation run on StatisticsService. This script only announces loading.
const statisticsForm = document.querySelector('[data-testid="statistics-form"]');
statisticsForm?.addEventListener("submit", () => {
  const button = statisticsForm.querySelector('[data-testid="statistics-submit"]');
  button.setAttribute("aria-label", "正在生成统计，请稍候");
});
