// ── SELF-LEARN MODULE ─────────────────────────────────────────────────────
// Curiosity-driven, no urgency trigger by design (Son & Metcalfe, 2000 —
// motivation/interest drives study-time allocation more than gap-closing logic).
// Sequenced AFTER Academic in the roadmap so it inherits a warm, retained user
// base rather than needing to create urgency from nothing.

let _selfHistory = [];
let _journalEntries = [];

// ── Curiosity Session ────────────────────────────────────────────────────

async function startSelfSession() {
  const topic = document.getElementById('selfTopic').value.trim();
  if (!topic) { alert('Enter a topic.'); return; }
  const why = document.getElementById('selfWhy').value.trim();
  const prior = document.getElementById('selfPrior').value.trim();
  const depth = getChip('selfDepthChips');

  _selfHistory = [];
  window._selfCurrentTopic = topic;

  document.getElementById('selfSessionSub').textContent = `— ${topic}`;
  document.getElementById('selfSetup').classList.add('hidden');
  document.getElementById('selfLearn').classList.remove('hidden');
  document.getElementById('selfMsgs').innerHTML = '';
  document.getElementById('selfEndBtn').classList.remove('hidden');

  window._selfSys = `You are MetaLearn's curiosity-driven tutor. Topic: "${topic}". Why interested: "${why || 'general curiosity'}". Prior knowledge: "${prior || 'none'}". Depth goal: ${depth}.
Rules:
1. Teach with genuine intellectual depth — don't oversimplify just because there's no exam pressure.
2. Every 3 exchanges, add [META]: a reflective question on its own line (Pintrich 2002 metacognitive knowledge style).
3. Connect to unexpected adjacent domains when genuinely relevant — curiosity-driven learners respond to surprising links.
4. Challenge oversimplifications directly; don't let comfortable wrong answers slide just because the tone is casual.
5. Surface what the learner doesn't know they don't know.
6. Max 3 paragraphs per response.`;

  _selfHistory.push({ role: 'user', content: `I want to explore: ${topic}. ${why ? 'What drew me in: ' + why : ''} ${prior ? 'I think I know: ' + prior : ''}` });

  load('Starting exploration...');
  try {
    await streamSelfChat();
  } finally {
    unload();
  }
}

async function sendSelfMsg() {
  const inp = document.getElementById('selfInput');
  const txt = inp.value.trim();
  if (!txt) return;
  inp.value = '';
  inp.style.height = '22px';
  addMsg('selfMsgs', 'user', txt);
  _selfHistory.push({ role: 'user', content: txt });
  await streamSelfChat();
}

async function streamSelfChat() {
  document.getElementById('selfSend').disabled = true;
  addTyping('selfMsgs', 'selfTyping');
  try {
    await aiStream(_selfHistory, window._selfSys,
      tok => {
        const t = document.getElementById('selfTyping');
        if (t) {
          t.remove();
          const msgEl = addMsg('selfMsgs', 'ai', '');
          msgEl.querySelector('.bbl').id = 'selfStream';
        }
        const s = document.getElementById('selfStream');
        if (s) { s.textContent += tok; document.getElementById('selfMsgs').scrollTop = 9999; }
      },
      full => {
        const s = document.getElementById('selfStream');
        if (s) s.removeAttribute('id');
        const metas = [...full.matchAll(/\[META\]:\s*(.+?)(?=\n|$)/g)].map(m => m[1]);
        metas.forEach(q => {
          const c = document.getElementById('selfMsgs');
          const d = document.createElement('div');
          d.className = 'meta-card';
          d.innerHTML = `<div class="meta-card-label" style="color:var(--self)">🌱 Reflect</div><div style="font-size:13.5px">${q}</div>`;
          c.appendChild(d);
          c.scrollTop = 9999;
        });
        _selfHistory.push({ role: 'assistant', content: full.replace(/\[META\]:.+?(?=\n|$)/g, '').trim() });
      }
    );
  } catch (e) {
    const t = document.getElementById('selfTyping');
    if (t) t.remove();
    addMsg('selfMsgs', 'ai', '⚠ Error: ' + e.message);
  }
  document.getElementById('selfSend').disabled = false;
}

function endSelfSession() {
  document.getElementById('selfLearn').classList.add('hidden');
  document.getElementById('selfReflect').classList.remove('hidden');
  document.getElementById('selfEndBtn').classList.add('hidden');
  document.getElementById('reflectResult').classList.add('hidden');
  ['refSurprise', 'refUnclear', 'refConnect'].forEach(id => document.getElementById(id).value = '');
}

function resetSelfSession() {
  document.getElementById('selfReflect').classList.add('hidden');
  document.getElementById('selfSetup').classList.remove('hidden');
  ['selfTopic', 'selfWhy', 'selfPrior'].forEach(id => document.getElementById(id).value = '');
}

// ── Reflection Scoring ────────────────────────────────────────────────────
// Plan -> Monitor -> Evaluate loop, Schraw (1998)

async function scoreReflection() {
  const surprise = document.getElementById('refSurprise').value.trim();
  const unclear = document.getElementById('refUnclear').value.trim();
  const connect = document.getElementById('refConnect').value.trim();
  if (!surprise && !unclear && !connect) { alert('Fill in at least one reflection field.'); return; }

  load('Scoring reflection...');
  try {
    const topic = window._selfCurrentTopic || 'the topic explored';
    const raw = await ai(`Score this learning reflection on "${topic}" using Schraw (1998) self-regulation and Tanner (2012) metacognition frameworks.
Surprise: "${surprise}". Unclear: "${unclear}". Connection: "${connect}".

Score on depth (surface vs causal), specificity (vague vs concrete), connection-making, and novelty.

Return ONLY valid JSON:
{"overall":0.74,"depth":0.68,"transfer":0.81,"feedback":"specific 2-sentence feedback","muddiest_point":"the clearest unresolved question to investigate next"}`);

    const d = JSON.parse(raw);
    document.getElementById('refScore').textContent = ((d.overall || 0) * 100).toFixed(0) + '%';
    document.getElementById('refDepth').textContent = ((d.depth || 0) * 100).toFixed(0) + '%';
    document.getElementById('refTransfer').textContent = ((d.transfer || 0) * 100).toFixed(0) + '%';
    document.getElementById('refFeedback').textContent = d.feedback || '';
    document.getElementById('refMuddiest').textContent = d.muddiest_point || unclear || 'Nothing flagged.';
    document.getElementById('reflectResult').classList.remove('hidden');

    updatePulse(
      Math.round((d.overall || 0) * 100),
      50,
      d.transfer || 0
    );
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

// ── Muddiest Point ────────────────────────────────────────────────────────
// Direct implementation of Tanner (2012)'s named technique

async function runMuddiest() {
  const point = document.getElementById('muddyPoint').value.trim();
  if (!point) { alert("Describe what's unclear."); return; }

  load('Diagnosing confusion...');
  try {
    const raw = await ai(`Learning coach. Help clarify this confusion (Tanner 2012 muddiest-point pedagogy).
Topic: "${document.getElementById('muddyTopic').value}". Unclear: "${point}". Already tried: "${document.getElementById('muddyTried').value}".

Return ONLY valid JSON:
{"why_confusing":"","clearest_explanation":"","analogy":"","test_questions":[]}`);

    const d = JSON.parse(raw);
    document.getElementById('muddyDiagnosis').textContent = d.why_confusing || '';
    document.getElementById('muddyExplain').textContent = d.clearest_explanation || '';
    document.getElementById('muddyAnalogy').textContent = d.analogy || '';
    document.getElementById('muddyTests').innerHTML = (d.test_questions || []).map(q => `<li>${q}</li>`).join('');
    resetSect('muddyResult', 'muddySetup');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

// ── Rabbit Hole ───────────────────────────────────────────────────────────

async function runRabbitHole() {
  const idea = document.getElementById('rhIdea').value.trim();
  if (!idea) { alert('Enter an idea.'); return; }

  load('Mapping the rabbit hole...');
  try {
    const raw = await ai(`Intellectual guide. Map a rabbit hole starting from: "${idea}".

Return ONLY valid JSON:
{"title":"","core_explanation":"","threads":[{"thread":"","why_interesting":""}],"unexpected_connections":[{"idea_a":"${idea}","idea_b":"","connection":""}],"next_session":""}`);

    const d = JSON.parse(raw);
    document.getElementById('rhTitle').textContent = d.title || idea;
    document.getElementById('rhCore').textContent = d.core_explanation || '';

    document.getElementById('rhThreads').innerHTML = (d.threads || []).map((t, i) => `
      <div style="display:flex;gap:11px;padding:10px 0;border-bottom:1px solid var(--b1)">
        <div style="width:20px;height:20px;border-radius:50%;background:var(--self-d);border:1px solid var(--self-b);color:var(--self);font-size:11px;font-weight:600;display:flex;align-items:center;justify-content:center;flex-shrink:0">${i + 1}</div>
        <div>
          <div style="font-size:13px;font-weight:500">${t.thread}</div>
          <div style="font-size:12px;color:var(--t3);margin-top:2px">${t.why_interesting}</div>
          <button class="btn btn-self btn-sm mt-8" onclick="jumpToSelfTopic('${t.thread.replace(/'/g, "\\'")}')">Explore this →</button>
        </div>
      </div>`).join('');

    document.getElementById('rhConnections').innerHTML = (d.unexpected_connections || []).map(c => `
      <div style="padding:9px 0;border-bottom:1px solid var(--b1)">
        <div class="flex gap-8"><span class="tag tag-self">${c.idea_a}</span><span style="color:var(--t3);font-size:12px">↔</span><span class="tag tag-self">${c.idea_b}</span></div>
        <div style="font-size:13px;color:var(--t2);margin-top:6px">${c.connection}</div>
      </div>`).join('');

    document.getElementById('rhNext').textContent = d.next_session || '';
    resetSect('rhResult', 'rhSetup');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

function jumpToSelfTopic(topic) {
  showView('self-session');
  setTimeout(() => { const el = document.getElementById('selfTopic'); if (el) el.value = topic; }, 50);
}

// ── Idea Connections ──────────────────────────────────────────────────────
// Transfer between domains = highest form of understanding (Tanner, 2012)

async function runConnections() {
  const a = document.getElementById('connA').value.trim();
  const b = document.getElementById('connB').value.trim();
  if (!a || !b) { alert('Enter both ideas.'); return; }

  load('Finding connections...');
  try {
    const raw = await ai(`Find deep structural connections between "${a}" and "${b}". This is about concept transfer — the highest form of understanding.

Return ONLY valid JSON:
{"title":"","core_connection":"","structural_similarities":[],"key_differences":[],"transfer_insight":""}`);

    const d = JSON.parse(raw);
    document.getElementById('connTitle').textContent = d.title || `${a} ↔ ${b}`;
    document.getElementById('connCore').textContent = d.core_connection || '';
    document.getElementById('connSimilar').innerHTML = (d.structural_similarities || []).map(s => `<li>${s}</li>`).join('');
    document.getElementById('connDiff').innerHTML = (d.key_differences || []).map(s => `<li>${s}</li>`).join('');
    document.getElementById('connInsight').textContent = d.transfer_insight || '';
    resetSect('connResult', 'connSetup');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

// ── Journal ───────────────────────────────────────────────────────────────

function addJournalEntry() {
  document.getElementById('journalCompose').classList.remove('hidden');
}

function saveJournalEntry() {
  const txt = document.getElementById('journalText').value.trim();
  if (!txt) return;
  _journalEntries.unshift({ text: txt, date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) });
  document.getElementById('journalText').value = '';
  document.getElementById('journalCompose').classList.add('hidden');
  renderJournal();
}

function renderJournal() {
  document.getElementById('journalEntries').innerHTML = _journalEntries.length
    ? _journalEntries.map(e => `
        <div class="card mb-8">
          <div style="font-size:11px;color:var(--t3);margin-bottom:6px">${e.date}</div>
          <div style="font-size:13.5px;line-height:1.7;color:var(--t2)">${e.text}</div>
        </div>`).join('')
    : `<div style="color:var(--t3);text-align:center;padding:40px;font-size:13px">No journal entries yet. Journaling builds metacognitive knowledge over time. (Tanner, 2012)</div>`;
}