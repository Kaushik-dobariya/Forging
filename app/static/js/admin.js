/**
 * Forging CMS - Enterprise Super Admin Scripts
 * Collapsible Sidebar, Accordion Navigation, Accessible Delete Modals, Tooltips
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Sidebar Desktop Collapse Persistence
  const sidebarStorageKey = 'forging_admin_sidebar_collapsed';
  const isCollapsed = localStorage.getItem(sidebarStorageKey) === 'true';
  if (isCollapsed) {
    document.body.classList.add('sidebar-collapsed');
  }

  const sidebarToggleBtn = document.querySelector('.btn-sidebar-toggle');
  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener('click', () => {
      document.body.classList.toggle('sidebar-collapsed');
      const nowCollapsed = document.body.classList.contains('sidebar-collapsed');
      localStorage.setItem(sidebarStorageKey, nowCollapsed ? 'true' : 'false');
    });
  }

  // 2. Mobile Navigation Drawer
  const mobileToggleBtn = document.querySelector('.btn-mobile-toggle');
  const sidebarBackdrop = document.querySelector('.sidebar-backdrop');

  if (mobileToggleBtn) {
    mobileToggleBtn.addEventListener('click', () => {
      document.body.classList.toggle('sidebar-mobile-open');
    });
  }

  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', () => {
      document.body.classList.remove('sidebar-mobile-open');
    });
  }

  // 3. Accordion Submenus & Active Group Auto-Expansion
  const openSubmenusKey = 'forging_admin_open_submenus';
  let openSubmenus = [];
  try {
    openSubmenus = JSON.parse(sessionStorage.getItem(openSubmenusKey) || '[]');
  } catch (err) {
    openSubmenus = [];
  }

  const navItemsWithSubmenu = document.querySelectorAll('.admin-nav-item.has-submenu');
  navItemsWithSubmenu.forEach((item, index) => {
    const itemLabel = item.querySelector('.nav-label')?.textContent?.trim() || String(index);
    const hasActiveChild = item.querySelector('.admin-subnav-link.active') !== null;
    const isParentActive = item.classList.contains('active-parent');

    // Expand if active or if user had opened it
    if (hasActiveChild || isParentActive || openSubmenus.includes(itemLabel)) {
      item.classList.add('open');
      if (hasActiveChild || isParentActive) {
        item.classList.add('active-parent');
        if (!openSubmenus.includes(itemLabel)) {
          openSubmenus.push(itemLabel);
          sessionStorage.setItem(openSubmenusKey, JSON.stringify(openSubmenus));
        }
      }
    }

    const triggerLink = item.querySelector('.admin-nav-link');
    if (triggerLink) {
      triggerLink.addEventListener('click', (e) => {
        // If sidebar is collapsed on desktop, expand it
        if (document.body.classList.contains('sidebar-collapsed') && window.innerWidth >= 1024) {
          document.body.classList.remove('sidebar-collapsed');
          localStorage.setItem(sidebarStorageKey, 'false');
        }

        const isChevron = e.target.closest('.nav-chevron') !== null;
        const href = triggerLink.getAttribute('href');

        // Toggle submenu if chevron clicked or link is anchor
        if (isChevron || href === '#' || href === 'javascript:void(0)') {
          e.preventDefault();
          item.classList.toggle('open');

          if (item.classList.contains('open')) {
            if (!openSubmenus.includes(itemLabel)) openSubmenus.push(itemLabel);
          } else {
            openSubmenus = openSubmenus.filter(k => k !== itemLabel);
          }
          sessionStorage.setItem(openSubmenusKey, JSON.stringify(openSubmenus));
        } else {
          // If navigating to the parent hub link, ensure it stays open in sessionStorage
          if (!openSubmenus.includes(itemLabel)) {
            openSubmenus.push(itemLabel);
            sessionStorage.setItem(openSubmenusKey, JSON.stringify(openSubmenus));
          }
        }
      });
    }
  });

  // 3b. Sidebar Navigation Scroll Position Preservation
  const navContainer = document.querySelector('.admin-nav-container');
  const scrollStorageKey = 'forging_admin_sidebar_scroll';

  if (navContainer) {
    // Restore saved scroll position
    const savedScroll = sessionStorage.getItem(scrollStorageKey);
    if (savedScroll !== null) {
      const scrollPos = parseInt(savedScroll, 10);
      if (!isNaN(scrollPos) && scrollPos > 0) {
        navContainer.scrollTop = scrollPos;
      }
    }

    // Save scroll on user scrolling
    let scrollTimeout;
    navContainer.addEventListener('scroll', () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        sessionStorage.setItem(scrollStorageKey, String(navContainer.scrollTop));
      }, 50);
    }, { passive: true });

    // Save immediately before navigating on any sidebar link
    document.querySelectorAll('.admin-nav-link, .admin-subnav-link').forEach(link => {
      link.addEventListener('click', () => {
        sessionStorage.setItem(scrollStorageKey, String(navContainer.scrollTop));
      });
    });

    // Bring active subnav or active item smoothly into view if offscreen
    requestAnimationFrame(() => {
      const activeLink = document.querySelector('.admin-subnav-link.active') || document.querySelector('.admin-nav-link.active');
      if (activeLink) {
        const itemRect = activeLink.getBoundingClientRect();
        const containerRect = navContainer.getBoundingClientRect();
        if (itemRect.top < containerRect.top || itemRect.bottom > containerRect.bottom) {
          activeLink.scrollIntoView({ block: 'nearest', behavior: 'auto' });
          sessionStorage.setItem(scrollStorageKey, String(navContainer.scrollTop));
        }
      }
    });
  }


  // 4. Accessible Delete Confirmation Modal
  const modalBackdrop = document.getElementById('deleteConfirmModal');
  const modalEntityName = document.getElementById('deleteModalEntityName');
  const modalDeleteForm = document.getElementById('deleteModalForm');
  const modalCancelBtn = document.getElementById('deleteModalCancel');
  const modalCloseBtn = document.getElementById('deleteModalClose');

  function openDeleteModal(actionUrl, entityName) {
    if (!modalBackdrop) return;
    if (modalEntityName) modalEntityName.textContent = entityName || 'this record';
    if (modalDeleteForm) modalDeleteForm.action = actionUrl;
    modalBackdrop.classList.add('open');
    if (modalCancelBtn) modalCancelBtn.focus();
  }

  function closeDeleteModal() {
    if (!modalBackdrop) return;
    modalBackdrop.classList.remove('open');
  }

  document.querySelectorAll('.btn-delete-trigger').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const actionUrl = btn.getAttribute('data-action') || (btn.closest('form') ? btn.closest('form').action : '#');
      const entityName = btn.getAttribute('data-entity-name') || 'this item';
      openDeleteModal(actionUrl, entityName);
    });
  });

  if (modalCancelBtn) modalCancelBtn.addEventListener('click', closeDeleteModal);
  if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeDeleteModal);
  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', (e) => {
      if (e.target === modalBackdrop) closeDeleteModal();
    });
  }

  // Escape key closes modals and mobile drawer
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeDeleteModal();
      document.body.classList.remove('sidebar-mobile-open');
    }
  });

  // 5. Flash Alert Auto-Dismiss
  document.querySelectorAll('.alert').forEach(alert => {
    const closeBtn = alert.querySelector('[data-dismiss="alert"]');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => alert.remove());
    }
  });

  // 6. Enterprise Admin Account Dropdown Interaction & Keyboard Navigation
  const accountWrapper = document.querySelector('.admin-account-dropdown-wrapper');
  const accountBtn = document.getElementById('adminAccountDropdownBtn');
  const accountMenu = document.getElementById('adminAccountMenu');

  if (accountWrapper && accountBtn && accountMenu) {
    const toggleAccountMenu = (forceOpen) => {
      const willOpen = typeof forceOpen === 'boolean' ? forceOpen : !accountWrapper.classList.contains('open');
      accountWrapper.classList.toggle('open', willOpen);
      accountBtn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      if (willOpen) {
        const firstItem = accountMenu.querySelector('[role="menuitem"]');
        if (firstItem) firstItem.focus();
      }
    };

    accountBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleAccountMenu();
    });

    // Close on outside click or tap
    document.addEventListener('click', (e) => {
      if (!accountWrapper.contains(e.target)) {
        accountWrapper.classList.remove('open');
        accountBtn.setAttribute('aria-expanded', 'false');
      }
    });

    // Escape and Arrow key navigation
    accountWrapper.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        accountWrapper.classList.remove('open');
        accountBtn.setAttribute('aria-expanded', 'false');
        accountBtn.focus();
        return;
      }

      if (!accountWrapper.classList.contains('open')) {
        if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleAccountMenu(true);
        }
        return;
      }

      const menuItems = Array.from(accountMenu.querySelectorAll('[role="menuitem"]'));
      const activeIdx = menuItems.indexOf(document.activeElement);

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const nextIdx = (activeIdx + 1) % menuItems.length;
        menuItems[nextIdx].focus();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prevIdx = (activeIdx - 1 + menuItems.length) % menuItems.length;
        menuItems[prevIdx].focus();
      } else if (e.key === 'Home') {
        e.preventDefault();
        if (menuItems.length) menuItems[0].focus();
      } else if (e.key === 'End') {
        e.preventDefault();
        if (menuItems.length) menuItems[menuItems.length - 1].focus();
      }
    });
  }
});
