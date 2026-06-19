// ── APP SHELL ─────────────────────────────────────────────────────────────

let _mode = 'home';

const MODE_LABELS = { career: 'Career', academic: 'Academic', self: 'Self-Learn' };
const MODE_SUBTITLES = {
  career: 'Land the role. Grow beyond it.',
  academic: 'Measure understanding, not exposure.',
  self: 'Curiosity-driven. Reflection-first.'
};
// First view to show when entering each mode
const MODE_DEFAULT_VIEW = { career: 'jd-analysis', academic: 'acad-session', self: 'self-session' };

function showMode(mode) {
  _mode = mode;

  document.querySelectorAll('.mode-btn').forEach(b => b.className = 'mode-btn');
  document.querySelectorAll('.sidebar-nav').forEach(n => n.classList.add('hidden'));

  if (mode === 'home') {
    document.documentElement.style.setProperty('--mode', 'var(--career)');
    document.documentElement.style.setProperty('--mode-d', 'var(--career-d)');
    document.documentElement.style.setProperty('--mode-b', 'var(--career-b)');
    document.getElementById('modeWordmark').innerHTML = `MetaLearn<span>Choose a mode to begin</span>`;
    document.querySelector('.rail-logo').style.background = '';
    showView('home');
    return;
  }

  document.getElementById('btn-' + mode).className = `mode-btn active-${mode}`;
  document.getElementById('nav-' + mode)?.classList.remove('hidden');

  // Wire mode CSS vars — academic uses 'acad-*' var names internally
  const varPrefix = mode === 'academic' ? 'acad' : mode;
  document.documentElement.style.setProperty('--mode', `var(--${mode})`);
  document.documentElement.style.setProperty('--mode-d', `var(--${varPrefix}-d)`);
  document.documentElement.style.setProperty('--mode-b', `var(--${varPrefix}-b)`);

  document.getElementById('modeWordmark').innerHTML = `${MODE_LABELS[mode]}<span>${MODE_SUBTITLES[mode]}</span>`;
  document.querySelector('.rail-logo').style.background = `var(--${mode})`;

  showView(MODE_DEFAULT_VIEW[mode]);
}

function showView(name) {
  document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
  const el = document.getElementById('view-' + name);
  if (!el) { console.warn('View not found:', name); return; }
  el.classList.add('active');

  document.querySelectorAll('.nav-item').forEach(n => {
    n.classList.remove('active-career', 'active-academic', 'active-self');
  });
  const navEl = document.querySelector(`.nav-item[data-view="${name}"]`);
  if (navEl) navEl.classList.add(`active-${_mode}`);
}

// ── Init ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initChips();
  renderJournal();
  showMode('home');
});