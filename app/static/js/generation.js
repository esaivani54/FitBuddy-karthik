/**
 * FitBuddy AI Generation Controller
 * Provides realistic progress animation and manages backend AI orchestration.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const container = document.getElementById('generation-container');
  const userId = parseInt(container.getAttribute('data-user-id'));
  const planId = parseInt(container.getAttribute('data-plan-id')) || null;
  const isRefinement = container.getAttribute('data-is-refinement') === 'true';
  const feedback = container.getAttribute('data-feedback') || '';
  const quickTags = container.getAttribute('data-quick-tags') ? container.getAttribute('data-quick-tags').split(',') : [];

  const stageList = [
    { title: "Analyzing physiological metrics & goals", desc: "Processing bodyweight, recovery capacity, and target focus." },
    { title: "Structuring 7-day periodized schedule", desc: "Optimizing push, pull, legs, and active restoration days." },
    { title: "Calibrating volume, rep tempos & sets", desc: "Aligning exercise selection with specified intensity tier." },
    { title: "Compiling nutrition & recovery protocols", desc: "Generating macro splits, hydration targets, and sleep guidelines." },
    { title: "Finalizing your FitBuddy blueprint", desc: "Packaging your custom plan for immediate action." }
  ];

  const statusText = document.getElementById('generation-status-text');
  const statusDesc = document.getElementById('generation-status-desc');
  const progressBar = document.getElementById('generation-progress-fill');
  const stageItems = document.querySelectorAll('.gen-stage-item');

  let currentStage = 0;

  function updateStageUI(index) {
    if (index >= stageList.length) return;
    const stage = stageList[index];
    if (statusText) statusText.textContent = stage.title;
    if (statusDesc) statusDesc.textContent = stage.desc;
    if (progressBar) progressBar.style.width = `${((index + 1) / stageList.length) * 90}%`;

    stageItems.forEach((el, i) => {
      if (i < index) {
        el.className = 'gen-stage-item completed';
        el.querySelector('.gen-stage-icon').textContent = '✓';
      } else if (i === index) {
        el.className = 'gen-stage-item active';
        el.querySelector('.gen-stage-icon').innerHTML = '<span class="spinner spinner-primary" style="width: 1rem; height: 1rem;"></span>';
      } else {
        el.className = 'gen-stage-item pending';
        el.querySelector('.gen-stage-icon').textContent = `${i + 1}`;
      }
    });
  }

  // Stage animation interval
  const stageInterval = setInterval(() => {
    if (currentStage < stageList.length - 1) {
      currentStage++;
      updateStageUI(currentStage);
    }
  }, 900);

  try {
    let result;
    if (isRefinement && planId) {
      // Regeneration API Call
      result = await FitBuddy.api('/api/workouts/feedback', {
        method: 'POST',
        body: JSON.stringify({
          user_id: userId,
          plan_id: planId,
          feedback: feedback,
          quick_tags: quickTags
        })
      });
    } else {
      // Initial Generation API Call
      result = await FitBuddy.api('/api/workouts/generate', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId })
      });
    }

    clearInterval(stageInterval);
    if (progressBar) progressBar.style.width = '100%';
    if (statusText) statusText.textContent = 'Plan Ready!';
    if (statusDesc) statusDesc.textContent = 'Redirecting to your dashboard...';

    // Mark all stages complete
    stageItems.forEach(el => {
      el.className = 'gen-stage-item completed';
      el.querySelector('.gen-stage-icon').textContent = '✓';
    });

    setTimeout(() => {
      window.location.href = `/dashboard?user_id=${userId}`;
    }, 800);

  } catch (error) {
    clearInterval(stageInterval);
    console.error('Generation failure:', error);
    
    // Display error state
    document.getElementById('generation-active-box').style.display = 'none';
    const errorBox = document.getElementById('generation-error-box');
    if (errorBox) {
      errorBox.style.display = 'block';
      document.getElementById('generation-error-message').textContent = error.message || 'An error occurred while generating the plan.';
    }
  }
});
