/**
 * FitBuddy Simplified Beginner-Friendly Onboarding Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  let currentStep = 1;
  const totalSteps = 4;

  const state = {
    name: '',
    age: '',
    weight: '',
    gender: 'Male',
    height: 175,
    goal: 'Weight Loss',
    intensity: 'Medium',
    experience: 'Beginner',
    equipment: 'Full Gym'
  };

  const prevBtn = document.getElementById('prevStepBtn');
  const nextBtn = document.getElementById('nextStepBtn');
  const submitBtn = document.getElementById('submitOnboardBtn');

  // Goal Cards Selection
  const goalCards = document.querySelectorAll('.goal-card');
  goalCards.forEach(card => {
    card.addEventListener('click', () => {
      goalCards.forEach(c => {
        c.style.border = '2px solid var(--border-color)';
        c.style.background = '#ffffff';
        const check = c.querySelector('span:last-child');
        if (check) check.style.display = 'none';
      });

      card.style.border = '2px solid var(--primary)';
      card.style.background = 'var(--primary-surface)';
      const currentCheck = card.querySelector('span:last-child');
      if (currentCheck) currentCheck.style.display = 'inline';

      state.goal = card.getAttribute('data-goal');
    });
  });

  // Intensity Cards Selection
  const intensityCards = document.querySelectorAll('.intensity-card');
  intensityCards.forEach(card => {
    card.addEventListener('click', () => {
      intensityCards.forEach(c => {
        c.style.border = '2px solid var(--border-color)';
        c.style.background = '#ffffff';
      });

      card.style.border = '2px solid var(--primary)';
      card.style.background = 'var(--primary-surface)';
      state.intensity = card.getAttribute('data-intensity');
    });
  });

  function updateStepUI() {
    for (let i = 1; i <= totalSteps; i++) {
      const pane = document.getElementById(`wizard-step-${i}`);
      if (pane) {
        pane.style.display = i === currentStep ? 'block' : 'none';
      }
    }

    if (prevBtn) prevBtn.style.display = currentStep > 1 ? 'inline-flex' : 'none';
    if (nextBtn) nextBtn.style.display = currentStep < totalSteps ? 'inline-flex' : 'none';
    if (submitBtn) submitBtn.style.display = currentStep === totalSteps ? 'inline-flex' : 'none';

    if (currentStep === 4) {
      const nameEl = document.getElementById('summary-name');
      const ageEl = document.getElementById('summary-age');
      const weightEl = document.getElementById('summary-weight');
      const heightEl = document.getElementById('summary-height');
      const goalEl = document.getElementById('summary-goal');
      const intensityEl = document.getElementById('summary-intensity');
      const equipmentEl = document.getElementById('summary-equipment');

      if (nameEl) nameEl.textContent = state.name || 'Friend';
      if (ageEl) ageEl.textContent = `${state.age} yrs`;
      if (weightEl) weightEl.textContent = `${state.weight} kg`;
      if (heightEl) heightEl.textContent = `${state.height || 175} cm`;
      if (goalEl) goalEl.textContent = state.goal;
      if (intensityEl) {
        const freq = state.intensity === 'Low' ? '3 days/wk' : (state.intensity === 'High' ? '5 days/wk' : '4 days/wk');
        intensityEl.textContent = `${state.intensity} (${freq})`;
      }
      if (equipmentEl) equipmentEl.textContent = state.equipment;
    }
  }

  function validateStep(step) {
    if (step === 1) {
      const name = document.getElementById('input-name').value.trim();
      const age = parseInt(document.getElementById('input-age').value);
      const weight = parseFloat(document.getElementById('input-weight').value);
      const height = parseFloat(document.getElementById('input-height').value) || 175;
      const gender = document.getElementById('input-gender').value;
      const equipment = document.getElementById('input-equipment').value;

      if (!name || name.length < 2) {
        FitBuddy.toast('Please enter your full name', 'error');
        document.getElementById('input-name').focus();
        return false;
      }
      if (!age || isNaN(age) || age < 12 || age > 100) {
        FitBuddy.toast('Please enter a valid age between 12 and 100', 'error');
        document.getElementById('input-age').focus();
        return false;
      }
      if (!weight || isNaN(weight) || weight < 30 || weight > 300) {
        FitBuddy.toast('Please enter a valid weight in kg', 'error');
        document.getElementById('input-weight').focus();
        return false;
      }

      state.name = name;
      state.age = age;
      state.weight = weight;
      state.height = height;
      state.gender = gender;
      state.equipment = equipment;
      return true;
    }
    return true;
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (validateStep(currentStep)) {
        currentStep++;
        updateStepUI();
      }
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentStep > 1) {
        currentStep--;
        updateStepUI();
      }
    });
  }

  if (submitBtn) {
    submitBtn.addEventListener('click', async () => {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner"></span> Creating Your Plan...';

      try {
        const user = await FitBuddy.api('/api/users', {
          method: 'POST',
          body: JSON.stringify(state)
        });

        window.location.href = `/generating?user_id=${user.id}`;
      } catch (err) {
        submitBtn.disabled = false;
        submitBtn.textContent = '⚡ Generate My Plan →';
      }
    });
  }

  updateStepUI();
});
