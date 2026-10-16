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
  const navItemsWithSubmenu = document.querySelectorAll('.admin-nav-item.has-submenu');
  navItemsWithSubmenu.forEach(item => {
    // If active child inside, expand parent
    const hasActiveChild = item.querySelector('.admin-subnav-link.active');
    if (hasActiveChild) {
      item.classList.add('open', 'active-parent');
    }

    const triggerLink = item.querySelector('.admin-nav-link');
    if (triggerLink) {
      triggerLink.addEventListener('click', (e) => {
        // If sidebar is collapsed on desktop, don't toggle accordion on click (link works or expand)
        if (document.body.classList.contains('sidebar-collapsed') && window.innerWidth >= 1024) {
          document.body.classList.remove('sidebar-collapsed');
          localStorage.setItem(sidebarStorageKey, 'false');
        }
        
        // Prevent default if clicking arrow or link has subnav
        const isChevron = e.target.closest('.nav-chevron');
        if (isChevron || triggerLink.getAttribute('href') === '#') {
          e.preventDefault();
          item.classList.toggle('open');
        }
      });
    }
  });

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
});
