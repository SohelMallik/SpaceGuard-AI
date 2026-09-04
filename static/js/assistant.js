/**
 * SpaceGuard AI — Mission Assistant Chat Interface
 * Structured Problem → Why → How responses using live telemetry
 */

const QUICK_PROMPTS = [
  { label: '🔍 What\'s wrong?',      text: 'What is wrong with the spacecraft?' },
  { label: '🏥 Health status',       text: 'What is the health status?' },
  { label: '⚠ Explain anomaly',     text: 'Explain the anomaly' },
  { label: '🔋 Battery & power',     text: 'Check battery and power status' },
  { label: '🌡 Temperature',         text: 'What is the temperature status?' },
  { label: '📡 Signal strength',     text: 'Check signal strength' },
  { label: '🚀 Fuel level',          text: 'What is the fuel level?' },
  { label: '☢ Radiation',           text: 'What is the radiation level?' },
  { label: '☀ Space weather',       text: 'What is the space weather risk?' },
  { label: '🔔 Active alerts',       text: 'Are there any active alerts?' },
  { label: '📊 Full diagnostic',     text: 'Show full diagnostic report' },
  { label: '📋 All readings',        text: 'Show all telemetry readings' },
];

/**
 * Build and inject the suggestion chips bar.
 * Called once on DOM ready.
 */
function initSuggestionChips(missionId) {
  const container = document.getElementById('chatSuggestions');
  if (!container) return;
  QUICK_PROMPTS.forEach(p => {
    const btn = document.createElement('button');
    btn.className = 'chip-btn';
    btn.textContent = p.label;
    btn.title = p.text;
    btn.addEventListener('click', () => {
      const input = document.getElementById('chatInput');
      if (input) input.value = p.text;
      sendMessage(missionId);
    });
    container.appendChild(btn);
  });
}

/**
 * Send a message to the AI Mission Assistant.
 */
function sendMessage(missionId) {
  const input   = document.getElementById('chatInput');
  const history = document.getElementById('chatHistory');
  if (!input || !history) return;

  const question = input.value.trim();
  if (!question) return;

  appendMessage(history, question, 'user');
  input.value = '';

  // Typing indicator
  const typingId = 'typing-' + Date.now();
  history.insertAdjacentHTML('beforeend',
    `<div id="${typingId}" class="chat-msg assistant typing-indicator">
       <span></span><span></span><span></span>
     </div>`
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
    const source = data.source  || 'SpaceGuard AI';
    appendMessage(history, answer, 'assistant', source);
  })
  .catch(err => {
    const el = document.getElementById(typingId);
    if (el) el.remove();
    appendMessage(history,
      '⚠ Unable to reach the AI assistant. Please check your connection.',
      'assistant', 'System');
    console.error('Assistant error:', err);
  });
}

/**
 * Append a chat bubble to the history container.
 */
function appendMessage(container, text, role, source) {
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;

  if (role === 'assistant') {
    const header = document.createElement('div');
    header.className = 'chat-msg-header';
    header.innerHTML = `<span class="chat-source">${escapeHtml(source || 'SpaceGuard AI')}</span>`;
    div.appendChild(header);
  }

  const body = document.createElement('div');
  body.className = 'chat-msg-body';
  body.innerHTML = formatText(text);
  div.appendChild(body);

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

/**
 * Convert plain text with markdown-lite to HTML.
 * Handles **bold**, section headers (🔍/❓/✅), numbered lists, bullet lists.
 */
function formatText(text) {
  let s = escapeHtml(text);

  // Section labels → styled spans
  s = s.replace(/\*\*(🔍 PROBLEM[^*]*)\*\*/g,   '<span class="ai-label ai-problem">$1</span>');
  s = s.replace(/\*\*(❓ WHY[^*]*)\*\*/g,        '<span class="ai-label ai-why">$1</span>');
  s = s.replace(/\*\*(✅ HOW TO FIX[^*]*)\*\*/g, '<span class="ai-label ai-fix">$1</span>');
  s = s.replace(/\*\*(✅ HOW TO FIX IT[^*]*)\*\*/g, '<span class="ai-label ai-fix">$1</span>');
  s = s.replace(/\*\*(✅ IMMEDIATE ACTIONS[^*]*)\*\*/g, '<span class="ai-label ai-fix">$1</span>');

  // Status labels
  s = s.replace(/🔴 CRITICAL/g, '<span class="ai-critical">🔴 CRITICAL</span>');
  s = s.replace(/⚠ WARNING/g,   '<span class="ai-warning">⚠ WARNING</span>');
  s = s.replace(/✓ Normal/g,    '<span class="ai-normal">✓ Normal</span>');

  // Remaining **bold**
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // Horizontal rule
  s = s.replace(/^---$/gm, '<hr class="chat-hr">');

  // Numbered list items (with 4-space indent = inside a fix block)
  s = s.replace(/^ {4}(\d+)\. (.+)$/gm, '<div class="chat-step"><span class="step-num">$1</span><span class="step-text">$2</span></div>');
  // Numbered list items (normal indent)
  s = s.replace(/^(\d+)\. (.+)$/gm, '<div class="chat-step"><span class="step-num">$1</span><span class="step-text">$2</span></div>');

  // Bullet points
  s = s.replace(/^• (.+)$/gm, '<div class="chat-bullet">• $1</div>');
  s = s.replace(/^\* (.+)$/gm, '<div class="chat-bullet">• $1</div>');

  // Italic *text*
  s = s.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Newlines → <br>
  s = s.replace(/\n/g, '<br>');

  return s;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function getCookie(name) {
  const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
  return v ? v[2] : null;
}

// ── Keyboard shortcut: Enter to send ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const missionId = typeof MISSION_ID !== 'undefined' ? MISSION_ID : null;

  const input = document.getElementById('chatInput');
  if (input) {
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (missionId) sendMessage(missionId);
      }
    });
  }

  if (missionId) initSuggestionChips(missionId);
});
