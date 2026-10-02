/**
 * FitBuddy Global Application Scripts
 */

// Toast Notification Manager
const FitBuddy = {
  toast: function (message, type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✓';
    if (type === 'error') icon = '⚠️';

    toast.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span style="font-weight: bold;">${icon}</span>
        <span>${message}</span>
      </div>
      <button style="background:none;border:none;cursor:pointer;color:var(--text-subtle);font-size:1.1rem;" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      if (toast.parentElement) {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.25s ease';
        setTimeout(() => toast.remove(), 250);
      }
    }, duration);
  },

  // Custom In-App Modal Dialog instead of native browser confirm/alert
  confirm: function (options) {
    return new Promise((resolve) => {
      const opts = typeof options === 'string' ? { message: options } : (options || {});
      const title = opts.title || 'Please Confirm';
      const message = opts.message || 'Are you sure you want to proceed?';
      const confirmText = opts.confirmText || 'Confirm';
      const cancelText = opts.cancelText || 'Cancel';
      const confirmVariant = opts.confirmVariant || 'primary';
      const icon = opts.icon || '💬';

      const existing = document.getElementById('fitbuddy-confirm-modal');
      if (existing) existing.remove();

      const backdrop = document.createElement('div');
      backdrop.id = 'fitbuddy-confirm-modal';
      backdrop.className = 'fb-modal-backdrop';
      backdrop.innerHTML = `
        <div class="fb-modal-box" role="dialog" aria-modal="true">
          <div class="fb-modal-header">
            <div class="fb-modal-icon">${icon}</div>
            <h3 class="fb-modal-title">${title}</h3>
          </div>
          <div class="fb-modal-body">
            <p>${message}</p>
          </div>
          <div class="fb-modal-actions">
            <button type="button" class="btn btn-secondary fb-modal-cancel">${cancelText}</button>
            <button type="button" class="btn btn-${confirmVariant} fb-modal-confirm">${confirmText}</button>
          </div>
        </div>
      `;

      document.body.appendChild(backdrop);
      requestAnimationFrame(() => backdrop.classList.add('active'));

      const cleanup = (result) => {
        backdrop.classList.remove('active');
        setTimeout(() => backdrop.remove(), 200);
        resolve(result);
      };

      backdrop.querySelector('.fb-modal-cancel').onclick = () => cleanup(false);
      backdrop.querySelector('.fb-modal-confirm').onclick = () => cleanup(true);
      backdrop.onclick = (e) => {
        if (e.target === backdrop) cleanup(false);
      };
    });
  },

  // Switch Active User (Demo Helper)
  switchUser: function (userId) {
    const url = new URL(window.location.href);
    url.searchParams.set('user_id', userId);
    window.location.href = url.toString();
  },

  // Make API Request Helper
  api: async function (url, options = {}) {
    try {
      const baseUrl = window.FITBUDDY_API_BASE || '';
      const requestUrl = (url.startsWith('http://') || url.startsWith('https://')) ? url : (baseUrl + url);
      const response = await fetch(requestUrl, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        },
        ...options
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'An unexpected error occurred');
      }
      return data;
    } catch (err) {
      FitBuddy.toast(err.message, 'error');
      throw err;
    }
  }
};

// Initialize Dropdown Menus and Mobile Nav Toggle
document.addEventListener('DOMContentLoaded', () => {
  const userBtn = document.getElementById('userDropdownBtn');
  const userMenu = document.getElementById('userDropdownMenu');
  const mobileToggle = document.getElementById('mobileNavToggle');
  const primaryNav = document.getElementById('primaryNavMenu');

  if (userBtn && userMenu) {
    userBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      userMenu.classList.toggle('show');
    });

    document.addEventListener('click', () => {
      userMenu.classList.remove('show');
    });
  }

  if (mobileToggle && primaryNav) {
    mobileToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      primaryNav.classList.toggle('mobile-open');
    });

    document.addEventListener('click', (e) => {
      if (!primaryNav.contains(e.target) && e.target !== mobileToggle) {
        primaryNav.classList.remove('mobile-open');
      }
    });
  }
});
