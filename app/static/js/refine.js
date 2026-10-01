/**
 * FitBuddy Plan Refinement Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  const selectedTags = new Set();
  const pills = document.querySelectorAll('.quick-tag-pill');
  const textarea = document.getElementById('refine-feedback-textarea');
  const submitBtn = document.getElementById('submit-refine-btn');
  const container = document.getElementById('refine-container');

  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      const tag = pill.getAttribute('data-tag');
      if (selectedTags.has(tag)) {
        selectedTags.delete(tag);
        pill.classList.remove('selected');
      } else {
        selectedTags.add(tag);
        pill.classList.add('selected');
      }
    });
  });

  if (submitBtn && container) {
    submitBtn.addEventListener('click', () => {
      const feedback = textarea.value.trim();
      const tagsArray = Array.from(selectedTags);

      if (!feedback && tagsArray.length === 0) {
        FitBuddy.toast('Please select at least one quick tag or enter your custom modification request.', 'error');
        textarea.focus();
        return;
      }

      const userId = container.getAttribute('data-user-id');
      const planId = container.getAttribute('data-plan-id');

      // Construct prompt text
      const fullFeedback = feedback || `Please modify plan: ${tagsArray.join(', ')}`;
      const tagsParam = encodeURIComponent(tagsArray.join(','));
      const feedbackParam = encodeURIComponent(fullFeedback);

      // Redirect to generation screen with refinement flags
      window.location.href = `/generating?user_id=${userId}&plan_id=${planId}&is_refinement=true&feedback=${feedbackParam}&quick_tags=${tagsParam}`;
    });
  }
});
