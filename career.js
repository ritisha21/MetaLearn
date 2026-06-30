// ── CAREER MODULE ────────────────────────────────────────────────────────

let _jdData = null;
let _skillMapData = null;
let _mockHistory = [];
let _mockQCount = 0;
let _mockDone = false;

// ── JD Analysis ──────────────────────────────────────────────────────────

async function runJDAnalysis(quick = false) {
  const title = document.getElementById('jdTitle').value.trim();
  if (!title && !quick) { alert('Enter a job title.'); return; }
  const company = document.getElementById('jdCompany').value.trim();
  const jd = document.getElementById('jdText').value.trim();

  load('Analysing job description...');
  try {
    const raw = await ai(`You are a senior career coach. Analyse: "${title || 'Software Engineer'}" at "${company || 'a tech company'}".
JD: """${jd || 'Not provided — infer from title and company type'}"""

Return ONLY valid JSON:
{"role_summary":"2 sentence summary","required_skills":[],"nice_to_have":[],"likely_interview_topics":[{"topic":"","why":"","difficulty":""}],"skills_to_build":[{"skill":"","priority":"","reason":""}],"red_flags":[]}`);

    const d = JSON.parse(raw);
    _jdData = { ...d, title, company, jd };

    document.getElementById('jdResTitle').textContent = title || 'Analysis';
    document.getElementById('jdResComp').textContent = company ? `at ${company}` : '';

    if (d.role_summary) {
      document.getElementById('jdSummaryTxt').textContent = d.role_summary;
      document.getElementById('jdSummaryBox').style.display = 'block';
    }

    document.getElementById('jdReqSkills').innerHTML =
      (d.required_skills || []).map(s => `<span class="tag tag-career" style="margin:2px">${s}</span>`).join('') +
      (d.nice_to_have || []).map(s => `<span class="tag" style="background:var(--s3);color:var(--t2);margin:2px">${s} <span style="font-size:10px;opacity:.5">opt</span></span>`).join('');

    document.getElementById('jdTopics').innerHTML = (d.likely_interview_topics || []).map(t => `
      <div style="padding:7px 0;border-bottom:1px solid var(--b1)">
        <div class="flex gap-8"><span style="flex:1;font-size:13px;font-weight:500">${t.topic}</span><span class="tag tag-${t.difficulty === 'hard' ? 'red' : t.difficulty === 'medium' ? 'amber' : 'green'}">${t.difficulty}</span></div>
        <div style="font-size:11.5px;color:var(--t3);margin-top:2px">${t.why}</div>
      </div>`).join('');

    document.getElementById('jdSkillsBuild').innerHTML = (d.skills_to_build || []).map(s => `
      <div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid var(--b1)">
        <span class="tag tag-${s.priority === 'high' ? 'red' : 'amber'}">${s.priority}</span>
        <div><div style="font-size:13px;font-weight:500">${s.skill}</div><div style="font-size:12px;color:var(--t3);margin-top:2px">${s.reason}</div></div>
      </div>`).join('');

    if (d.red_flags?.length) {
      document.getElementById('jdRedFlagsTxt').innerHTML = d.red_flags.map(f => `<div>⚠ ${f}</div>`).join('');
      document.getElementById('jdRedFlags').style.display = 'block';
    }

    resetSect('jdResults', 'jdSetup');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

function preFillMock() {
  if (_jdData) {
    document.getElementById('mockRole').value = _jdData.title || '';
    document.getElementById('mockCompany').value = _jdData.company || '';
    document.getElementById('mockJD').value = _jdData.jd || '';
  }
}
function preFillResume() {
  if (_jdData) {
    document.getElementById('resJobTitle').value = _jdData.title || '';
    document.getElementById('resJD').value = _jdData.jd || '';
  }
}
function preFillPlan() {
  if (_jdData?.skills_to_build?.length) {
    document.getElementById('cpSkill').value = _jdData.skills_to_build.slice(0, 2).map(s => s.skill).join(', ');
  }
}
function preFillPlanFromSkillMap() {
  if (_skillMapData?.priority_skills?.length) {
    document.getElementById('cpSkill').value = _skillMapData.priority_skills.slice(0, 2).map(s => s.skill).join(', ');
  }
}

// ── Mock Interview ───────────────────────────────────────────────────────

async function startMockInterview() {
  const role = document.getElementById('mockRole').value.trim() || 'Software Engineer';
  const company = document.getElementById('mockCompany').value.trim();
  const focus = getChip('mockFocusChips');
  const level = getChip('mockLevelChips');
  const jd = document.getElementById('mockJD').value.trim();
  const bg = document.getElementById('mockBG').value.trim();

  _mockHistory = [];
  _mockQCount = 1;
  _mockDone = false;

  document.getElementById('mockSetup').classList.add('hidden');
  document.getElementById('mockChat').classList.remove('hidden');
  document.getElementById('mockMsgs').innerHTML = '';
  document.getElementById('mockSubtitle').textContent = `— ${role}${company ? ' at ' + company : ''}`;
  document.getElementById('mockStats').classList.remove('hidden');
  document.getElementById('mockEndBtn').classList.remove('hidden');
  document.getElementById('mockQ').textContent = '1';
  document.getElementById('mockInput').disabled = false;

  window._mockSys = `You are a ${level}-level interviewer at ${company || 'a top tech company'} for a ${role} role. Focus: ${focus}. JD: ${jd.slice(0, 300) || 'N/A'}. Candidate background: ${bg || 'N/A'}.
Rules: ONE question per message. After each answer: 2-sentence feedback (what was strong, what was weak), then the next question. After 6 questions total: write exactly ##DONE## plus a one-line closing. Probe shallow answers — ask "can you be more specific?" or "what trade-offs did you consider?" Max 100 words per response. Calibrate difficulty to the stated level.`;

  _mockHistory.push({ role: 'user', content: 'Start the interview. Ask the first question only.' });

  load('Starting interview...');
  try {
    await streamChat('mockMsgs', _mockHistory, window._mockSys, (h, full) => {
      _mockHistory = h;
      if (full.includes('##DONE##')) markMockDone();
    });
  } finally {
    unload();
  }
}

function markMockDone() {
  _mockDone = true;
  document.getElementById('mockInput').disabled = true;
  document.getElementById('mockHint').textContent = 'Interview complete — click "End & score →" above';
}

async function sendMockMsg() {
  const inp = document.getElementById('mockInput');
  const txt = inp.value.trim();
  if (!txt || _mockDone) return;
  inp.value = '';
  inp.style.height = '22px';
  addMsg('mockMsgs', 'user', txt);
  _mockHistory.push({ role: 'user', content: txt });
  _mockQCount++;
  document.getElementById('mockQ').textContent = Math.min(_mockQCount, 6);

  await streamChat('mockMsgs', _mockHistory, window._mockSys, (h, full) => {
    _mockHistory = h;
    if (full.includes('##DONE##')) markMockDone();
  });
}

async function endMockInterview() {
  load('Generating performance report...');
  const transcript = _mockHistory
    .map(m => `${m.role === 'assistant' ? 'INTERVIEWER' : 'CANDIDATE'}: ${m.content}`)
    .join('\n\n');

  try {
    const raw = await ai(`Score this mock interview transcript. Role: ${document.getElementById('mockRole').value}.
Transcript: """${transcript}"""

Return ONLY valid JSON:
{"overall_score":74,"hire_signal":"Lean yes","confidence_calibration":"Overconfident","dimension_scores":{"communication":80,"technical_depth":65,"problem_solving":70,"behavioural_examples":75,"role_fit":78},"strengths":[],"areas_to_improve":[{"area":"","gap":"","fix":""}],"best_answer":"","weakest_answer":"","next_steps":[]}`);

    const d = JSON.parse(raw);
    document.getElementById('rScore').textContent = d.overall_score + '%';
    document.getElementById('rHire').textContent = d.hire_signal || '—';
    document.getElementById('rCalib').textContent = d.confidence_calibration || '—';

    document.getElementById('rDims').innerHTML = Object.entries(d.dimension_scores || {}).map(([k, v]) => `
      <div class="skill-row">
        <div class="skill-name" style="text-transform:capitalize;min-width:130px">${k.replace(/_/g, ' ')}</div>
        <div class="skill-bar-track"><div class="skill-bar-fill" style="width:${v}%;background:${v >= 75 ? 'var(--green)' : v >= 50 ? 'var(--amber)' : 'var(--red)'}"></div></div>
        <span style="font-size:12px;min-width:30px;text-align:right">${v}%</span>
      </div>`).join('');

    document.getElementById('rStr').innerHTML = (d.strengths || []).map(s => `<li>${s}</li>`).join('');
    document.getElementById('rImp').innerHTML = (d.areas_to_improve || []).map(a => `<li><strong>${a.area}</strong> — ${a.fix || a.gap}</li>`).join('');
    document.getElementById('rBest').innerHTML = `<div class="hl-label" style="color:var(--green)">STRONGEST</div>${d.best_answer || '—'}`;
    document.getElementById('rWeak').innerHTML = `<div class="hl-label" style="color:var(--red)">NEEDS WORK</div>${d.weakest_answer || '—'}`;
    document.getElementById('rNext').innerHTML = (d.next_steps || []).map(s => `<li>${s}</li>`).join('');

    document.getElementById('mockChat').classList.add('hidden');
    document.getElementById('mockReport').classList.remove('hidden');
    document.getElementById('mockEndBtn').classList.add('hidden');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

function resetMock() {
  document.getElementById('mockReport').classList.add('hidden');
  document.getElementById('mockSetup').classList.remove('hidden');
  document.getElementById('mockStats').classList.add('hidden');
  document.getElementById('mockEndBtn').classList.add('hidden');
}

// ── Resume Optimizer ──────────────────────────────────────────────────────

async function runResumeAnalysis() {
  const jd = document.getElementById('resJD').value.trim();
  const resume = document.getElementById('resText').value.trim();
  if (!jd || !resume) { alert('Paste both the job description and your resume.'); return; }

  load('Scoring resume against JD...');
  try {
    const raw = await ai(`Senior technical recruiter. Score resume vs JD.
JD: """${jd}"""
Resume: """${resume}"""

Return ONLY valid JSON:
{"match_score":72,"match_label":"Moderate match","matched_skills":[],"missing_skills":[{"skill":"","importance":"required","suggestion":""}],"weak_sections":[{"section":"","issue":"","fix":""}],"rewrite_bullets":[{"original":"","rewritten":""}],"overall_advice":""}`);

    const d = JSON.parse(raw);
    const score = d.match_score || 0;
    document.getElementById('resScore').textContent = score + '%';
    document.getElementById('resScore').style.color = score >= 75 ? 'var(--green)' : score >= 50 ? 'var(--amber)' : 'var(--red)';
    document.getElementById('resLabel').textContent = d.match_label || '—';
    document.getElementById('resGaps').textContent = (d.missing_skills || []).length;
    document.getElementById('resJobDisplay').textContent = document.getElementById('resJobTitle').value;

    document.getElementById('resMatched').innerHTML = (d.matched_skills || []).map(s => `<span class="tag tag-green" style="margin:3px">${s}</span>`).join('');

    document.getElementById('resMissing').innerHTML = (d.missing_skills || []).map(s => `
      <div style="padding:7px 0;border-bottom:1px solid var(--b1)">
        <div class="flex gap-8"><span class="tag tag-${s.importance === 'required' ? 'red' : 'amber'}">${s.importance}</span><span style="font-size:13px;font-weight:500">${s.skill}</span></div>
        <div style="font-size:12px;color:var(--t3);margin-top:3px">${s.suggestion}</div>
      </div>`).join('');

    document.getElementById('resRewrites').innerHTML = (d.rewrite_bullets || []).map(b => `
      <div style="margin-bottom:12px">
        <div class="diff-label">Before</div><div class="diff-before">${b.original}</div>
        <div class="diff-label" style="color:var(--green)">After</div><div class="diff-after">${b.rewritten}</div>
      </div>`).join('');

    document.getElementById('resWeak').innerHTML = (d.weak_sections || []).map(s => `
      <div style="padding:8px 0;border-bottom:1px solid var(--b1)">
        <span class="tag tag-amber">${s.section}</span>
        <div style="font-size:13px;color:var(--t2);margin-top:5px">${s.issue}</div>
        <div style="font-size:12px;color:var(--green);margin-top:3px">→ ${s.fix}</div>
      </div>`).join('');

    document.getElementById('resAdvice').textContent = d.overall_advice || '';
    resetSect('resumeResults', 'resumeSetup');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

// ── Skill Map (Upskill) ───────────────────────────────────────────────────

async function runSkillMap() {
  const role = document.getElementById('upRole').value.trim();
  const goal = document.getElementById('upGoal').value.trim();
  if (!role || !goal) { alert('Fill in your current role and goal.'); return; }

  load('Mapping your skills...');
  try {
    const raw = await ai(`Senior career coach. Skill map. Role: "${role}". Goal: "${goal}". Track: ${getChip('upTrackChips')}. Skills: "${document.getElementById('upSkills').value}".

Return ONLY valid JSON:
{"current_level":"","target_role":"","skill_clusters":[{"cluster":"","skills":[{"name":"","current_level":"","target_level":"","gap":""}]}],"priority_skills":[{"skill":"","reason":"","estimated_hours":0}],"learning_sequence":[],"timeline_estimate":""}`);

    const d = JSON.parse(raw);
    _skillMapData = d;

    document.getElementById('upTargetRole').textContent = '→ ' + (d.target_role || goal);
    document.getElementById('upCurrentLevel').textContent = `${d.current_level || 'Current'} · ${d.timeline_estimate || ''}`;

    const gapColor = g => g === 'high' ? 'var(--red)' : g === 'medium' ? 'var(--amber)' : 'var(--green)';

    document.getElementById('upClusters').innerHTML = (d.skill_clusters || []).map(c => `
      <div style="margin-bottom:16px">
        <div style="font-size:11px;color:var(--t3);text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px">${c.cluster}</div>
        ${(c.skills || []).map(s => `
          <div class="skill-row">
            <div class="skill-name">${s.name}</div>
            <div style="flex:1;display:flex;flex-direction:column;gap:4px">
              <div style="display:flex;align-items:center;gap:7px;font-size:11px;color:var(--t3)">Now<div class="skill-bar-track" style="flex:1"><div class="skill-bar-fill" style="width:${lvlPct(s.current_level)}%;background:var(--mode)"></div></div></div>
              <div style="display:flex;align-items:center;gap:7px;font-size:11px;color:var(--t3)">Target<div class="skill-bar-track" style="flex:1"><div class="skill-bar-fill" style="width:${lvlPct(s.target_level)}%;background:var(--s5)"></div></div></div>
            </div>
            <span class="tag" style="background:${gapColor(s.gap)}20;color:${gapColor(s.gap)};min-width:52px;justify-content:center">${s.gap || 'ok'}</span>
          </div>`).join('')}
      </div>`).join('');

    document.getElementById('upPriority').innerHTML = (d.priority_skills || []).map((s, i) => `
      <div style="display:flex;gap:11px;align-items:flex-start;padding:9px 0;border-bottom:1px solid var(--b1)">
        <div style="width:20px;height:20px;border-radius:50%;background:var(--mode-d);border:1px solid var(--mode-b);color:var(--mode);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;flex-shrink:0;margin-top:1px">${i + 1}</div>
        <div style="flex:1"><div style="font-size:13px;font-weight:500">${s.skill}</div><div style="font-size:12px;color:var(--t3);margin-top:2px">${s.reason}</div></div>
        <div style="font-size:11.5px;color:var(--t3);white-space:nowrap">~${s.estimated_hours}h</div>
      </div>`).join('');

    document.getElementById('upSequence').innerHTML = (d.learning_sequence || []).map(s => `<li>${s}</li>`).join('');
    resetSect('upskillResults', 'upskillSetup');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

// ── Learning Plan ─────────────────────────────────────────────────────────

async function runLearningPlan() {
  const skill = document.getElementById('cpSkill').value.trim();
  if (!skill) { alert('Enter what to learn.'); return; }
  const role = document.getElementById('cpRole').value.trim();
  const timeline = getChip('cpTimelineChips') || '8';
  const hours = getChip('cpHoursChips') || '5';

  load('Building your plan...');
  try {
    const raw = await ai(`Senior learning designer. Plan for: "${skill}". Context: "${role}". ${timeline} weeks, ${hours}h/week.

Return ONLY valid JSON:
{"plan_title":"","goal_statement":"","phases":[{"phase":1,"name":"","weeks":"","focus":"","sessions":[{"week":1,"topic":"","type":"concept","hours":${hours},"metalearn_prompt":"","milestone":""}]}],"checkpoints":[{"week":4,"checkpoint":""}],"success_metrics":[]}`);

    const d = JSON.parse(raw);
    document.getElementById('cpTitle').textContent = d.plan_title || 'Plan';
    document.getElementById('cpGoal').textContent = d.goal_statement || '';

    document.getElementById('cpPhases').innerHTML = (d.phases || []).map(p => `
      <div class="plan-phase">
        <div class="phase-label"><span class="phase-num">Phase ${p.phase}</span><span style="font-size:14px;font-weight:600">${p.name}</span><span style="font-size:12px;color:var(--t3)">Weeks ${p.weeks}</span></div>
        <div style="font-size:12.5px;color:var(--t3);margin-bottom:10px">${p.focus}</div>
        ${(p.sessions || []).map(s => `
          <div class="week-card" onclick="this.classList.toggle('open')">
            <div class="week-header">
              <div><span class="week-topic">Week ${s.week}: ${s.topic}</span><span class="tag tag-${s.type === 'applied' ? 'green' : 'career'}" style="margin-left:8px">${s.type}</span></div>
              <span style="font-size:11.5px;color:var(--t2)">${s.hours}h</span>
            </div>
            <div class="week-body">
              <div style="margin-bottom:8px"><div style="font-size:10px;color:var(--t3);margin-bottom:3px">MILESTONE</div><div style="font-size:13px">${s.milestone}</div></div>
              <div style="margin-bottom:10px"><div style="font-size:10px;color:var(--mode);margin-bottom:4px">METALEARN PROMPT</div><div class="hl hl-mode" style="font-size:12.5px">${s.metalearn_prompt}</div></div>
              <button class="btn btn-academic btn-sm" onclick="event.stopPropagation();jumpToAcademicSession('${s.topic.replace(/'/g, "\\'")}')">Start session →</button>
            </div>
          </div>`).join('')}
      </div>`).join('');

    document.getElementById('cpChecks').innerHTML = (d.checkpoints || []).map(c => `
      <div style="display:flex;gap:10px;align-items:center;padding:7px 0;border-bottom:1px solid var(--b1)">
        <div style="background:var(--s4);color:var(--t2);padding:2px 8px;border-radius:20px;font-size:11px;white-space:nowrap">Wk ${c.week}</div>
        <div style="font-size:13px">${c.checkpoint}</div>
      </div>`).join('');

    document.getElementById('cpMetrics').innerHTML = (d.success_metrics || []).map(m => `<li>${m}</li>`).join('');
    resetSect('careerPlanResults', 'careerPlanSetup');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}

function jumpToAcademicSession(topic) {
  showMode('academic');
  showView('acad-session');
  setTimeout(() => { const el = document.getElementById('acadTopic'); if (el) el.value = topic; }, 50);
}

// ── Salary Intel ──────────────────────────────────────────────────────────

async function runSalaryIntel() {
  const role = document.getElementById('salRole').value.trim();
  if (!role) { alert('Enter a role.'); return; }

  load('Researching salary data...');
  try {
    const raw = await ai(`Compensation specialist. Salary intel.
Role: "${role}". Company/industry: "${document.getElementById('salCompany').value}". Location: "${document.getElementById('salLocation').value}". Experience: ${document.getElementById('salYears').value || 3} years. Situation: "${document.getElementById('salContext').value}".

Return ONLY valid JSON:
{"p25_salary":"","median_salary":"","p75_salary":"","compensation_breakdown":{"base":"","bonus":"","equity":"","total_comp":""},"negotiation_strategy":"","negotiation_tactics":[{"tactic":"","detail":""}],"scripts":[{"scenario":"","script":""}]}`);

    const d = JSON.parse(raw);
    document.getElementById('salTitle').textContent = role + ' — Salary Intel';
    document.getElementById('salP25').textContent = d.p25_salary || '—';
    document.getElementById('salMed').textContent = d.median_salary || '—';
    document.getElementById('salP75').textContent = d.p75_salary || '—';

    document.getElementById('salBreakdown').innerHTML = Object.entries(d.compensation_breakdown || {}).map(([k, v]) => `
      <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--b1);font-size:13px">
        <span style="color:var(--t2);text-transform:capitalize">${k.replace(/_/g, ' ')}</span><span style="font-weight:500">${v}</span>
      </div>`).join('') + `<div style="margin-top:10px;font-size:13.5px;color:var(--t2);line-height:1.6">${d.negotiation_strategy || ''}</div>`;

    document.getElementById('salTactics').innerHTML = (d.negotiation_tactics || []).map(t => `
      <div style="padding:9px 0;border-bottom:1px solid var(--b1)">
        <div style="font-size:13px;font-weight:500">${t.tactic}</div><div style="font-size:12.5px;color:var(--t2);margin-top:2px">${t.detail}</div>
      </div>`).join('');

    document.getElementById('salScripts').innerHTML = (d.scripts || []).map(s => `
      <div style="margin-bottom:12px">
        <div style="font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px">${s.scenario}</div>
        <div style="background:var(--s2);border-left:3px solid var(--mode);padding:9px 13px;border-radius:0 var(--rs) var(--rs) 0;font-size:13px;line-height:1.65;color:var(--t2);font-style:italic">"${s.script}"</div>
      </div>`).join('');

    resetSect('salaryResults', 'salarySetup');
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    unload();
  }
}
