// Inject all view HTML into the DOM
document.getElementById('views-container').innerHTML = `

<!-- HOME -->
<div class="view" id="view-home">
  <div class="content-scroll">
    <div style="max-width:700px;margin:0 auto;padding-top:8px">
      <div style="margin-bottom:32px">
        <div style="font-size:11px;color:var(--t3);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px">Based on MIT TLL Research · Pintrich · Schraw · Dunlosky · Tanner</div>
        <h1 style="font-family:'Instrument Serif',serif;font-size:34px;font-style:italic;letter-spacing:-.6px;line-height:1.15;margin-bottom:10px">You don't have a knowledge problem.<br>You have a <em style="color:var(--career)">calibration</em> problem.</h1>
        <p style="font-size:14.5px;color:var(--t2);max-width:520px;line-height:1.75">Most learners confuse familiarity with understanding. MetaLearn measures the gap between what you think you know and what you actually know — then closes it.</p>
      </div>
      <div class="grid-3 mb-20">
        <div class="mode-entry career-entry" onclick="showMode('career')">
          <div class="entry-content"><div class="entry-icon">🎯</div><div class="entry-title">Career</div><div class="entry-desc">Land the role. Grow beyond it. Mock interviews, resume gaps, skill maps, salary intel.</div><div class="entry-tags"><span class="tag tag-career">Interview prep</span><span class="tag tag-career">Upskill</span></div></div>
        </div>
        <div class="mode-entry academic-entry" onclick="showMode('academic')">
          <div class="entry-content"><div class="entry-icon">🎓</div><div class="entry-title">Academic</div><div class="entry-desc">Exams, concepts, problem-solving. Feynman scoring, misconception tracking, spaced repetition.</div><div class="entry-tags"><span class="tag tag-academic">Feynman test</span><span class="tag tag-academic">Exam prep</span></div></div>
        </div>
        <div class="mode-entry self-entry" onclick="showMode('self')">
          <div class="entry-content"><div class="entry-icon">🌱</div><div class="entry-title">Self-Learn</div><div class="entry-desc">Curiosity-driven learning. Rabbit holes, reflective journaling, idea connections across domains.</div><div class="entry-tags"><span class="tag tag-self">Reflection</span><span class="tag tag-self">Habits</span></div></div>
        </div>
      </div>
      <div class="card">
        <div style="font-size:11px;color:var(--t3);letter-spacing:.8px;text-transform:uppercase;margin-bottom:14px">The research behind every feature</div>
        <div class="grid-3">
          <div><div style="font-size:13px;font-weight:500;margin-bottom:4px">Familiarity ≠ Understanding</div><div style="font-size:12px;color:var(--t2);line-height:1.6">Students conflate familiarity with mastery. MetaLearn forces delayed retrieval to surface real gaps. (Dunlosky & Nelson, 1992)</div></div>
          <div><div style="font-size:13px;font-weight:500;margin-bottom:4px">Plan → Monitor → Evaluate</div><div style="font-size:12px;color:var(--t2);line-height:1.6">Every session embeds Schraw's self-regulation cycle through metacognitive prompts at the right moments. (Schraw, 1998)</div></div>
          <div><div style="font-size:13px;font-weight:500;margin-bottom:4px">Feynman as the real test</div><div style="font-size:12px;color:var(--t2);line-height:1.6">Explaining to a novice is the gold standard for understanding. We ML-score it on accuracy, depth, and transfer. (Tanner, 2012)</div></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- DASHBOARD -->
<div class="view" id="view-dashboard">
  <div class="topbar"><div class="topbar-title">Dashboard</div><div class="topbar-sub">— Your metacognitive profile</div></div>
  <div class="content-scroll">
    <div class="section-header"><div><div class="section-title">Career readiness</div><div class="section-sub">Confidence vs actual performance — the core metacognitive gap</div></div></div>
    <div class="grid-3 mb-16"><div class="score-card"><div class="score-big" style="color:var(--career)">3</div><div class="score-label">Mock interviews done</div></div><div class="score-card"><div class="score-big" style="color:var(--green)">74%</div><div class="score-label">Avg interview score</div></div><div class="score-card"><div class="score-big" style="color:var(--amber)">−12</div><div class="score-label">Confidence gap</div></div></div>
    <div class="hl hl-amber"><div class="hl-label" style="color:var(--amber)">Insight</div>You consistently rate yourself higher than your interview scores suggest. Biggest gap: system design depth. Focus there for maximum ROI before the next interview.</div>
  </div>
</div>

<!-- ═══ CAREER VIEWS ═══ -->

<!-- JD Analysis -->
<div class="view" id="view-jd-analysis">
  <div class="topbar"><div class="topbar-title">JD Analysis</div><div class="topbar-sub">— Role intelligence</div></div>
  <div class="content-scroll">
    <div id="jdSetup">
      <div class="section-header"><div><div class="section-title">What role are you targeting?</div><div class="section-sub">Paste a full job description for the most accurate analysis.</div></div></div>
      <div class="grid-2" style="gap:20px;align-items:start;max-width:700px">
        <div>
          <div class="field"><label class="field-label">Job title *</label><input class="input" id="jdTitle" placeholder="Senior Software Engineer"></div>
          <div class="field"><label class="field-label">Target company</label><input class="input" id="jdCompany" placeholder="Stripe, Google, a startup..."></div>
          <div class="field"><label class="field-label">Interview stage</label>
            <div class="chips" id="stageChips">
              <div class="chip sel" data-val="applied">Just applied</div>
              <div class="chip" data-val="screening">Phone screen</div>
              <div class="chip" data-val="technical">Technical round</div>
              <div class="chip" data-val="final">Final round</div>
            </div>
          </div>
        </div>
        <div><div class="field"><label class="field-label">Full job description <span style="color:var(--t3)">(paste for best results)</span></label><textarea class="input textarea" id="jdText" style="min-height:210px" placeholder="We're looking for a Senior Engineer..."></textarea></div></div>
      </div>
      <div class="flex gap-8 mt-16"><button class="btn btn-career" onclick="runJDAnalysis()">Analyse role →</button><button class="btn btn-ghost" onclick="runJDAnalysis(true)">Quick start (no JD)</button></div>
    </div>
    <div id="jdResults" class="hidden">
      <div class="section-header"><div><div class="section-title" id="jdResTitle">Analysis</div><div class="section-sub" id="jdResComp"></div></div><button class="btn btn-ghost btn-sm" onclick="resetSect('jdSetup','jdResults')">← Change role</button></div>
      <div class="hl hl-mode mb-16" id="jdSummaryBox" style="display:none"><div class="hl-label" style="color:var(--career)">Role summary</div><div id="jdSummaryTxt"></div></div>
      <div class="grid-2 mb-16"><div class="card"><div class="card-title mb-12">Required skills</div><div id="jdReqSkills"></div></div><div class="card"><div class="card-title mb-12">Likely interview topics</div><div id="jdTopics"></div></div></div>
      <div class="card mb-16"><div class="card-title mb-12">Skills to build before the interview</div><div id="jdSkillsBuild"></div></div>
      <div class="hl hl-amber mb-16" id="jdRedFlags" style="display:none"><div class="hl-label" style="color:var(--amber)">⚠ Worth noting</div><div id="jdRedFlagsTxt"></div></div>
      <div class="card"><div class="card-title mb-14">Next step</div>
        <div class="grid-3">
          <div class="mode-entry career-entry" onclick="showView('mock-interview');preFillMock()" style="padding:14px"><div class="entry-content"><div style="font-size:18px;margin-bottom:6px">🎙</div><div style="font-size:13px;font-weight:600">Mock Interview</div><div class="card-sub mt-8">Practice the real questions</div></div></div>
          <div class="mode-entry career-entry" onclick="showView('resume');preFillResume()" style="padding:14px"><div class="entry-content"><div style="font-size:18px;margin-bottom:6px">📄</div><div style="font-size:13px;font-weight:600">Resume Optimizer</div><div class="card-sub mt-8">Score resume vs this JD</div></div></div>
          <div class="mode-entry career-entry" onclick="showView('career-plan');preFillPlan()" style="padding:14px"><div class="entry-content"><div style="font-size:18px;margin-bottom:6px">🗺</div><div style="font-size:13px;font-weight:600">Learning Plan</div><div class="card-sub mt-8">Build the missing skills</div></div></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Mock Interview -->
<div class="view" id="view-mock-interview">
  <div class="topbar"><div class="topbar-title">Mock Interview</div><div class="topbar-sub" id="mockSubtitle">— Configure below</div><div class="topbar-right"><span id="mockStats" class="hidden" style="font-size:12px;color:var(--t2)">Q <strong id="mockQ">1</strong>/6</span><button class="btn btn-ghost btn-sm hidden" id="mockEndBtn" onclick="endMockInterview()">End & score →</button></div></div>
  <div id="mockSetup" class="content-scroll">
    <div class="section-header"><div><div class="section-title">Set up your mock interview</div><div class="section-sub">One question at a time. The AI probes shallow answers and gives feedback after each response.</div></div></div>
    <div class="grid-2" style="gap:20px;max-width:680px;align-items:start">
      <div>
        <div class="field"><label class="field-label">Role *</label><input class="input" id="mockRole" placeholder="Senior Software Engineer"></div>
        <div class="field"><label class="field-label">Company</label><input class="input" id="mockCompany" placeholder="Stripe"></div>
        <div class="field"><label class="field-label">Focus</label><div class="chips" id="mockFocusChips"><div class="chip sel" data-val="mixed">Mixed</div><div class="chip" data-val="behavioural">Behavioural</div><div class="chip" data-val="technical">Technical</div><div class="chip" data-val="system-design">System design</div></div></div>
        <div class="field"><label class="field-label">Level</label><div class="chips" id="mockLevelChips"><div class="chip" data-val="junior">Junior</div><div class="chip sel" data-val="mid">Mid</div><div class="chip" data-val="senior">Senior</div><div class="chip" data-val="staff">Staff/Lead</div></div></div>
      </div>
      <div>
        <div class="field"><label class="field-label">JD context <span style="color:var(--t3)">(optional)</span></label><textarea class="input textarea" id="mockJD" style="min-height:130px" placeholder="Paste JD for more relevant questions..."></textarea></div>
        <div class="field"><label class="field-label">Your background <span style="color:var(--t3)">(optional)</span></label><textarea class="input textarea" id="mockBG" style="min-height:70px" placeholder="Brief summary of experience..."></textarea></div>
      </div>
    </div>
    <button class="btn btn-career mt-8" onclick="startMockInterview()">Start interview →</button>
  </div>
  <div id="mockChat" class="hidden chat-shell">
    <div class="msgs" id="mockMsgs"></div>
    <div class="chat-input-area">
      <div class="chat-row"><textarea id="mockInput" placeholder="Answer the question..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMockMsg()}" oninput="autoResize(this)" rows="1"></textarea><button class="send-btn" id="mockSend" onclick="sendMockMsg()"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="white" stroke-width="2"><path d="M2 8L14 2L10 8L14 14Z"/></svg></button></div>
      <div style="margin-top:7px;font-size:11.5px;color:var(--t3)" id="mockHint">Answer fully — the AI probes shallow responses</div>
    </div>
  </div>
  <div id="mockReport" class="hidden content-scroll">
    <div class="section-header"><div><div class="section-title">Interview complete</div><div class="section-sub">Your full performance breakdown</div></div><button class="btn btn-ghost btn-sm" onclick="resetMock()">Practice again</button></div>
    <div class="grid-3 mb-16"><div class="score-card"><div class="score-big" id="rScore" style="color:var(--career)">—</div><div class="score-label">Overall</div></div><div class="score-card"><div class="score-big" id="rHire" style="font-size:18px;color:var(--green)">—</div><div class="score-label">Hire signal</div></div><div class="score-card"><div class="score-big" id="rCalib" style="font-size:16px;color:var(--amber)">—</div><div class="score-label">Calibration</div></div></div>
    <div class="grid-2 mb-16"><div class="card"><div class="card-title mb-12">Dimension scores</div><div id="rDims"></div></div><div class="card"><div class="card-title mb-12">Strengths</div><ul class="bl mb-12" id="rStr"></ul><div class="divider"></div><div class="card-title mb-12">Improve</div><ul class="bl" id="rImp"></ul></div></div>
    <div class="grid-2 mb-16"><div class="hl hl-green" id="rBest"></div><div class="hl hl-red" id="rWeak"></div></div>
    <div class="card"><div class="card-title mb-12">Next steps</div><ul class="bl" id="rNext"></ul></div>
  </div>
</div>

<!-- Resume -->
<div class="view" id="view-resume">
  <div class="topbar"><div class="topbar-title">Resume Optimizer</div><div class="topbar-sub">— Match and beat the JD</div></div>
  <div class="content-scroll">
    <div id="resumeSetup">
      <div class="section-header"><div><div class="section-title">Resume gap analysis</div><div class="section-sub">Paste both. We score the match and tell you exactly what to fix — with rewritten bullets.</div></div></div>
      <div class="grid-2" style="gap:20px;align-items:start">
        <div><div class="field"><label class="field-label">Role / company</label><input class="input" id="resJobTitle" placeholder="Senior Engineer at Stripe"></div><div class="field"><label class="field-label">Job description *</label><textarea class="input textarea" id="resJD" style="min-height:210px" placeholder="Paste full JD..."></textarea></div></div>
        <div><div class="field"><label class="field-label">Your resume *</label><textarea class="input textarea" id="resText" style="min-height:310px" placeholder="Paste resume as plain text..."></textarea></div></div>
      </div>
      <button class="btn btn-career mt-12" onclick="runResumeAnalysis()">Score my resume →</button>
    </div>
    <div id="resumeResults" class="hidden">
      <div class="section-header"><div><div class="section-title">Resume analysis</div><div class="section-sub" id="resJobDisplay"></div></div><button class="btn btn-ghost btn-sm" onclick="resetSect('resumeSetup','resumeResults')">← Analyse another</button></div>
      <div class="grid-3 mb-16"><div class="score-card"><div class="score-big" id="resScore" style="color:var(--career)">—</div><div class="score-label">Match score</div></div><div class="score-card"><div class="score-big" id="resLabel" style="font-size:16px;color:var(--green)">—</div><div class="score-label">Assessment</div></div><div class="score-card"><div class="score-big" id="resGaps" style="color:var(--red)">—</div><div class="score-label">Gaps to fix</div></div></div>
      <div class="grid-2 mb-16"><div class="card"><div class="card-title mb-12">✅ Matched skills</div><div id="resMatched"></div></div><div class="card"><div class="card-title mb-12">❌ Critical gaps</div><div id="resMissing"></div></div></div>
      <div class="card mb-16"><div class="card-title mb-14">🔧 Bullet rewrites — before & after</div><div id="resRewrites"></div></div>
      <div class="card mb-16"><div class="card-title mb-12">Weak sections</div><div id="resWeak"></div></div>
      <div class="hl hl-mode"><div class="hl-label" style="color:var(--career)">Coach advice</div><div id="resAdvice"></div></div>
    </div>
  </div>
</div>

<!-- Salary -->
<div class="view" id="view-salary">
  <div class="topbar"><div class="topbar-title">Salary Intel</div><div class="topbar-sub">— Know your worth</div></div>
  <div class="content-scroll">
    <div id="salarySetup">
      <div class="section-header"><div><div class="section-title">Salary & negotiation intel</div><div class="section-sub">Realistic ranges + word-for-word negotiation scripts for your situation.</div></div></div>
      <div style="max-width:460px">
        <div class="field"><label class="field-label">Role *</label><input class="input" id="salRole" placeholder="Senior Software Engineer"></div>
        <div class="field"><label class="field-label">Company / industry</label><input class="input" id="salCompany" placeholder="Fintech startup, FAANG, mid-size SaaS"></div>
        <div class="field"><label class="field-label">Location</label><input class="input" id="salLocation" placeholder="San Francisco, Remote US, London"></div>
        <div class="field"><label class="field-label">Years of experience</label><input class="input" id="salYears" type="number" placeholder="5" style="width:100px"></div>
        <div class="field"><label class="field-label">Your situation <span style="color:var(--t3)">(optional — massively improves advice)</span></label><textarea class="input textarea" id="salContext" placeholder="e.g. I have an offer for $130k. Competing offer at $145k. Want to negotiate..." style="min-height:70px"></textarea></div>
        <button class="btn btn-career mt-8" onclick="runSalaryIntel()">Get intel →</button>
      </div>
    </div>
    <div id="salaryResults" class="hidden">
      <div class="section-header"><div><div class="section-title" id="salTitle">Salary intel</div></div><button class="btn btn-ghost btn-sm" onclick="resetSect('salarySetup','salaryResults')">← New</button></div>
      <div class="grid-3 mb-16"><div class="score-card"><div class="score-big" id="salP25" style="font-size:22px;color:var(--t2)">—</div><div class="score-label">25th percentile</div></div><div class="score-card" style="border-color:var(--career-b)"><div class="score-big" id="salMed" style="font-size:22px;color:var(--career)">—</div><div class="score-label">Median</div></div><div class="score-card"><div class="score-big" id="salP75" style="font-size:22px;color:var(--green)">—</div><div class="score-label">75th percentile</div></div></div>
      <div class="card mb-16"><div class="card-title mb-12">Compensation breakdown</div><div id="salBreakdown"></div></div>
      <div class="card mb-16"><div class="card-title mb-12">Negotiation tactics</div><div id="salTactics"></div></div>
      <div class="card"><div class="card-title mb-12">Scripts to use word-for-word</div><div id="salScripts"></div></div>
    </div>
  </div>
</div>

<!-- Upskill -->
<div class="view" id="view-upskill">
  <div class="topbar"><div class="topbar-title">Skill Map</div><div class="topbar-sub">— Where you are, where you're going</div></div>
  <div class="content-scroll">
    <div id="upskillSetup">
      <div class="section-header"><div><div class="section-title">Map your path forward</div><div class="section-sub">Identify the real gaps and prioritise what to learn first.</div></div></div>
      <div class="grid-2" style="gap:20px;max-width:680px;align-items:start">
        <div>
          <div class="field"><label class="field-label">Current role *</label><input class="input" id="upRole" placeholder="Mid-level Frontend Engineer"></div>
          <div class="field"><label class="field-label">Your goal *</label><input class="input" id="upGoal" placeholder="Become a Senior Full-stack Engineer"></div>
          <div class="field"><label class="field-label">Track</label><div class="chips" id="upTrackChips"><div class="chip sel" data-val="deepen">Deepen expertise</div><div class="chip" data-val="branch">Branch into new area</div></div></div>
        </div>
        <div>
          <div class="field"><label class="field-label">Skills you have <span style="color:var(--t3)">(comma separated)</span></label><textarea class="input textarea" id="upSkills" style="min-height:90px" placeholder="React, TypeScript, Node.js, REST APIs..."></textarea></div>
          <div class="field"><label class="field-label">Hours available per week</label><div class="chips" id="upHoursChips"><div class="chip" data-val="3">3 hrs</div><div class="chip sel" data-val="5">5 hrs</div><div class="chip" data-val="10">10 hrs</div><div class="chip" data-val="15">15+</div></div></div>
        </div>
      </div>
      <button class="btn btn-career mt-12" onclick="runSkillMap()">Build skill map →</button>
    </div>
    <div id="upskillResults" class="hidden">
      <div class="section-header"><div><div class="section-title" id="upTargetRole">Skill map</div><div class="section-sub" id="upCurrentLevel"></div></div><button class="btn btn-ghost btn-sm" onclick="resetSect('upskillSetup','upskillResults')">← Change</button></div>
      <div class="card mb-16"><div class="card-title mb-14">Skill clusters</div><div id="upClusters"></div></div>
      <div class="card mb-16"><div class="card-title mb-12">Priority order</div><div id="upPriority"></div></div>
      <div class="hl hl-mode mb-16"><div class="hl-label" style="color:var(--career)">Learning sequence</div><ul class="bl" id="upSequence"></ul></div>
      <button class="btn btn-career" onclick="showView('career-plan');preFillPlanFromSkillMap()">Build learning plan →</button>
    </div>
  </div>
</div>

<!-- Career Plan -->
<div class="view" id="view-career-plan">
  <div class="topbar"><div class="topbar-title">Learning Plan</div><div class="topbar-sub">— Week by week</div></div>
  <div class="content-scroll">
    <div id="careerPlanSetup">
      <div class="section-header"><div><div class="section-title">Build your learning plan</div><div class="section-sub">Week-by-week structure with MetaLearn sessions built in at every step.</div></div></div>
      <div style="max-width:500px">
        <div class="field"><label class="field-label">What to learn *</label><input class="input" id="cpSkill" placeholder="Machine learning fundamentals"></div>
        <div class="field"><label class="field-label">Context</label><input class="input" id="cpRole" placeholder="Backend engineer moving into ML"></div>
        <div class="grid-2">
          <div class="field"><label class="field-label">Timeline</label><div class="chips" id="cpTimelineChips"><div class="chip" data-val="4">4 wks</div><div class="chip sel" data-val="8">8 wks</div><div class="chip" data-val="12">12 wks</div></div></div>
          <div class="field"><label class="field-label">Hours / week</label><div class="chips" id="cpHoursChips"><div class="chip" data-val="3">3 hrs</div><div class="chip sel" data-val="5">5 hrs</div><div class="chip" data-val="10">10 hrs</div></div></div>
        </div>
        <button class="btn btn-career mt-8" onclick="runLearningPlan()">Generate plan →</button>
      </div>
    </div>
    <div id="careerPlanResults" class="hidden">
      <div class="section-header"><div><div class="section-title" id="cpTitle">Plan</div><div class="section-sub" id="cpGoal"></div></div><button class="btn btn-ghost btn-sm" onclick="resetSect('careerPlanSetup','careerPlanResults')">← New plan</button></div>
      <div id="cpPhases"></div>
      <div class="card mt-16"><div class="card-title mb-12">Checkpoints</div><div id="cpChecks"></div></div>
      <div class="hl hl-mode mt-16"><div class="hl-label" style="color:var(--career)">Success metrics</div><ul class="bl" id="cpMetrics"></ul></div>
    </div>
  </div>
</div>

<!-- ═══ ACADEMIC VIEWS ═══ -->

<!-- Academic Session -->
<div class="view" id="view-acad-session">
  <div class="topbar">
    <div class="topbar-title">Learning Session</div>
    <div class="topbar-sub" id="acadSessionSub">— Set up below</div>
    <div class="topbar-right">
      <div class="stepper" id="acadStepper">
        <div class="step active" id="as-pre"><div class="sdot"></div>Pre</div><div class="step-line"></div>
        <div class="step" id="as-learn"><div class="sdot"></div>Learn</div><div class="step-line"></div>
        <div class="step" id="as-feynman"><div class="sdot"></div>Feynman</div><div class="step-line"></div>
        <div class="step" id="as-quiz"><div class="sdot"></div>Quiz</div><div class="step-line"></div>
        <div class="step" id="as-results"><div class="sdot"></div>Results</div>
      </div>
    </div>
  </div>
  <!-- Pre-learn -->
  <div id="acadPre" class="content-scroll">
    <div class="section-header"><div><div class="section-title">Before we start</div><div class="section-sub">Pre-assessment surfaces familiarity bias before it distorts learning. (Dunlosky & Nelson, 1992)</div></div></div>
    <div style="max-width:480px">
      <div class="field"><label class="field-label">Topic *</label><input class="input" id="acadTopic" placeholder="e.g. Backpropagation in neural networks"></div>
      <div class="field">
        <label class="field-label">How confident are you? <span style="color:var(--t3)">(honest estimate)</span></label>
        <div class="conf-wrap mt-12">
          <div class="conf-num" id="preConfNum">50%</div>
          <input type="range" class="conf-slider" min="0" max="100" value="50" id="preConfSlider" oninput="document.getElementById('preConfNum').textContent=this.value+'%';window._preConf=parseInt(this.value)">
          <div style="font-size:11.5px;color:var(--t3)">0 = no idea · 100 = expert</div>
        </div>
      </div>
      <div class="field"><label class="field-label">What do you already know? <span style="color:var(--t3)">(be specific — this detects misconceptions)</span></label><textarea class="input textarea" id="acadPrior" style="min-height:100px" placeholder="I know that backprop uses the chain rule..."></textarea></div>
      <button class="btn btn-academic mt-8" onclick="startAcadSession()">Begin session →</button>
    </div>
  </div>
  <!-- Learn chat -->
  <div id="acadLearn" class="hidden chat-shell">
    <div class="msgs" id="acadMsgs"></div>
    <div class="chat-input-area">
      <div class="chat-row"><textarea id="acadInput" placeholder="Ask a question or respond..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendAcadMsg()}" oninput="autoResize(this)" rows="1"></textarea><button class="send-btn" id="acadSend" onclick="sendAcadMsg()"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="white" stroke-width="2"><path d="M2 8L14 2L10 8L14 14Z"/></svg></button></div>
      <div style="display:flex;justify-content:space-between;margin-top:7px"><span style="font-size:11.5px;color:var(--t3)" id="acadMsgCount">0 exchanges</span><button class="btn btn-ghost btn-sm" onclick="goToFeynman()">Feynman test →</button></div>
    </div>
  </div>
  <!-- Feynman -->
  <div id="acadFeynman" class="hidden content-scroll">
    <div class="section-header"><div><div class="section-title">Feynman Test</div><div class="section-sub">Explain <strong id="feynmanTopicLabel"></strong> as if teaching a curious 12-year-old. No notes.</div></div></div>
    <textarea class="feynman-area" id="feynmanText" style="max-width:620px;display:block" placeholder="Start explaining in your own words...&#10;&#10;Don't copy what the AI taught you. Show you understood it."></textarea>
    <button class="btn btn-academic mt-12" onclick="scoreFeynman()">Submit for evaluation →</button>
    <div id="feynmanResult" class="hidden mt-20" style="max-width:620px">
      <div class="card">
        <div class="flex gap-16 mb-16">
          <div class="score-card" style="min-width:100px"><div class="score-big" id="feyScore" style="color:var(--academic)">—</div><div class="score-label">Feynman score</div></div>
          <div class="grid-2" id="feyDims" style="gap:8px;flex:1"></div>
        </div>
        <div class="hl hl-green mb-8" id="feyStrengths"></div>
        <div class="hl hl-amber mb-8" id="feyGaps"></div>
        <div class="hl hl-mode" id="feyNext"><div class="hl-label" style="color:var(--academic)">Next step</div><span id="feyNextTxt"></span></div>
        <button class="btn btn-academic mt-16" onclick="goToAcadQuiz()">Continue to quiz →</button>
      </div>
    </div>
  </div>
  <!-- Quiz -->
  <div id="acadQuiz" class="hidden content-scroll">
    <div style="max-width:560px">
      <div id="quizLoading" class="card" style="text-align:center;padding:32px"><div class="spinner" style="margin:0 auto 12px"></div><div style="color:var(--t2)">Generating questions from your session...</div></div>
      <div id="quizQuestion" class="hidden">
        <div style="font-size:11px;color:var(--t3);margin-bottom:14px" id="quizProg">Question 1 of 4</div>
        <div class="quiz-q" id="quizQText"></div>
        <div class="quiz-opts" id="quizOpts"></div>
      </div>
    </div>
  </div>
  <!-- Results -->
  <div id="acadResults" class="hidden content-scroll">
    <div class="section-header"><div><div class="section-title">Session complete</div><div class="section-sub" id="resultsTopicLabel"></div></div><button class="btn btn-ghost btn-sm" onclick="resetAcadSession()">New session</button></div>
    <div class="grid-3 mb-16"><div class="score-card"><div class="score-big" id="resFey" style="color:var(--academic)">—</div><div class="score-label">Feynman</div></div><div class="score-card"><div class="score-big" id="resQScore" style="color:var(--green)">—</div><div class="score-label">Quiz score</div></div><div class="score-card"><div class="score-big" id="resCalib" style="color:var(--amber)">—</div><div class="score-label">Calibration Δ</div></div></div>
    <div class="hl hl-mode mb-16" id="resCalibInsight"></div>
    <div id="resMiscSection" class="card mb-16 hidden"><div class="card-title mb-12">⚠ Detected misconceptions</div><div id="resMiscList"></div></div>
    <div class="card"><div class="card-title mb-12">Next review (spaced repetition)</div><div id="resNextReview"></div></div>
  </div>
</div>

<!-- Exam Wrapper -->
<div class="view" id="view-exam-wrapper">
  <div class="topbar"><div class="topbar-title">Exam Wrapper</div><div class="topbar-sub">— Post-exam metacognitive analysis (Lovett, 2016)</div></div>
  <div class="content-scroll">
    <div id="ewSetup">
      <div class="section-header"><div><div class="section-title">Post-exam reflection</div><div class="section-sub">Find what actually went wrong — not just what felt wrong. Used at MIT to improve future exam performance.</div></div></div>
      <div style="max-width:560px">
        <div class="field"><label class="field-label">Subject / exam *</label><input class="input" id="ewSubject" placeholder="Organic Chemistry Midterm"></div>
        <div class="grid-2"><div class="field"><label class="field-label">Your score</label><input class="input" id="ewScore" placeholder="67%" style="width:130px"></div><div class="field"><label class="field-label">Expected score (before results)</label><input class="input" id="ewExpected" placeholder="80%" style="width:130px"></div></div>
        <div class="field"><label class="field-label">How did you study? *</label><textarea class="input textarea" id="ewStudy" placeholder="Re-reading, practice problems, flashcards, group study..." style="min-height:80px"></textarea></div>
        <div class="field"><label class="field-label">Which topics gave you trouble?</label><textarea class="input textarea" id="ewTrouble" placeholder="Nucleophilic substitution, especially SN2 stereochemistry..." style="min-height:70px"></textarea></div>
        <div class="field"><label class="field-label">Why do you think those went wrong?</label><textarea class="input textarea" id="ewWhy" placeholder="I recognised the terms but couldn't apply them to novel problems..." style="min-height:70px"></textarea></div>
        <button class="btn btn-academic mt-8" onclick="runExamWrapper()">Analyse my exam →</button>
      </div>
    </div>
    <div id="ewResults" class="hidden">
      <div class="section-header"><div><div class="section-title" id="ewResTitle">Exam analysis</div></div><button class="btn btn-ghost btn-sm" onclick="resetSect('ewSetup','ewResults')">← New</button></div>
      <div class="hl hl-mode mb-16" id="ewDiagnosis"></div>
      <div class="grid-2 mb-16"><div class="card"><div class="card-title mb-12">What actually went wrong</div><div id="ewWhatWrong"></div></div><div class="card"><div class="card-title mb-12">Study strategy analysis</div><div id="ewStrategy"></div></div></div>
      <div class="card mb-16"><div class="card-title mb-12">What to do differently next time</div><ul class="bl" id="ewDoDiff"></ul></div>
      <div class="hl hl-amber"><div class="hl-label" style="color:var(--amber)">Metacognitive insight</div><div id="ewMeta"></div></div>
    </div>
  </div>
</div>

<!-- Spaced Rep -->
<div class="view" id="view-spaced-rep">
  <div class="topbar"><div class="topbar-title">Review Queue</div><div class="topbar-sub">— SM-2 spaced repetition</div></div>
  <div class="content-scroll">
    <div class="section-header"><div><div class="section-title">3 concepts due today</div><div class="section-sub">Based on your calibration error — concepts where you were most overconfident get reviewed first.</div></div></div>
    <div style="max-width:520px">
      <div class="card mb-8" style="border-color:var(--red-d)"><div class="flex gap-12"><div style="background:var(--red-d);color:var(--red);padding:2px 9px;border-radius:20px;font-size:11px">Overdue 2d</div><div style="font-size:13.5px;font-weight:500">Gradient descent optimisation</div></div><div style="font-size:12px;color:var(--t2);margin-top:6px">Last score: 60% · You predicted 80% → calibration gap of 20pts</div><button class="btn btn-academic btn-sm mt-8" onclick="showView('acad-session');document.getElementById('acadTopic').value='Gradient descent optimisation'">Review now →</button></div>
      <div class="card mb-8"><div class="flex gap-12"><div style="background:var(--amber-d);color:var(--amber);padding:2px 9px;border-radius:20px;font-size:11px">Due today</div><div style="font-size:13.5px;font-weight:500">Attention mechanisms in transformers</div></div><div style="font-size:12px;color:var(--t2);margin-top:6px">Last score: 75% · 1 misconception still open</div><button class="btn btn-academic btn-sm mt-8" onclick="showView('acad-session');document.getElementById('acadTopic').value='Attention mechanisms in transformers'">Review now →</button></div>
      <div class="card mb-8"><div class="flex gap-12"><div style="background:var(--green-d);color:var(--green);padding:2px 9px;border-radius:20px;font-size:11px">Due today</div><div style="font-size:13.5px;font-weight:500">Bias-variance tradeoff</div></div><div style="font-size:12px;color:var(--t2);margin-top:6px">Last score: 88% · Well calibrated</div><button class="btn btn-academic btn-sm mt-8" onclick="showView('acad-session');document.getElementById('acadTopic').value='Bias-variance tradeoff'">Review now →</button></div>
    </div>
  </div>
</div>

<!-- Misconceptions -->
<div class="view" id="view-misconceptions">
  <div class="topbar"><div class="topbar-title">Misconceptions</div><div class="topbar-sub">— Persistent misunderstandings across sessions</div></div>
  <div class="content-scroll"><div id="miscList"><div class="card" style="color:var(--t3);text-align:center;padding:40px">No misconceptions tracked yet. Complete a learning session to begin.</div></div></div>
</div>

<!-- Upload -->
<div class="view" id="view-acad-upload">
  <div class="topbar"><div class="topbar-title">Upload Material</div><div class="topbar-sub">— PDF, notes, URLs</div></div>
  <div class="content-scroll">
    <div class="section-header"><div><div class="section-title">Add learning material</div><div class="section-sub">Upload a PDF or paste notes. MetaLearn will use it as context for your learning session.</div></div></div>
    <div style="max-width:480px">
      <div class="field"><label class="field-label">Topic name</label><input class="input" id="uploadTopicName" placeholder="e.g. Attention Is All You Need (paper)"></div>
      <div class="field"><label class="field-label">Paste content</label><textarea class="input textarea" id="uploadContent" style="min-height:200px" placeholder="Paste your notes, article, or extracted PDF text here..."></textarea></div>
      <button class="btn btn-academic mt-8" onclick="saveUploadedMaterial()">Save & use in session →</button>
    </div>
  </div>
</div>

<!-- Feynman standalone -->
<div class="view" id="view-feynman">
  <div class="topbar"><div class="topbar-title">Feynman Test</div><div class="topbar-sub">— Test any concept, anytime</div></div>
  <div class="content-scroll">
    <div class="section-header"><div><div class="section-title">Explain it from scratch</div><div class="section-sub">Named after Richard Feynman: if you can't explain it simply, you don't understand it yet.</div></div></div>
    <div style="max-width:620px">
      <div class="field"><label class="field-label">Concept to test *</label><input class="input" id="standaloneFeynmanTopic" placeholder="e.g. How does HTTPS work?"></div>
      <div class="field"><label class="field-label">Your explanation</label><textarea class="feynman-area" id="standaloneFeynmanText" style="min-height:180px" placeholder="Explain it as if teaching a smart 12-year-old with no background in the subject..."></textarea></div>
      <button class="btn btn-academic mt-8" onclick="runStandaloneFeynman()">Score my explanation →</button>
      <div id="standaloneFeynmanResult" class="hidden mt-20">
        <div class="card">
          <div class="flex gap-16 mb-16"><div class="score-card" style="min-width:100px"><div class="score-big" id="sfScore" style="color:var(--academic)">—</div><div class="score-label">Score</div></div><div class="grid-2" id="sfDims" style="flex:1;gap:8px"></div></div>
          <div class="hl hl-green mb-8" id="sfStr"></div>
          <div class="hl hl-amber mb-8" id="sfGaps"></div>
          <div class="hl hl-mode"><div class="hl-label" style="color:var(--academic)">Next step</div><span id="sfNext"></span></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Quiz standalone -->
<div class="view" id="view-acad-quiz">
  <div class="topbar"><div class="topbar-title">Quiz Me</div><div class="topbar-sub">— On-demand testing</div></div>
  <div class="content-scroll">
    <div id="sqSetup"><div class="section-header"><div><div class="section-title">Generate a quiz</div><div class="section-sub">Testing beats re-reading. Generate a quiz on any topic to surface real gaps.</div></div></div>
    <div style="max-width:400px"><div class="field"><label class="field-label">Topic *</label><input class="input" id="sqTopic" placeholder="Convolutional neural networks"></div><div class="field"><label class="field-label">Difficulty</label><div class="chips" id="sqDiffChips"><div class="chip" data-val="easy">Easy</div><div class="chip sel" data-val="medium">Medium</div><div class="chip" data-val="hard">Hard</div></div></div><button class="btn btn-academic mt-8" onclick="runStandaloneQuiz()">Generate quiz →</button></div></div>
    <div id="sqQuiz" class="hidden" style="max-width:560px"><div style="font-size:11px;color:var(--t3);margin-bottom:14px" id="sqProg">Question 1 of 5</div><div class="quiz-q" id="sqQText"></div><div class="quiz-opts" id="sqOpts"></div></div>
    <div id="sqResults" class="hidden" style="max-width:560px">
      <div class="section-header"><div><div class="section-title">Quiz results</div></div><button class="btn btn-ghost btn-sm" onclick="resetSect('sqSetup','sqResults');document.getElementById('sqQuiz').classList.add('hidden')">Try another</button></div>
      <div class="grid-2"><div class="score-card"><div class="score-big" id="sqScore" style="color:var(--academic)">—</div><div class="score-label">Score</div></div><div class="score-card"><div class="score-big" id="sqCalibLabel" style="font-size:16px;color:var(--amber)">—</div><div class="score-label">Calibration</div></div></div>
    </div>
  </div>
</div>

<!-- ═══ SELF-LEARN VIEWS ═══ -->

<!-- Self Session -->
<div class="view" id="view-self-session">
  <div class="topbar"><div class="topbar-title">Curiosity Session</div><div class="topbar-sub" id="selfSessionSub">— What are you curious about?</div><div class="topbar-right"><button class="btn btn-ghost btn-sm hidden" id="selfEndBtn" onclick="endSelfSession()">Reflect on this →</button></div></div>
  <div id="selfSetup" class="content-scroll">
    <div class="section-header"><div><div class="section-title">What do you want to explore?</div><div class="section-sub">No syllabus. No exam. Just genuine curiosity — with rigorous metacognitive measurement underneath.</div></div></div>
    <div style="max-width:480px">
      <div class="field"><label class="field-label">Topic or question *</label><input class="input" id="selfTopic" placeholder="Why does democracy keep producing polarisation?"></div>
      <div class="field"><label class="field-label">What drew you to this?</label><textarea class="input textarea" id="selfWhy" style="min-height:70px" placeholder="I read an article that mentioned..."></textarea></div>
      <div class="field"><label class="field-label">What do you already think you know?</label><textarea class="input textarea" id="selfPrior" style="min-height:70px" placeholder="I think it's related to..."></textarea></div>
      <div class="field"><label class="field-label">Depth goal</label><div class="chips" id="selfDepthChips"><div class="chip sel" data-val="intro">Introductory</div><div class="chip" data-val="solid">Solid understanding</div><div class="chip" data-val="deep">Deep / expert</div></div></div>
      <button class="btn btn-self mt-8" onclick="startSelfSession()">Start exploring →</button>
    </div>
  </div>
  <div id="selfLearn" class="hidden chat-shell">
    <div class="msgs" id="selfMsgs"></div>
    <div class="chat-input-area">
      <div class="chat-row"><textarea id="selfInput" placeholder="Ask, wonder, push back..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendSelfMsg()}" oninput="autoResize(this)" rows="1"></textarea><button class="send-btn" id="selfSend" onclick="sendSelfMsg()"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="white" stroke-width="2"><path d="M2 8L14 2L10 8L14 14Z"/></svg></button></div>
      <div style="margin-top:7px;font-size:11.5px;color:var(--t3)">Disagree if something seems wrong. The AI won't let shallow thinking slide.</div>
    </div>
  </div>
  <div id="selfReflect" class="hidden content-scroll">
    <div class="section-header"><div><div class="section-title">Reflection</div><div class="section-sub">Plan → Monitor → Evaluate — the self-regulation loop. (Schraw, 1998)</div></div></div>
    <div style="max-width:560px">
      <div class="field"><label class="field-label">What genuinely surprised you?</label><textarea class="input textarea" id="refSurprise" style="min-height:80px" placeholder="I didn't expect that..."></textarea></div>
      <div class="field"><label class="field-label">Where are you still unclear?</label><textarea class="input textarea" id="refUnclear" style="min-height:80px" placeholder="I'm still fuzzy on..."></textarea></div>
      <div class="field"><label class="field-label">How does this connect to something you already knew?</label><textarea class="input textarea" id="refConnect" style="min-height:80px" placeholder="This reminds me of..."></textarea></div>
      <button class="btn btn-self mt-8" onclick="scoreReflection()">Score my reflection →</button>
    </div>
    <div id="reflectResult" class="hidden mt-16" style="max-width:560px">
      <div class="grid-3 mb-16"><div class="score-card"><div class="score-big" id="refScore" style="color:var(--self)">—</div><div class="score-label">Reflection quality</div></div><div class="score-card"><div class="score-big" id="refDepth" style="font-size:22px;color:var(--academic)">—</div><div class="score-label">Depth</div></div><div class="score-card"><div class="score-big" id="refTransfer" style="font-size:22px;color:var(--career)">—</div><div class="score-label">Transfer</div></div></div>
      <div class="hl hl-mode mb-8"><div class="hl-label" style="color:var(--self)">Feedback</div><div id="refFeedback"></div></div>
      <div class="hl hl-amber"><div class="hl-label" style="color:var(--amber)">Muddiest point — investigate next</div><div id="refMuddiest"></div></div>
      <div class="flex gap-8 mt-12"><button class="btn btn-self" onclick="showView('journal')">Add to journal →</button><button class="btn btn-ghost" onclick="resetSelfSession()">Done</button></div>
    </div>
  </div>
</div>

<!-- Rabbit Hole -->
<div class="view" id="view-rabbit-hole">
  <div class="topbar"><div class="topbar-title">Rabbit Hole</div><div class="topbar-sub">— Follow the idea wherever it leads</div></div>
  <div class="content-scroll">
    <div id="rhSetup"><div class="section-header"><div><div class="section-title">Start with any idea</div><div class="section-sub">The AI maps where it leads, what it connects to, and what's worth exploring next.</div></div></div>
    <div style="max-width:480px"><div class="field"><label class="field-label">Starting idea *</label><input class="input" id="rhIdea" placeholder="Why does music make us emotional?"></div><button class="btn btn-self mt-8" onclick="runRabbitHole()">Explore →</button></div></div>
    <div id="rhResult" class="hidden">
      <div class="section-header"><div><div class="section-title" id="rhTitle">Rabbit hole</div></div><button class="btn btn-ghost btn-sm" onclick="resetSect('rhSetup','rhResult')">← New</button></div>
      <div class="card mb-16"><div class="card-title mb-12">The core idea</div><div id="rhCore" style="font-size:13.5px;line-height:1.75;color:var(--t2)"></div></div>
      <div class="card mb-16"><div class="card-title mb-12">5 threads to pull</div><div id="rhThreads"></div></div>
      <div class="card mb-16"><div class="card-title mb-12">Unexpected connections</div><div id="rhConnections"></div></div>
      <div class="hl hl-mode"><div class="hl-label" style="color:var(--self)">Best next session</div><div id="rhNext"></div></div>
    </div>
  </div>
</div>

<!-- Idea Connections -->
<div class="view" id="view-connections">
  <div class="topbar"><div class="topbar-title">Idea Connections</div><div class="topbar-sub">— Transfer is the highest form of understanding</div></div>
  <div class="content-scroll">
    <div id="connSetup"><div class="section-header"><div><div class="section-title">Find the link</div><div class="section-sub">Enter two ideas from different domains. Transfer between domains is the mark of deep understanding. (Tanner, 2012)</div></div></div>
    <div style="max-width:480px"><div class="field"><label class="field-label">Idea A</label><input class="input" id="connA" placeholder="Natural selection"></div><div class="field"><label class="field-label">Idea B</label><input class="input" id="connB" placeholder="Machine learning gradient descent"></div><button class="btn btn-self mt-8" onclick="runConnections()">Find connections →</button></div></div>
    <div id="connResult" class="hidden">
      <div class="section-header"><div><div class="section-title" id="connTitle">Connections</div></div><button class="btn btn-ghost btn-sm" onclick="resetSect('connSetup','connResult')">← New</button></div>
      <div class="card mb-16"><div class="card-title mb-12">The deep connection</div><div id="connCore" style="font-size:13.5px;line-height:1.75;color:var(--t2)"></div></div>
      <div class="grid-2 mb-16"><div class="card"><div class="card-title mb-12">Structural similarities</div><ul class="bl" id="connSimilar"></ul></div><div class="card"><div class="card-title mb-12">Key differences</div><ul class="bl" id="connDiff"></ul></div></div>
      <div class="hl hl-mode"><div class="hl-label" style="color:var(--self)">What this transfer insight reveals</div><div id="connInsight"></div></div>
    </div>
  </div>
</div>

<!-- Journal -->
<div class="view" id="view-journal">
  <div class="topbar"><div class="topbar-title">Learning Journal</div><div class="topbar-sub">— Your private thinking record</div><div class="topbar-right"><button class="btn btn-self btn-sm" onclick="addJournalEntry()">+ Entry</button></div></div>
  <div class="content-scroll">
    <div id="journalCompose" class="hidden mb-16"><div class="card"><div class="field"><label class="field-label">What did you learn or think about today?</label><textarea class="input textarea" id="journalText" style="min-height:120px" placeholder="Today I explored... what surprised me was... I'm still wondering about..."></textarea></div><div class="flex gap-8"><button class="btn btn-self btn-sm" onclick="saveJournalEntry()">Save entry</button><button class="btn btn-ghost btn-sm" onclick="document.getElementById('journalCompose').classList.add('hidden')">Cancel</button></div></div></div>
    <div id="journalEntries"><div style="color:var(--t3);text-align:center;padding:40px;font-size:13px">No journal entries yet. Journaling builds metacognitive knowledge over time. (Tanner, 2012)</div></div>
  </div>
</div>

<!-- Muddiest Point -->
<div class="view" id="view-muddiest">
  <div class="topbar"><div class="topbar-title">Muddiest Point</div><div class="topbar-sub">— Name what's still unclear (Tanner, 2012)</div></div>
  <div class="content-scroll">
    <div id="muddySetup"><div class="section-header"><div><div class="section-title">What's still muddy?</div><div class="section-sub">Naming confusion precisely is the first step to resolving it. The AI diagnoses why it's confusing and builds a clarity plan.</div></div></div>
    <div style="max-width:500px"><div class="field"><label class="field-label">Topic / subject</label><input class="input" id="muddyTopic" placeholder="Quantum entanglement"></div><div class="field"><label class="field-label">What specifically is unclear? *</label><textarea class="input textarea" id="muddyPoint" style="min-height:100px" placeholder="I understand that two particles can be entangled, but I don't understand why measuring one instantly affects the other — doesn't that violate relativity?"></textarea></div><div class="field"><label class="field-label">What have you already tried?</label><textarea class="input textarea" id="muddyTried" style="min-height:70px" placeholder="I read the Wikipedia article but it made it more confusing..."></textarea></div><button class="btn btn-self mt-8" onclick="runMuddiest()">Help me clarify this →</button></div></div>
    <div id="muddyResult" class="hidden">
      <div class="section-header"><div><div class="section-title">Clarity plan</div></div><button class="btn btn-ghost btn-sm" onclick="resetSect('muddySetup','muddyResult')">← New</button></div>
      <div class="hl hl-mode mb-16"><div class="hl-label" style="color:var(--self)">Why it's confusing</div><div id="muddyDiagnosis"></div></div>
      <div class="card mb-16"><div class="card-title mb-12">Clearest explanation</div><div id="muddyExplain" style="font-size:13.5px;line-height:1.75;color:var(--t2)"></div></div>
      <div class="card mb-16"><div class="card-title mb-12">Analogy to make it stick</div><div id="muddyAnalogy" style="font-size:13.5px;line-height:1.75;color:var(--t2)"></div></div>
      <div class="card"><div class="card-title mb-12">Questions to test your understanding</div><ul class="bl" id="muddyTests"></ul></div>
    </div>
  </div>
</div>

<!-- Goals -->
<div class="view" id="view-self-goals">
  <div class="topbar"><div class="topbar-title">My Goals</div><div class="topbar-sub">— Goal-setting improves metacognitive regulation (Schunk, 1990)</div></div>
  <div class="content-scroll"><div class="card" style="color:var(--t3);text-align:center;padding:40px">Goals created from learning sessions and plans will appear here.</div></div>
</div>

<!-- Habit Tracker -->
<div class="view" id="view-habit-tracker">
  <div class="topbar"><div class="topbar-title">Learning Habits</div><div class="topbar-sub">— Consistency compounds</div></div>
  <div class="content-scroll">
    <div class="section-header"><div><div class="section-title">Your learning streak</div><div class="section-sub">Motivation shapes metacognitive control. (Son & Metcalfe, 2000)</div></div></div>
    <div class="grid-3 mb-16"><div class="card"><div style="font-size:22px;margin-bottom:8px">🔥</div><div class="score-big" style="color:var(--self);font-size:38px">7</div><div class="score-label">Day streak</div></div><div class="card"><div style="font-size:22px;margin-bottom:8px">⏱</div><div class="score-big" style="color:var(--academic);font-size:38px">3.2h</div><div class="score-label">Avg hrs/week</div></div><div class="card"><div style="font-size:22px;margin-bottom:8px">📚</div><div class="score-big" style="color:var(--career);font-size:38px">12</div><div class="score-label">Sessions total</div></div></div>
    <div class="card"><div class="card-title mb-12">This week</div><div style="display:grid;grid-template-columns:repeat(7,1fr);gap:6px;max-width:360px">${['M','T','W','T','F','S','S'].map((d,i)=>`<div style="text-align:center"><div style="font-size:10px;color:var(--t3);margin-bottom:4px">${d}</div><div style="width:36px;height:36px;border-radius:8px;background:${i<5?'var(--self-d)':'var(--s3)'};border:1px solid ${i<5?'var(--self-b)':'var(--b1)'};display:flex;align-items:center;justify-content:center;font-size:${i<5?'16':'12'}px;color:${i<5?'var(--green)':'var(--t4)'}">${i<5?'✓':''}</div></div>`).join('')}</div></div>
  </div>
</div>
`;