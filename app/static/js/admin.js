/**
 * Forging CMS - Super Admin Scripts
 */
document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss alert messages
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    const closeBtn = alert.querySelector('[data-dismiss="alert"]');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => alert.remove());
    }
  });

  // Attach CSRF header to asynchronous AJAX requests if present
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  if (csrfMeta) {
    window.csrfToken = csrfMeta.getAttribute('content');
  }
});
