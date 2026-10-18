/**
 * Forging CMS - Public Frontend Scripts
 * Industrial Engineering Theme & Interactive Components
 */
document.addEventListener('DOMContentLoaded', () => {
  // ==============================================================================
  // 1. Mobile Navigation Drawer Controller
  // ==============================================================================
  const mobileToggles = document.querySelectorAll('[data-toggle-nav]');
  const mobileNav = document.querySelector('[data-mobile-nav]');
  const mobileBackdrop = document.querySelector('.mobile-nav-backdrop');

  function toggleMobileNav() {
    if (!mobileNav) return;
    const isOpen = mobileNav.classList.contains('is-open');
    if (isOpen) {
      mobileNav.classList.remove('is-open');
      mobileNav.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
      mobileToggles.forEach(t => t.setAttribute('aria-expanded', 'false'));
    } else {
      mobileNav.classList.add('is-open');
      mobileNav.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
      mobileToggles.forEach(t => t.setAttribute('aria-expanded', 'true'));
    }
  }

  mobileToggles.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      toggleMobileNav();
    });
  });

  if (mobileBackdrop) {
    mobileBackdrop.addEventListener('click', toggleMobileNav);
  }

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && mobileNav && mobileNav.classList.contains('is-open')) {
      toggleMobileNav();
    }
  });


  // ==============================================================================
  // 2. Dynamic Homepage Hero Slider
  // ==============================================================================
  const slider = document.querySelector('#home-hero-slider');
  if (slider) {
    const slides = slider.querySelectorAll('.hero-slide');
    const dots = slider.querySelectorAll('.slider-dot');
    const prevBtn = slider.querySelector('.slider-prev');
    const nextBtn = slider.querySelector('.slider-next');
    let currentIndex = 0;
    let autoplayTimer = null;
    const intervalMs = 5000;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function showSlide(index) {
      if (slides.length <= 1) return;
      if (index < 0) {
        currentIndex = slides.length - 1;
      } else if (index >= slides.length) {
        currentIndex = 0;
      } else {
        currentIndex = index;
      }

      slides.forEach((s, idx) => {
        if (idx === currentIndex) {
          s.classList.add('active');
          s.style.display = 'flex';
          s.setAttribute('aria-hidden', 'false');
        } else {
          s.classList.remove('active');
          s.style.display = 'none';
          s.setAttribute('aria-hidden', 'true');
        }
      });

      dots.forEach((d, idx) => {
        if (idx === currentIndex) {
          d.classList.add('active');
          d.style.background = 'var(--color-accent)';
        } else {
          d.classList.remove('active');
          d.style.background = 'transparent';
        }
      });
    }

    function startAutoplay() {
      if (prefersReducedMotion || slides.length <= 1) return;
      stopAutoplay();
      autoplayTimer = setInterval(() => {
        showSlide(currentIndex + 1);
      }, intervalMs);
    }

    function stopAutoplay() {
      if (autoplayTimer) {
        clearInterval(autoplayTimer);
        autoplayTimer = null;
      }
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        showSlide(currentIndex - 1);
        startAutoplay();
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        showSlide(currentIndex + 1);
        startAutoplay();
      });
    }

    dots.forEach((dot, idx) => {
      dot.addEventListener('click', () => {
        showSlide(idx);
        startAutoplay();
      });
    });

    // Pause on hover
    slider.addEventListener('mouseenter', stopAutoplay);
    slider.addEventListener('mouseleave', startAutoplay);

    // Keyboard navigation when focused or hovering over slider
    slider.setAttribute('tabindex', '0');
    slider.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') {
        showSlide(currentIndex - 1);
        startAutoplay();
      } else if (e.key === 'ArrowRight') {
        showSlide(currentIndex + 1);
        startAutoplay();
      }
    });

    // Mobile swipe gestures
    let touchStartX = 0;
    let touchEndX = 0;

    slider.addEventListener('touchstart', (e) => {
      touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    slider.addEventListener('touchend', (e) => {
      touchEndX = e.changedTouches[0].screenX;
      handleSwipe();
    }, { passive: true });

    function handleSwipe() {
      const swipeThreshold = 45;
      if (touchEndX < touchStartX - swipeThreshold) {
        // Swipe Left -> Next
        showSlide(currentIndex + 1);
        startAutoplay();
      } else if (touchEndX > touchStartX + swipeThreshold) {
        // Swipe Right -> Prev
        showSlide(currentIndex - 1);
        startAutoplay();
      }
    }

    // Initialize autoplay
    startAutoplay();
  }


  // ==============================================================================
  // 3. Auto-Dismiss Alert Messages
  // ==============================================================================
  const autoAlerts = document.querySelectorAll('.alert[data-auto-dismiss]');
  autoAlerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.4s ease';
      setTimeout(() => alert.remove(), 400);
    }, 6000);
  });
});
