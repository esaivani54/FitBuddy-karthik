/**
 * FitBuddy Dedicated Page AI Coach Chat Controller
 * Loads database history, handles real-time messages, and manages plan change confirmations.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const container = document.querySelector('[data-user-id]');
  const userId = container ? parseInt(container.getAttribute('data-user-id')) : null;
  const messagesContainer = document.getElementById('pageChatMessagesContainer');
  const inputField = document.getElementById('pageChatInputField');
  const sendBtn = document.getElementById('pageChatSendBtn');
  const clearBtn = document.getElementById('pageChatClearBtn');
  const quickChips = document.querySelectorAll('#pageChatSuggestions .chat-suggestion-chip');

  if (!messagesContainer || !inputField) return;

  function scrollToBottom() {
    setTimeout(() => {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 20);
  }

  // Format markdown helper
  function formatMessageText(text) {
    if (!text) return '';
    let safe = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    safe = safe.replace(/\*(.*?)\*/g, '<em>$1</em>');

    const lines = safe.split('\n');
    let inList = false;
    let formatted = [];

    lines.forEach(line => {
      const trimmed = line.trim();
      if (trimmed.startsWith('•') || trimmed.startsWith('-')) {
        if (!inList) {
          formatted.push('<ul>');
          inList = true;
        }
        formatted.push(`<li>${trimmed.substring(1).trim()}</li>`);
      } else {
        if (inList) {
          formatted.push('</ul>');
          inList = false;
        }
        if (trimmed.length > 0) {
          formatted.push(`<p>${trimmed}</p>`);
        }
      }
    });

    if (inList) formatted.push('</ul>');
    return formatted.join('');
  }

  function appendMessage(role, content, timeStr, actionObj = null) {
    const row = document.createElement('div');
    row.className = `chat-message-row ${role === 'user' ? 'user-row' : 'assistant-row'}`;
    const time = timeStr || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    let actionMarkup = '';
    if (actionObj && actionObj.url) {
      actionMarkup = `
        <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--border-light);">
          <a href="${actionObj.url}" class="btn btn-primary btn-sm" style="font-size: 0.825rem;">
            ${actionObj.label || '⚡ Update Plan'}
          </a>
        </div>
      `;
    }

    if (role === 'assistant') {
      row.innerHTML = `
        <div class="chat-bubble-avatar">⚡</div>
        <div>
          <div class="chat-bubble">
            ${formatMessageText(content)}
            ${actionMarkup}
          </div>
          <div class="chat-message-time">${time}</div>
        </div>
      `;
    } else {
      row.innerHTML = `
        <div>
          <div class="chat-bubble">
            ${formatMessageText(content)}
          </div>
          <div class="chat-message-time">${time}</div>
        </div>
      `;
    }

    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  // Load history from database
  try {
    const history = await FitBuddy.api(`/api/chat/history${userId ? `?user_id=${userId}` : ''}`);
    if (history && history.length > 0) {
      history.forEach(m => appendMessage(m.role, m.message, m.created_at));
    }
  } catch (err) {
    console.warn('Could not load chat history', err);
  }

  // Typing indicator
  let typingEl = null;
  function showTyping() {
    if (typingEl) return;
    typingEl = document.createElement('div');
    typingEl.className = 'chat-message-row assistant-row';
    typingEl.innerHTML = `
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
    messagesContainer.appendChild(typingEl);
    scrollToBottom();
  }

  function hideTyping() {
    if (typingEl) {
      typingEl.remove();
      typingEl = null;
    }
  }

  // Send message
  async function sendMessage(text) {
    const msg = (text || inputField.value).trim();
    if (!msg) return;

    inputField.value = '';
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    appendMessage('user', msg, nowTime);

    showTyping();
    if (sendBtn) sendBtn.disabled = true;

    try {
      const resp = await FitBuddy.api('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          user_id: userId,
          message: msg
        })
      });

      hideTyping();
      appendMessage('assistant', resp.response, resp.timestamp, resp.suggested_action);

    } catch (err) {
      hideTyping();
      appendMessage('assistant', 'Sorry, an error occurred while connecting with your coach. Please try again.');
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      inputField.focus();
    }
  }

  if (sendBtn) {
    sendBtn.addEventListener('click', () => sendMessage());
  }

  inputField.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt') || chip.textContent;
      sendMessage(prompt);
    });
  });

  if (clearBtn) {
    clearBtn.addEventListener('click', async () => {
      const confirmed = await FitBuddy.confirm({
        title: 'Clear Conversation?',
        message: 'Are you sure you want to reset your conversation history with your AI Coach?',
        confirmText: 'Clear Chat',
        confirmVariant: 'danger',
        icon: '🗑️'
      });

      if (confirmed) {
        try {
          await FitBuddy.api(`/api/chat/history${userId ? `?user_id=${userId}` : ''}`, { method: 'DELETE' });
          messagesContainer.innerHTML = `
            <div class="chat-message-row assistant-row">
              <div class="chat-bubble-avatar">⚡</div>
              <div>
                <div class="chat-bubble">
                  <p>Chat history cleared! 👋 How can I assist you with your fitness journey today?</p>
                </div>
                <div class="chat-message-time">Just now</div>
              </div>
            </div>
          `;
          FitBuddy.toast('Chat history cleared', 'info');
        } catch (err) {
          console.error(err);
        }
      }
    });
  }
});
