/**
 * BloodLife – main.js
 * Misc frontend helpers
 */

document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss flash alerts after 5 s
  document.querySelectorAll('.alert').forEach(el => {
    setTimeout(() => {
      el.classList.remove('show');
      el.classList.add('fade');
    }, 5000);
  });

  // Confirm dangerous actions
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      if (!confirm(el.dataset.confirm)) e.preventDefault();
    });
  });

  // Highlight active nav link (fallback for server-rendered class)
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-link-custom').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

  // Set today's date as default for date inputs marked with [data-today]
  document.querySelectorAll('input[type=date][data-today]').forEach(inp => {
    if (!inp.value) inp.value = new Date().toISOString().slice(0, 10);
  });
});
