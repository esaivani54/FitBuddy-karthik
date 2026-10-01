/**
 * FitBuddy Admin Dashboard Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('admin-user-search');
  const userRows = document.querySelectorAll('.admin-user-row');
  const seedBtn = document.getElementById('admin-seed-btn');
  const resetBtn = document.getElementById('admin-reset-btn');

  // Initialize Goal Progress Bars
  document.querySelectorAll('.goal-progress-bar').forEach(bar => {
    const progress = bar.getAttribute('data-progress') || '0';
    bar.style.width = progress + '%';
  });

  // Search filter
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      userRows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
      });
    });
  }

  // Seed sample data
  if (seedBtn) {
    seedBtn.addEventListener('click', async () => {
      seedBtn.disabled = true;
      seedBtn.innerHTML = '<span class="spinner spinner-primary"></span> Seeding...';
      try {
        await FitBuddy.api('/api/admin/seed', { method: 'POST' });
        FitBuddy.toast('Sample users and plans seeded successfully!', 'success');
        setTimeout(() => window.location.reload(), 800);
      } catch (err) {
        seedBtn.disabled = false;
        seedBtn.textContent = 'Seed Demo Data';
      }
    });
  }

  // Reset database
  if (resetBtn) {
    resetBtn.addEventListener('click', async () => {
      const confirmed = await FitBuddy.confirm({
        title: 'Reset Database?',
        message: 'Are you sure you want to reset all user and workout records to the demonstration baseline?',
        confirmText: 'Reset Records',
        confirmVariant: 'danger',
        icon: '⚠️'
      });

      if (confirmed) {
        resetBtn.disabled = true;
        resetBtn.innerHTML = '<span class="spinner"></span> Resetting...';
        try {
          await FitBuddy.api('/api/admin/reset', { method: 'POST' });
          FitBuddy.toast('Database reset to clean baseline!', 'success');
          setTimeout(() => window.location.reload(), 800);
        } catch (err) {
          resetBtn.disabled = false;
          resetBtn.textContent = 'Reset Database';
        }
      }
    });
  }
});
