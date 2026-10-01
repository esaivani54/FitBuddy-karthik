/**
 * FitBuddy Premium Realtime AI Fitness Coach Chat Controller
 * Manages floating launcher, spacious popup, size expand/collapse, clear history, and context sync.
 */

document.addEventListener('DOMContentLoaded', () => {
  const triggerBtn = document.getElementById('chatFloatingTrigger');
  const popupWindow = document.getElementById('chatPopupWindow');
  const closeBtn = document.getElementById('chatCloseBtn');
  const expandBtn = document.getElementById('chatExpandBtn');
  const clearBtn = document.getElementById('chatClearBtn');
  const inputField = document.getElementById('chatInputField');
  const sendBtn = document.getElementById('chatSendBtn');
  const messagesContainer = document.getElementById('chatMessagesContainer');
  const quickChips = document.querySelectorAll('.chat-suggestion-chip');
  const coachSubtitle = document.getElementById('chatCoachSubtitle');

  if (!triggerBtn || !popupWindow) return;

  // Retrieve current active user ID from URL or window
  function getActiveUserId() {
    const urlParams = new URLSearchParams(window.location.search);
    const userIdFromUrl = urlParams.get('user_id');
    if (userIdFromUrl) return parseInt(userIdFromUrl);

    const datasetEl = document.querySelector('[data-user-id]');
    if (datasetEl && datasetEl.getAttribute('data-user-id')) {
      return parseInt(datasetEl.getAttribute('data-user-id'));
    }

    return null;
  }

  // State
  let history = [];
  const currentUserId = getActiveUserId();
  const storageKey = `fitbuddy_chat_history_${currentUserId || 'guest'}`;

  // Load saved history if available
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      history = JSON.parse(saved);
    }
  } catch (e) {
    console.warn('Could not read chat history from storage', e);
  }

  // Toggle Popup
  function openChat() {
    popupWindow.classList.add('active');
    triggerBtn.style.display = 'none';
    if (inputField) inputField.focus();
    scrollToBottom();
  }

  function closeChat() {
    popupWindow.classList.remove('active');
    triggerBtn.style.display = 'flex';
  }

  function toggleExpand() {
    popupWindow.classList.toggle('expanded');
    if (expandBtn) {
      expandBtn.textContent = popupWindow.classList.contains('expanded') ? '🗗' : '⛶';
      expandBtn.title = popupWindow.classList.contains('expanded') ? 'Restore Standard Size' : 'Expand Size';
    }
    scrollToBottom();
  }

  async function clearConversation() {
    const confirmed = await FitBuddy.confirm({
      title: 'Clear Chat History?',
      message: 'Are you sure you want to reset your conversation with FitBuddy AI Coach?',
      confirmText: 'Clear History',
      confirmVariant: 'danger',
      icon: '🗑️'
    });

    if (confirmed) {
      history = [];
      try {
        localStorage.removeItem(storageKey);
      } catch (e) {
        console.warn('Could not remove history from storage', e);
      }
      if (currentUserId) {
        try {
          await fetch(`/api/chat/history?user_id=${currentUserId}`, { method: 'DELETE' });
        } catch (e) {
          console.warn('Failed to delete remote chat history', e);
        }
      }
      if (messagesContainer) {
        messagesContainer.innerHTML = `
          <div class="chat-message-row assistant-row">
            <div class="chat-bubble-avatar">⚡</div>
            <div>
              <div class="chat-bubble">
                <p>Conversation reset! 👋 What would you like to discuss about your workouts, nutrition, or recovery?</p>
              </div>
              <div class="chat-message-time">Just now</div>
            </div>
          </div>
        `;
      }
      FitBuddy.toast('Chat history cleared', 'info');
    }
  }

  triggerBtn.addEventListener('click', openChat);
  if (closeBtn) closeBtn.addEventListener('click', closeChat);
  if (expandBtn) expandBtn.addEventListener('click', toggleExpand);
  if (clearBtn) clearBtn.addEventListener('click', clearConversation);

  // Markdown Formatter Helper
  function formatMessageText(text) {
    if (!text) return '';
    
    // Escape basic HTML
    let safe = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Bold **text**
    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Italic *text*
    safe = safe.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Bullet points (• or -)
    const lines = safe.split('\n');
    let inList = false;
    let formattedLines = [];

    lines.forEach(line => {
      const trimmed = line.trim();
      if (trimmed.startsWith('•') || trimmed.startsWith('-')) {
        if (!inList) {
          formattedLines.push('<ul>');
          inList = true;
        }
        formattedLines.push(`<li>${trimmed.substring(1).trim()}</li>`);
      } else {
        if (inList) {
          formattedLines.push('</ul>');
          inList = false;
        }
        if (trimmed.length > 0) {
          formattedLines.push(`<p>${trimmed}</p>`);
        }
      }
    });

    if (inList) {
      formattedLines.push('</ul>');
    }

    return formattedLines.join('');
  }

  function scrollToBottom() {
    if (messagesContainer) {
      setTimeout(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }, 10);
    }
  }

  function appendMessageUI(role, content, timeStr) {
    const row = document.createElement('div');
    row.className = `chat-message-row ${role === 'user' ? 'user-row' : 'assistant-row'}`;
    
    const nowTime = timeStr || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (role === 'assistant') {
      row.innerHTML = `
        <div class="chat-bubble-avatar">⚡</div>
        <div>
          <div class="chat-bubble">
            ${formatMessageText(content)}
          </div>
          <div class="chat-message-time">${nowTime}</div>
        </div>
      `;
    } else {
      row.innerHTML = `
        <div>
          <div class="chat-bubble">
            ${formatMessageText(content)}
          </div>
          <div class="chat-message-time">${nowTime}</div>
        </div>
      `;
    }

    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  // Render initial history if present
  if (history && history.length > 0) {
    history.forEach(item => appendMessageUI(item.role, item.content, item.time));
  }

  // Show Typing Indicator
  let typingIndicatorEl = null;

  function showTyping() {
    if (typingIndicatorEl) return;
    typingIndicatorEl = document.createElement('div');
    typingIndicatorEl.className = 'chat-message-row assistant-row';
    typingIndicatorEl.id = 'chatTypingIndicatorRow';
    typingIndicatorEl.innerHTML = `
      <div class="chat-bubble-avatar chat-avatar-pulse">⚡</div>
      <div class="chat-typing-indicator">
        <span class="chat-typing-label">Coach is checking your plan</span>
        <div class="chat-typing-dots">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    `;
    messagesContainer.appendChild(typingIndicatorEl);
    scrollToBottom();
  }

  function hideTyping() {
    if (typingIndicatorEl) {
      typingIndicatorEl.remove();
      typingIndicatorEl = null;
    }
  }

  // Send Message
  async function sendMessage(text) {
    const msg = (text || (inputField ? inputField.value : '')).trim();
    if (!msg) return;

    if (inputField) {
      inputField.value = '';
    }

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Append to UI & memory
    appendMessageUI('user', msg, timeStr);
    history.push({ role: 'user', content: msg, time: timeStr });

    showTyping();
    if (sendBtn) sendBtn.disabled = true;

    try {
      const response = await FitBuddy.api('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          user_id: currentUserId,
          message: msg,
          history: history.slice(-6).map(h => ({ role: h.role, content: h.content }))
        })
      });

      hideTyping();

      const aiTimeStr = response.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      appendMessageUI('assistant', response.response, aiTimeStr);
      history.push({ role: 'assistant', content: response.response, time: aiTimeStr });

      // Update subtitle if user context received
      if (coachSubtitle && response.user_name) {
        coachSubtitle.textContent = `Online · ${response.user_name}${response.plan_version ? ` (Plan v${response.plan_version})` : ''}`;
      }

      // Save to localStorage (keep last 25 messages)
      try {
        localStorage.setItem(storageKey, JSON.stringify(history.slice(-25)));
      } catch (err) {
        console.warn('Could not save chat history to storage', err);
      }

    } catch (err) {
      hideTyping();
      appendMessageUI('assistant', 'Sorry, I encountered an issue connecting with the AI service. Please verify your connection or try again.');
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      if (inputField) inputField.focus();
    }
  }

  if (sendBtn) {
    sendBtn.addEventListener('click', () => sendMessage());
  }

  if (inputField) {
    inputField.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // Quick chips
  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt') || chip.textContent;
      sendMessage(prompt);
    });
  });
});
