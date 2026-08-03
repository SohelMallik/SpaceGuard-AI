/**
 * SpaceGuard AI — Mission Assistant Chat Interface
 */

/**
 * Send a message to the AI Mission Assistant.
 * @param {number} missionId
 */
function sendMessage(missionId) {
  const input = document.getElementById('chatInput');
  const history = document.getElementById('chatHistory');
  if (!input || !history) return;

  const question = input.value.trim();
  if (!question) return;

  // Append user message
  appendMessage(history, question, 'user');
  input.value = '';

  // Show typing indicator
  const typingId = 'typing-' + Date.now();
  history.insertAdjacentHTML('beforeend',
    `<div id="${typingId}" class="chat-msg assistant text-muted fst-italic">SpaceGuard AI is thinking...</div>`
  );
  history.scrollTop = history.scrollHeight;

  fetch(`/api/missions/${missionId}/assistant/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({ question }),
  })
  .then(r => r.json())
  .then(data => {
    const el = document.getElementById(typingId);
    if (el) el.remove();

    const answer = data.answer || 'No response received.';
    const source = data.source || 'SpaceGuard AI';
    appendMessage(history, answer, 'assistant', source);
  })
  .catch(err => {
    const el = document.getElementById(typingId);
    if (el) el.remove();
    appendMessage(history, 'Unable to reach the AI assistant. Please check your connection.', 'assistant', 'System');
    console.error('Assistant error:', err);
  });
}

function appendMessage(container, text, role, source) {
  const prefix = role === 'assistant'
    ? `<strong>${source || 'SpaceGuard AI'}</strong><br>`
    : '';
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  div.innerHTML = prefix + escapeHtml(text);
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Allow Enter key to send message
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('chatInput');
  if (input) {
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const missionId = typeof MISSION_ID !== 'undefined' ? MISSION_ID : null;
        if (missionId) sendMessage(missionId);
      }
    });
  }
});
