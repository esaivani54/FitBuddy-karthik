/**
 * FitBuddy Workout Tracker & Interactive Circular Timer Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  const logContainer = document.getElementById('daily-workout-tracker');
  if (!logContainer) return;

  const planId = parseInt(logContainer.getAttribute('data-plan-id')) || 0;
  const userId = parseInt(logContainer.getAttribute('data-user-id')) || 0;
  const dayNumber = parseInt(logContainer.getAttribute('data-day-number')) || 1;

  // ============================================================
  // 1. CIRCULAR SVG REST TIMER CONTROLLER
  // ============================================================
  let totalRestSeconds = 45;
  let remainingSeconds = 45;
  let timerInterval = null;
  let isTimerRunning = false;
  const CIRCLE_CIRCUMFERENCE = 440; // 2 * PI * 70

  const timerDisplay = document.getElementById('workout-timer-display');
  const timerCircle = document.getElementById('timer-svg-circle');
  const startBtn = document.getElementById('timer-start-btn');
  const pauseBtn = document.getElementById('timer-pause-btn');
  const resetBtn = document.getElementById('timer-reset-btn');
  const customTimerBtn = document.getElementById('btn-custom-timer');
  const durationText = document.getElementById('timer-rest-duration-text');

  function formatTimerString(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }

  function updateTimerCircle() {
    if (!timerCircle) return;
    const progressFraction = Math.max(0, remainingSeconds / totalRestSeconds);
    const dashOffset = CIRCLE_CIRCUMFERENCE * (1 - progressFraction);
    timerCircle.style.strokeDashoffset = dashOffset;
    if (timerDisplay) {
      timerDisplay.textContent = formatTimerString(remainingSeconds);
    }
  }

  function startRestTimer() {
    if (isTimerRunning) return;
    if (remainingSeconds <= 0) {
      remainingSeconds = totalRestSeconds;
    }
    isTimerRunning = true;
    if (startBtn) startBtn.style.display = 'none';
    if (pauseBtn) pauseBtn.style.display = 'inline-flex';

    timerInterval = setInterval(() => {
      remainingSeconds--;
      updateTimerCircle();

      if (remainingSeconds <= 0) {
        clearInterval(timerInterval);
        isTimerRunning = false;
        if (pauseBtn) pauseBtn.style.display = 'none';
        if (startBtn) startBtn.style.display = 'inline-flex';
        FitBuddy.toast('⏱ Rest period complete! Ready for your next set.', 'success', 4000);
      }
    }, 1000);
  }

  function pauseRestTimer() {
    isTimerRunning = false;
    clearInterval(timerInterval);
    if (pauseBtn) pauseBtn.style.display = 'none';
    if (startBtn) startBtn.style.display = 'inline-flex';
  }

  function resetRestTimer() {
    isTimerRunning = false;
    clearInterval(timerInterval);
    remainingSeconds = totalRestSeconds;
    updateTimerCircle();
    if (pauseBtn) pauseBtn.style.display = 'none';
    if (startBtn) startBtn.style.display = 'inline-flex';
  }

  if (startBtn) startBtn.addEventListener('click', startRestTimer);
  if (pauseBtn) pauseBtn.addEventListener('click', pauseRestTimer);
  if (resetBtn) resetBtn.addEventListener('click', resetRestTimer);

  if (customTimerBtn) {
    customTimerBtn.addEventListener('click', async () => {
      pauseRestTimer();
      const customSeconds = prompt('Enter rest duration in seconds (e.g., 30, 45, 60, 90, 120):', totalRestSeconds.toString());
      if (customSeconds && !isNaN(parseInt(customSeconds))) {
        totalRestSeconds = Math.max(5, Math.min(600, parseInt(customSeconds)));
        remainingSeconds = totalRestSeconds;
        if (durationText) durationText.textContent = `${totalRestSeconds} seconds`;
        resetRestTimer();
        FitBuddy.toast(`Rest timer set to ${totalRestSeconds} seconds`, 'info', 2000);
      }
    });
  }

  // Initialize dial
  updateTimerCircle();

  // ============================================================
  // 2. EXERCISE CHECKLIST & PROGRESS SYNCHRONIZATION
  // ============================================================
  const exerciseCards = document.querySelectorAll('.exercise-card-modern');
  const counterCompleted = document.getElementById('counter-completed-num');
  const counterPercent = document.getElementById('counter-percent-num');
  const summaryCompleted = document.getElementById('summary-completed-count');
  const summaryPercent = document.getElementById('summary-progress-percent');
  const progressBarFill = document.getElementById('summary-progress-bar-fill');
  const statusTag = document.getElementById('workout-summary-status-tag');
  const markCompleteBtn = document.getElementById('mark-day-complete-btn');

  function updateProgressUI() {
    const total = exerciseCards.length;
    if (total === 0) return;

    let completedCount = 0;
    exerciseCards.forEach(card => {
      if (card.classList.contains('is-checked')) {
        completedCount++;
      }
    });

    const percent = Math.round((completedCount / total) * 100);

    if (counterCompleted) counterCompleted.textContent = completedCount;
    if (counterPercent) counterPercent.textContent = `${percent}%`;
    if (summaryCompleted) summaryCompleted.textContent = completedCount;
    if (summaryPercent) summaryPercent.textContent = `${percent}%`;
    if (progressBarFill) progressBarFill.style.width = `${percent}%`;

    const isAllDone = (completedCount === total && total > 0);
    if (statusTag) {
      if (isAllDone || (markCompleteBtn && markCompleteBtn.getAttribute('data-completed') === 'true')) {
        statusTag.textContent = 'Completed';
        statusTag.className = 'workout-summary-status-pill status-pill-completed';
      } else {
        statusTag.textContent = 'In Progress';
        statusTag.className = 'workout-summary-status-pill status-pill-in-progress';
      }
    }

    if (markCompleteBtn) {
      if (isAllDone || markCompleteBtn.getAttribute('data-completed') === 'true') {
        markCompleteBtn.innerHTML = '<span>✓</span> Workout Completed';
        markCompleteBtn.classList.add('is-completed');
      } else {
        markCompleteBtn.innerHTML = '<span>✓</span> Mark Workout Complete';
        markCompleteBtn.classList.remove('is-completed');
      }
    }
  }

  async function syncWorkoutProgress(showToast = true) {
    const completedExercises = [];
    exerciseCards.forEach(card => {
      if (card.classList.contains('is-checked')) {
        const exName = card.getAttribute('data-exercise-name');
        if (exName) completedExercises.push(exName);
      }
    });

    const isDone = (completedExercises.length === exerciseCards.length && exerciseCards.length > 0) ||
                   (markCompleteBtn && markCompleteBtn.getAttribute('data-completed') === 'true');

    const notesEl = document.getElementById('workout-session-notes');
    const notes = notesEl ? notesEl.value : '';

    try {
      await FitBuddy.api('/api/workouts/log-day', {
        method: 'POST',
        body: JSON.stringify({
          plan_id: planId,
          user_id: userId,
          day_number: dayNumber,
          completed: isDone,
          completed_exercises: completedExercises,
          duration_minutes: 45,
          notes: notes
        })
      });

      if (showToast) {
        FitBuddy.toast(`Progress saved (${completedExercises.length}/${exerciseCards.length} exercises)`, 'success', 1800);
      }
    } catch (err) {
      console.error('Failed to sync workout log:', err);
    }
  }

  // Setup click listeners on exercise cards
  exerciseCards.forEach(card => {
    const checkBtn = card.querySelector('.exercise-checkbox-btn');
    const mainRow = card.querySelector('.exercise-card-main-row');
    const chevron = card.querySelector('.exercise-expand-chevron');

    if (checkBtn) {
      checkBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        card.classList.toggle('is-checked');
        const isChecked = card.classList.contains('is-checked');
        checkBtn.textContent = isChecked ? '✓' : '';
        updateProgressUI();
        syncWorkoutProgress();
      });
    }

    if (chevron) {
      chevron.addEventListener('click', (e) => {
        e.stopPropagation();
        card.classList.toggle('expanded');
      });
    }

    if (mainRow) {
      mainRow.addEventListener('click', (e) => {
        if (e.target === checkBtn || e.target === chevron) return;
        card.classList.toggle('expanded');
      });
    }
  });

  // Expand / Collapse All button
  const toggleExpandAllBtn = document.getElementById('toggle-expand-all-btn');
  let allExpanded = false;
  if (toggleExpandAllBtn) {
    toggleExpandAllBtn.addEventListener('click', () => {
      allExpanded = !allExpanded;
      exerciseCards.forEach(card => {
        if (allExpanded) {
          card.classList.add('expanded');
        } else {
          card.classList.remove('expanded');
        }
      });
      toggleExpandAllBtn.innerHTML = allExpanded ? '<span>⤡</span> Collapse All' : '<span>⤢</span> Expand All';
    });
  }

  // Mark Workout Complete Button
  if (markCompleteBtn) {
    markCompleteBtn.addEventListener('click', async () => {
      exerciseCards.forEach(card => {
        card.classList.add('is-checked');
        const checkBtn = card.querySelector('.exercise-checkbox-btn');
        if (checkBtn) checkBtn.textContent = '✓';
      });
      markCompleteBtn.setAttribute('data-completed', 'true');
      updateProgressUI();
      await syncWorkoutProgress(false);
      FitBuddy.toast('🎉 Great job! Workout marked as complete.', 'success', 3500);
    });
  }

  // Initial Progress UI calculation
  updateProgressUI();

  // ============================================================
  // 3. PERSONAL NOTES CHARACTER COUNTER & SAVE
  // ============================================================
  const notesTextarea = document.getElementById('workout-session-notes');
  const notesCharCounter = document.getElementById('notes-char-counter');
  const btnSaveNotes = document.getElementById('btn-save-notes');

  function updateCharCount() {
    if (!notesTextarea || !notesCharCounter) return;
    const len = notesTextarea.value.length;
    notesCharCounter.textContent = `${len}/500`;
  }

  if (notesTextarea) {
    notesTextarea.addEventListener('input', updateCharCount);
    updateCharCount();
  }

  if (btnSaveNotes) {
    btnSaveNotes.addEventListener('click', async () => {
      await syncWorkoutProgress(false);
      FitBuddy.toast('📝 Personal notes saved successfully!', 'success', 2000);
    });
  }

  // ============================================================
  // 4. SUB-TABS INTERACTIVE SWITCHING
  // ============================================================
  const subtabBtns = document.querySelectorAll('.workout-subtab-btn');
  const exercisesContainer = document.getElementById('exercises-container');
  const tabDetailsContent = document.getElementById('tab-details-content');
  const tabTipsContent = document.getElementById('tab-tips-content');
  const tabMusclesContent = document.getElementById('tab-muscles-content');

  subtabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      subtabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const target = btn.getAttribute('data-tab-target');

      // Hide all panels
      if (exercisesContainer) exercisesContainer.style.display = 'none';
      if (tabDetailsContent) tabDetailsContent.style.display = 'none';
      if (tabTipsContent) tabTipsContent.style.display = 'none';
      if (tabMusclesContent) tabMusclesContent.style.display = 'none';

      if (target === 'tab-workout' && exercisesContainer) {
        exercisesContainer.style.display = 'flex';
      } else if (target === 'tab-details' && tabDetailsContent) {
        tabDetailsContent.style.display = 'block';
      } else if (target === 'tab-tips' && tabTipsContent) {
        tabTipsContent.style.display = 'block';
      } else if (target === 'tab-muscles' && tabMusclesContent) {
        tabMusclesContent.style.display = 'block';
      }
    });
  });
});
