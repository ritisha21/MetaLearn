// ── API & SHARED UTILITIES ────────────────────────────────────────────────

const API_URL = 'https://api.anthropic.com/v1/messages';

function getKey() { return document.getElementById('apiKey').value.trim(); }

function load(msg = 'Thinking...') {
  document.getElementById('loader').classList.remove('hidden');
  document.getElementById('loaderMsg').textContent = msg;
}
function unload() { document.getElementById('loader').classList.add('hidden'); }

async function ai(prompt, system = '', maxTokens = 2000) {
  const key = getKey();
  const body = {
    model: 'claude-sonnet-4-6',
    max_tokens: maxTokens,
    messages: [{ role: 'user', content: prompt }]
  };
  if (system) body.system = system;
  const r = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': key,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true'
    },
    body: JSON.stringify(body)
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(e.error?.message || 'API error ' + r.status);
  }
  const d = await r.json();
  return d.content?.map(b => b.text || '').join('').replace(/```json\s*/g, '').replace(/```\s*/g, '').trim();
}

async function aiStream(messages, system, onToken, onDone) {
  const key = getKey();
  const body = { model: 'claude-sonnet-4-6', max_tokens: 900, stream: true, messages };
  if (system) body.system = system;
  const r = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': key,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true'
    },
    body: JSON.stringify(body)
  });
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    for (const line of dec.decode(value, { stream: true }).split('\n')) {
      if (line.startsWith('data:')) {
        try {
          const d = JSON.parse(line.slice(5).trim());
          if (d.type === 'content_block_delta' && d.delta?.text) {
            buf += d.delta.text;
            onToken(d.delta.text);
          }
        } catch (_) {}
      }
    }
  }
  onDone(buf);
}

// ── DOM UTILITIES ─────────────────────────────────────────────────────────

function autoResize(el) {
  el.style.height = '22px';
  el.style.height = Math.min(el.scrollHeight, 96) + 'px';
}

function resetSect(showId, hideId) {
  document.getElementById(showId).classList.remove('hidden');
  document.getElementById(hideId).classList.add('hidden');
}

function getChip(containerId) {
  return document.querySelector(`#${containerId} .chip.sel`)?.dataset.val || '';
}

function initChips() {
  document.querySelectorAll('.chips').forEach(container => {
    container.addEventListener('click', e => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      container.querySelectorAll('.chip').forEach(c => c.classList.remove('sel'));
      chip.classList.add('sel');
    });
  });
}

function addMsg(containerId, role, text) {
  const c = document.getElementById(containerId);
  const d = document.createElement('div');
  d.className = `msg ${role === 'user' ? 'u' : 'ai'}`;
  d.innerHTML = `<div class="av ${role === 'user' ? 'u' : 'ai'}">${role === 'user' ? 'You' : 'AI'}</div><div class="bbl">${text.replace(/\n/g, '<br>')}</div>`;
  c.appendChild(d);
  c.scrollTop = c.scrollHeight;
  return d;
}

function addTyping(containerId, id) {
  const c = document.getElementById(containerId);
  const d = document.createElement('div');
  d.className = 'msg ai';
  d.id = id;
  d.innerHTML = `<div class="av ai">AI</div><div class="bbl"><div class="dots"><span></span><span></span><span></span></div></div>`;
  c.appendChild(d);
  c.scrollTop = c.scrollHeight;
}

function setStep(ids, activeIdx) {
  ids.forEach((id, i) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = 'step' + (i < activeIdx ? ' done' : i === activeIdx ? ' active' : '');
  });
}

function lvlPct(l) {
  const m = { beginner: 18, junior: 32, intermediate: 50, proficient: 65, advanced: 80, expert: 95 };
  for (const [k, v] of Object.entries(m)) if ((l || '').toLowerCase().includes(k)) return v;
  return 50;
}

function updatePulse(quizScore, preConf, feynScore) {
  const calibration = Math.max(0, 100 - Math.abs(preConf - quizScore));
  document.getElementById('pKnow').style.width = quizScore + '%';
  document.getElementById('pKnowVal').textContent = quizScore;
  document.getElementById('pCalib').style.width = calibration + '%';
  document.getElementById('pCalibVal').textContent = calibration;
  document.getElementById('pRef').style.width = Math.round(feynScore * 100) + '%';
  document.getElementById('pRefVal').textContent = Math.round(feynScore * 100);
  const gap = preConf - quizScore;
  document.getElementById('pulseInsight').textContent =
    Math.abs(gap) <= 10
      ? 'Well calibrated. Confidence matched actual performance.'
      : gap > 10
      ? `Overconfident by ${gap} points. Familiarity ≠ understanding — the core gap MetaLearn tracks.`
      : `Underconfident by ${Math.abs(gap)} points. You know more than you think.`;
}

// Generic streaming chat helper used across modes
async function streamChat(msgsId, history, sys, onHistoryUpdate) {
  document.querySelectorAll('.send-btn').forEach(b => b.disabled = true);
  addTyping(msgsId, 'streamTyping');
  let streamBubble = null;
  try {
    await aiStream(
      history,
      sys,
      tok => {
        const t = document.getElementById('streamTyping');
        if (t) {
          t.remove();
          const msgEl = addMsg(msgsId, 'ai', '');
          streamBubble = msgEl.querySelector('.bbl');
          streamBubble.id = 'streamBub';
        }
        const s = document.getElementById('streamBub');
        if (s) { s.textContent += tok; document.getElementById(msgsId).scrollTop = 9999; }
      },
      full => {
        const s = document.getElementById('streamBub');
        if (s) s.removeAttribute('id');
        const clean = full
          .replace(/\[(META|MISCONCEPTION|DONE)\].*?(?=\n|$)/g, '')
          .replace(/##\w+##/g, '')
          .trim();
        history.push({ role: 'assistant', content: clean });
        onHistoryUpdate(history, full);
      }
    );
  } catch (e) {
    const t = document.getElementById('streamTyping');
    if (t) t.remove();
    addMsg(msgsId, 'ai', '⚠ Error: ' + e.message);
  }
  document.querySelectorAll('.send-btn').forEach(b => b.disabled = false);
}