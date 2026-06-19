// ── ACADEMIC MODULE ──────────────────────────────────────────────────────
// Implements the Plan -> Monitor -> Evaluate loop (Schraw, 1998)
// Confidence elicitation happens AFTER recall attempts, never during passive reading
// (Dunlosky & Nelson, 1992 / Koriat & Bjork, 2005 — foresight bias)

let _acadTopic = '';
let _preConf = 50;
let _acadHistory = [];
let _acadMsgCount = 0;
let _acadMisconceptions = [];
let _feynmanScoreVal = 0;
let _quizData = [];
let _quizIdx = 0;
let _quizScore = 0;
let _uploadedMaterials = {};

// ── Pre-Learning Phase ───────────────────────────────────────────────────

async function startAcadSession() {
  _acadTopic = document.getElementById('acadTopic').value.trim();
  if (!_acadTopic) { alert('Enter a topic.'); return; }
  _preConf = parseInt(document.getElementById('preConfSlider').value);
  const prior = document.getElementById('acadPrior').value.trim();

  _acadHistory = [];
  _acadMsgCount = 0;
  _acadMisconceptions = [];
  updateMiscBadge();

  document.getElementById('acadSessionSub').textContent = `— ${_acadTopic}`;
  document.getElementById('feynmanTopicLabel').textContent = _acadTopic;
  document.getElementById('resultsTopicLabel').textContent = _acadTopic;
  document.getElementById('acadMsgs').innerHTML = '';

  setStep(['as-pre', 'as-learn', 'as-feynman', 'as-quiz', 'as-results'], 1);
  document.getElementById('acadPre').classList.add('hidden');
  document.getElementById('acadLearn').classList.remove('hidden');

  const materialContext = _uploadedMaterials[_acadTopic] ? `\n\nReference material provided by learner:\n"""${_uploadedMaterials[_acadTopic].slice(0, 3000)}"""` : '';

  const sys = `You are MetaLearn, an AI metacognitive tutor. Topic: "${_acadTopic}". Learner's stated prior knowledge: "${prior || 'none'}". Learner's self-rated confidence: ${_preConf}%.${materialContext}

Rules:
1. Max 3 short paragraphs per response. Dense walls of text defeat learning.
2. Every 2 exchanges, insert exactly ONE metacognitive prompt on its own line: [META]: question
   Good prompts (Schraw 1998 regulatory checklist style): "What surprised you?", "Where are you still fuzzy?", "How does this connect to something you already know?", "Predict what comes next."
3. If you detect a misconception in what the learner says, flag it on its own line: [MISCONCEPTION]: brief description
4. Never just give answers — make the learner reason first, then confirm or correct.
5. Use concrete examples and analogies, not abstract definitions.
6. If reference material was provided, ground your teaching in it specifically.`;

  _acadHistory.push({ role: 'user', content: `Teach me about: ${_acadTopic}. ${prior ? 'My prior knowledge: ' + prior : ''}` });

  load('Starting session...');
  try {
    await streamAcadChat(sys);
  } finally {
    unload();
  }
}

async function sendAcadMsg() {
  const inp = document.getElementById('acadInput');
  const txt = inp.value.trim();
  if (!txt) return;
  inp.value = '';
  inp.style.height = '22px';
  addMsg('acadMsgs', 'user', txt);
  _acadHistory.push({ role: 'user', content: txt });
  _acadMsgCount++;
  document.getElementById('acadMsgCount').textContent = `${_acadMsgCount} exchange${_acadMsgCount !== 1 ? 's' : ''}`;

  const sys = `You are MetaLearn metacognitive tutor. Topic: "${_acadTopic}". Confidence: ${_preConf}%. Rules: (1) Max 3 short paragraphs. (2) Every 2 exchanges add [META]: question on its own line. (3) Flag misconceptions as [MISCONCEPTION]: description. (4) Challenge shallow thinking. Keep responses tight.`;
  await streamAcadChat(sys);
}

async function streamAcadChat(sys) {
  document.getElementById('acadSend').disabled = true;
  addTyping('acadMsgs', 'acadTyping');
  try {
    await aiStream(_acadHistory, sys,
      tok => {
        const t = document.getElementById('acadTyping');
        if (t) {
          t.remove();
          const msgEl = addMsg('acadMsgs', 'ai', '');
          msgEl.querySelector('.bbl').id = 'acadStream';
        }
        const s = document.getElementById('acadStream');
        if (s) { s.textContent += tok; document.getElementById('acadMsgs').scrollTop = 9999; }
      },
      full => {
        const s = document.getElementById('acadStream');
        if (s) s.removeAttribute('id');

        const metas = [...full.matchAll(/\[META\]:\s*(.+?)(?=\n|$)/g)].map(m => m[1]);
        const miscs = [...full.matchAll(/\[MISCONCEPTION\]:\s*(.+?)(?=\n|$)/g)].map(m => m[1]);

        miscs.forEach(m => {
          if (!_acadMisconceptions.includes(m)) {
            _acadMisconceptions.push(m);
            updateMiscBadge();
          }
        });

        metas.forEach(q => {
          const c = document.getElementById('acadMsgs');
          const d = document.createElement('div');
          d.className = 'meta-card';
          d.innerHTML = `<div class="meta-card-label" style="color:var(--amber)">🧠 Metacognitive prompt</div><div style="font-size:13.5px">${q}</div>`;
          c.appendChild(d);
          c.scrollTop = 9999;
        });

        const clean = full.replace(/\[(META|MISCONCEPTION)\]:.+?(?=\n|$)/g, '').trim();
        _acadHistory.push({ role: 'assistant', content: clean });
      }
    );
  } catch (e) {
    const t = document.getElementById('acadTyping');
    if (t) t.remove();
    addMsg('acadMsgs', 'ai', '⚠ Error: ' + e.message);
  }
  document.getElementById('acadSend').disabled = false;
}

function updateMiscBadge() {
  const b = document.getElementById('miscBadge');
  if (b) {
    b.textContent = _acadMisconceptions.length;
    b.style.display = _acadMisconceptions.length ? 'inline-flex' : 'none';
  }
}

// ── Feynman Phase ─────────────────────────────────────────────────────────
// Deliberately separated in time/context from the teaching phase
// (Thiede & Anderson, 2003 — delayed summarization produces accurate self-assessment)

function goToFeynman() {
  setStep(['as-pre', 'as-learn', 'as-feynman', 'as-quiz', 'as-results'], 2);
  document.getElementById('acadLearn').classList.add('hidden');
  document.getElementById('acadFeynman').classList.remove('hidden');
  document.getElementById('feynmanResult').classList.add('hidden');
  document.getElementById('feynmanText').value = '';
}

async function scoreFeynman() {
  const txt = document.getElementById('feynmanText').value.trim();
  if (txt.length < 30) { alert('Write a real explanation — at least a few sentences.'); return; }

  load('Evaluating Feynman explanation...');
  try {
    const raw = await ai(`Evaluate this Feynman explanation of "${_acadTopic}".
Learner wrote: """${txt}"""

Score 0.00-1.00 on each dimension. Penalize answers that merely recycle source vocabulary without independent reconstruction (Serra & Metcalfe, 2009 familiarity-bias finding) — recognising terms is not the same as explaining them.

Return ONLY valid JSON:
{"scores":{"accuracy":0.0,"clarity":0.0,"depth":0.0,"transfer":0.0},"overall":0.0,"strengths":"","gaps":"","next_step":""}`);

    const d = JSON.parse(raw);
    _feynmanScoreVal = d.overall || 0;

    document.getElementById('feyScore').textContent = d.overall?.toFixed(2) || '—';
    document.getElementById('feyDims').innerHTML = Object.entries(d.scores || {}).map(([k, v]) => `
      <div class="score-card" style="padding:10px">
        <div style="font-size:18px;font-weight:600;color:${v >= .75 ? 'var(--green)' : v >= .5 ? 'var(--amber)' : 'var(--red)'}">${(v * 100).toFixed(0)}</div>
        <div style="font-size:10px;color:var(--t3);text-transform:capitalize">${k}</div>
      </div>`).join('');

    document.getElementById('feyStrengths').innerHTML = `<div class="hl-label" style="color:var(--green)">Strengths</div>${d.strengths || ''}`;
    document.getElementById('feyGaps').innerHTML = `<div class="hl-label" style="color:var(--amber)">Gaps</div>${d.gaps || ''}`;
    document.getElementById('feyNextTxt').textContent = d.next_step || '';
    document.getElementById('feynmanResult').classList.remove('hidden');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

// ── Quiz Phase ────────────────────────────────────────────────────────────

async function goToAcadQuiz() {
  setStep(['as-pre', 'as-learn', 'as-feynman', 'as-quiz', 'as-results'], 3);
  document.getElementById('acadFeynman').classList.add('hidden');
  document.getElementById('acadQuiz').classList.remove('hidden');
  document.getElementById('quizLoading').classList.remove('hidden');
  document.getElementById('quizQuestion').classList.add('hidden');

  _quizIdx = 0;
  _quizScore = 0;
  _quizData = [];

  const transcript = _acadHistory.slice(-10).map(m => `${m.role}: ${m.content.slice(0, 200)}`).join('\n');

  try {
    const raw = await ai(`Generate 4 MCQ questions about "${_acadTopic}" that test understanding, not memorisation. Based on this session:
"""${transcript}"""

Return ONLY valid JSON:
{"questions":[{"id":1,"question":"","options":{"A":"","B":"","C":"","D":""},"correct":"A","explanation":"","difficulty":"medium"}]}`);

    const d = JSON.parse(raw);
    _quizData = d.questions || [];
    document.getElementById('quizLoading').classList.add('hidden');
    document.getElementById('quizQuestion').classList.remove('hidden');
    showQuizQ();
  } catch (e) {
    alert('Error generating quiz: ' + e.message);
  }
}

function showQuizQ() {
  const q = _quizData[_quizIdx];
  document.getElementById('quizProg').textContent = `Question ${_quizIdx + 1} of ${_quizData.length}`;
  document.getElementById('quizQText').textContent = q.question;
  document.getElementById('quizOpts').innerHTML = Object.entries(q.options || {}).map(([k, v]) =>
    `<div class="opt" onclick="selectOpt('${k}',this)" data-letter="${k}"><div class="opt-letter">${k}</div>${v}</div>`
  ).join('');
}

function selectOpt(letter, el) {
  const q = _quizData[_quizIdx];
  document.querySelectorAll('.opt').forEach(o => {
    o.onclick = null;
    if (o.dataset.letter === q.correct) o.classList.add('correct');
    else if (o === el) o.classList.add('wrong');
  });
  if (letter === q.correct) _quizScore++;
  setTimeout(() => {
    _quizIdx++;
    _quizIdx < _quizData.length ? showQuizQ() : showAcadResults();
  }, 900);
}

// ── Post-Learning: Results & Recalibration ──────────────────────────────

function showAcadResults() {
  const pct = Math.round((_quizScore / _quizData.length) * 100);
  const calibErr = _preConf - pct;

  setStep(['as-pre', 'as-learn', 'as-feynman', 'as-quiz', 'as-results'], 4);
  document.getElementById('acadQuiz').classList.add('hidden');
  document.getElementById('acadResults').classList.remove('hidden');

  document.getElementById('resFey').textContent = _feynmanScoreVal.toFixed(2);
  document.getElementById('resQScore').textContent = pct + '%';
  document.getElementById('resCalib').textContent = (calibErr > 0 ? '+' : '') + calibErr + '%';

  let calibMsg = '';
  if (Math.abs(calibErr) <= 10) {
    calibMsg = `Well calibrated. Your confidence (${_preConf}%) matched your performance (${pct}%). This is rare — most learners are significantly overconfident. (Dunlosky & Nelson, 1992)`;
  } else if (calibErr > 10) {
    calibMsg = `Overconfident by ${calibErr} points. You expected ${_preConf}% but scored ${pct}%. Familiarity felt like understanding — the core failure mode MetaLearn measures. (Serra & Metcalfe, 2009)`;
  } else {
    calibMsg = `Underconfident by ${Math.abs(calibErr)} points. You scored ${pct}% but only expected ${_preConf}%. You know more than you think.`;
  }
  document.getElementById('resCalibInsight').innerHTML = `<div class="hl-label" style="color:var(--academic)">Calibration insight</div>${calibMsg}`;

  if (_acadMisconceptions.length) {
    document.getElementById('resMiscSection').classList.remove('hidden');
    document.getElementById('resMiscList').innerHTML = _acadMisconceptions.map(m =>
      `<div style="display:flex;gap:8px;padding:7px 0;border-bottom:1px solid var(--b1)"><span style="color:var(--red)">⚠</span><span style="font-size:13px;color:var(--t2)">${m}</span></div>`
    ).join('');
  }

  const nextReview = pct >= 80 ? '7 days' : pct >= 60 ? '3 days' : '1 day';
  document.getElementById('resNextReview').innerHTML = `<div style="font-size:13px;color:var(--t2)">Next review in <strong style="color:var(--academic)">${nextReview}</strong> (SM-2 algorithm). Topic: <strong>${_acadTopic}</strong></div>`;

  updatePulse(pct, _preConf, _feynmanScoreVal);
}

function resetAcadSession() {
  setStep(['as-pre', 'as-learn', 'as-feynman', 'as-quiz', 'as-results'], 0);
  ['acadLearn', 'acadFeynman', 'acadQuiz', 'acadResults'].forEach(id => document.getElementById(id)?.classList.add('hidden'));
  document.getElementById('acadPre').classList.remove('hidden');
  document.getElementById('acadTopic').value = '';
  document.getElementById('acadPrior').value = '';
  document.getElementById('preConfSlider').value = 50;
  document.getElementById('preConfNum').textContent = '50%';
}

// ── Exam Wrapper ──────────────────────────────────────────────────────────
// Template from Lovett (2016), CMU Eberly Center

async function runExamWrapper() {
  const subject = document.getElementById('ewSubject').value.trim();
  if (!subject) { alert('Enter subject/exam.'); return; }

  load('Analysing exam...');
  try {
    const raw = await ai(`Metacognitive exam analysis (exam-wrapper format, Lovett 2016).
Subject: "${subject}". Score: "${document.getElementById('ewScore').value}". Expected: "${document.getElementById('ewExpected').value}".
Study approach: "${document.getElementById('ewStudy').value}". Trouble topics: "${document.getElementById('ewTrouble').value}". Why wrong: "${document.getElementById('ewWhy').value}".

Return ONLY valid JSON:
{"diagnosis":"2 sentence honest diagnosis","what_went_wrong":[{"issue":"","explanation":""}],"study_strategy_analysis":[{"strategy":"","assessment":"","better_alternative":""}],"do_differently":[],"metacognitive_insight":""}`);

    const d = JSON.parse(raw);
    document.getElementById('ewResTitle').textContent = subject;
    document.getElementById('ewDiagnosis').innerHTML = `<div class="hl-label" style="color:var(--academic)">Diagnosis</div>${d.diagnosis || ''}`;

    document.getElementById('ewWhatWrong').innerHTML = (d.what_went_wrong || []).map(w => `
      <div style="padding:8px 0;border-bottom:1px solid var(--b1)"><div style="font-size:13px;font-weight:500">${w.issue}</div><div style="font-size:12.5px;color:var(--t2);margin-top:2px">${w.explanation}</div></div>`).join('');

    document.getElementById('ewStrategy').innerHTML = (d.study_strategy_analysis || []).map(s => `
      <div style="padding:8px 0;border-bottom:1px solid var(--b1)">
        <span class="tag tag-amber">${s.strategy}</span>
        <div style="font-size:12.5px;color:var(--t2);margin-top:4px">${s.assessment}</div>
        <div style="font-size:12px;color:var(--green);margin-top:3px">→ ${s.better_alternative}</div>
      </div>`).join('');

    document.getElementById('ewDoDiff').innerHTML = (d.do_differently || []).map(s => `<li>${s}</li>`).join('');
    document.getElementById('ewMeta').textContent = d.metacognitive_insight || '';
    resetSect('ewResults', 'ewSetup');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

// ── Upload Material ───────────────────────────────────────────────────────

function saveUploadedMaterial() {
  const name = document.getElementById('uploadTopicName').value.trim();
  const content = document.getElementById('uploadContent').value.trim();
  if (!name || !content) { alert('Add a topic name and paste content.'); return; }
  _uploadedMaterials[name] = content;
  alert(`Saved! Start a session on "${name}" and MetaLearn will use this material as context.`);
  document.getElementById('uploadTopicName').value = '';
  document.getElementById('uploadContent').value = '';
}

// ── Standalone Feynman Test ───────────────────────────────────────────────

async function runStandaloneFeynman() {
  const topic = document.getElementById('standaloneFeynmanTopic').value.trim();
  const txt = document.getElementById('standaloneFeynmanText').value.trim();
  if (!topic || txt.length < 30) { alert('Add a topic and a real explanation.'); return; }

  load('Scoring explanation...');
  try {
    const raw = await ai(`Evaluate this Feynman explanation of "${topic}".
Learner wrote: """${txt}"""

Return ONLY valid JSON:
{"scores":{"accuracy":0.0,"clarity":0.0,"depth":0.0,"transfer":0.0},"overall":0.0,"strengths":"","gaps":"","next_step":""}`);

    const d = JSON.parse(raw);
    document.getElementById('sfScore').textContent = d.overall?.toFixed(2) || '—';
    document.getElementById('sfDims').innerHTML = Object.entries(d.scores || {}).map(([k, v]) => `
      <div class="score-card" style="padding:10px"><div style="font-size:18px;font-weight:600;color:${v >= .75 ? 'var(--green)' : v >= .5 ? 'var(--amber)' : 'var(--red)'}">${(v * 100).toFixed(0)}</div><div style="font-size:10px;color:var(--t3);text-transform:capitalize">${k}</div></div>`).join('');
    document.getElementById('sfStr').innerHTML = `<div class="hl-label" style="color:var(--green)">Strengths</div>${d.strengths || ''}`;
    document.getElementById('sfGaps').innerHTML = `<div class="hl-label" style="color:var(--amber)">Gaps</div>${d.gaps || ''}`;
    document.getElementById('sfNext').textContent = d.next_step || '';
    document.getElementById('standaloneFeynmanResult').classList.remove('hidden');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

// ── Standalone Quiz ────────────────────────────────────────────────────────

let _sqData = [];
let _sqIdx = 0;
let _sqScore = 0;

async function runStandaloneQuiz() {
  const topic = document.getElementById('sqTopic').value.trim();
  if (!topic) { alert('Enter a topic.'); return; }
  const diff = getChip('sqDiffChips') || 'medium';

  load('Generating quiz...');
  try {
    const raw = await ai(`Generate 5 MCQ questions about "${topic}" at ${diff} difficulty.
Return ONLY valid JSON:
{"questions":[{"id":1,"question":"","options":{"A":"","B":"","C":"","D":""},"correct":"A"}]}`);

    const d = JSON.parse(raw);
    _sqData = d.questions || [];
    _sqIdx = 0;
    _sqScore = 0;
    document.getElementById('sqSetup').classList.add('hidden');
    document.getElementById('sqQuiz').classList.remove('hidden');
    showSqQ();
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

function showSqQ() {
  const q = _sqData[_sqIdx];
  document.getElementById('sqProg').textContent = `Question ${_sqIdx + 1} of ${_sqData.length}`;
  document.getElementById('sqQText').textContent = q.question;
  document.getElementById('sqOpts').innerHTML = Object.entries(q.options || {}).map(([k, v]) =>
    `<div class="opt" onclick="selectSqOpt('${k}',this)" data-letter="${k}"><div class="opt-letter">${k}</div>${v}</div>`
  ).join('');
}

function selectSqOpt(letter, el) {
  const q = _sqData[_sqIdx];
  document.querySelectorAll('#sqOpts .opt').forEach(o => {
    o.onclick = null;
    if (o.dataset.letter === q.correct) o.classList.add('correct');
    else if (o === el) o.classList.add('wrong');
  });
  if (letter === q.correct) _sqScore++;
  setTimeout(() => {
    _sqIdx++;
    if (_sqIdx < _sqData.length) showSqQ();
    else {
      document.getElementById('sqQuiz').classList.add('hidden');
      document.getElementById('sqResults').classList.remove('hidden');
      const pct = Math.round((_sqScore / _sqData.length) * 100);
      document.getElementById('sqScore').textContent = pct + '%';
      document.getElementById('sqCalibLabel').textContent = pct >= 70 ? 'Solid' : 'Needs review';
    }
  }, 900);
}