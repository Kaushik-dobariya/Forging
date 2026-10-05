/**
 * Forging CMS - Public Frontend Scripts
 */
document.addEventListener('DOMContentLoaded', () => {
  // Mobile navigation drawer toggle
  const mobileToggle = document.querySelector('[data-toggle-nav]');
  const mobileNav = document.querySelector('[data-mobile-nav]');

  if (mobileToggle && mobileNav) {
    mobileToggle.addEventListener('click', () => {
      const isExpanded = mobileToggle.getAttribute('aria-expanded') === 'true';
      mobileToggle.setAttribute('aria-expanded', !isExpanded);
      mobileNav.classList.toggle('is-open');
    });
  }

  // Auto-dismiss alert messages after 6 seconds
  const autoAlerts = document.querySelectorAll('.alert[data-auto-dismiss]');
  autoAlerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.4s ease';
      setTimeout(() => alert.remove(), 400);
    }, 6000);
  });
});
