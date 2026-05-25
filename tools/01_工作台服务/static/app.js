/* ═══════════════════════════════════════════════════════
   能量工作台 · 主应用 v12
   ═══════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ═══════════════════════════════════════════════════════
     DOM 引用
     ═══════════════════════════════════════════════════════ */
  const $ = (id) => document.getElementById(id);

  const DOM = {
    nl: $('nl-input'),
    prompt: $('prompt-input'),
    kb: $('kb-input'),
    presetStatus: $('preset-status'),
    presetList: $('preset-list'),
    presetHint: $('preset-hint'),
    emotionTitle: $('emotion-title'),
    pulseInfo: $('pulse-info'),
    l1Msg: $('l1-fix-msg'),
    curve: $('curve'),
    zoneRise: $('zone-rise'),
    zoneMove: $('zone-move'),
    zoneFall: $('zone-fall'),
    neonPlaceholder: $('neon-placeholder'),
    neonVideo: $('neon-video'),
    neonStatus: $('neon-status'),
    btnRenderNeon: $('btn-render-neon'),
    pipeTabs: $('pipe-tabs'),
    pipeJson: $('pipe-json'),
    pipeSource: $('pipe-source'),
    pipeFull: $('pipe-full'),
    btnSaveCtx: $('btn-save-ctx'),
    btnSavePacket: $('btn-save-packet'),
    btnCopy: $('btn-copy'),
    btnNeutral: $('btn-neutral'),
    personSelect: $('persona-select'),
    personSliders: $('persona-sliders'),
    assetTree: $('asset-tree'),
    dogNl: $('dog-nl-input'),
    dogBtn: $('btn-dog-test'),
    dogStatus: $('dog-test-status'),
    // 客户资产库
    customerSelect: $('customer-select'),
    projectSelect: $('project-select'),
    btnCustomerNew: $('btn-customer-new'),
    btnProjectNew: $('btn-project-new'),
    btnCustomerSaveCtx: $('btn-customer-save-ctx'),
    btnCustomerSaveAdj: $('btn-customer-save-adj'),
    customerProjectBlock: $('customer-project-block'),
    customerActions: $('customer-actions'),
    customerStatus: $('customer-status'),
  };

  /* ═══════════════════════════════════════════════════════
     状态
     ═══════════════════════════════════════════════════════ */
  const STATE = {
    schema: 'slider-packet-v1',
    zones: {},
    presetGroups: [],
    presets: {},
    shapeOpts: [],
    macroIds: [],
    holdIds: [],
    validShapes: [],
    pipeTabs: [],
    neutral: { macro: { push: 50, power: 50, speed: 50, steady: 50, grip: 50, outro: 50 }, hold_seg: { shape: 'flat', pulse_rate: 0, pulse_depth: 0, swell: 0 } },
    macro: {},
    holdSeg: {},
    activePreset: '',
    pipelineData: null,
    activePipeTab: '1_slider_packet',
    loadToken: 0,
    loading: false,
    currentSpecies: 'human',
    personaMatrix: null,
    selectedPersonaId: '',
    // 客户资产库状态
    customers: [],
    projects: [],
    activeCustomerId: '',
    activeProjectId: '',
    currentPacket: null,
  };

  // 初始化宏和保持段
  STATE.macro = { ...STATE.neutral.macro };
  STATE.holdSeg = { ...STATE.neutral.hold_seg };

  /* ═══════════════════════════════════════════════════════
     工具函数
     ═══════════════════════════════════════════════════════ */
  const clamp = (v) => Math.max(0, Math.min(100, Math.round(Number(v))));

  function notify(msg, type) {
    const el = document.createElement('div');
    el.className = 'notification ' + (type || 'info');
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => { el.remove(); }, 3000);
  }

  /* ═══════════════════════════════════════════════════════
     物种数据
     ═══════════════════════════════════════════════════════ */
  const SPECIES = {
    human: { label: '人类', icon: '🙂', channelCount: 12, presets: null, hint: '选情绪 = 自动填充滑杆 · 再微调 = 自定义' },
    cat: {
      label: '猫', icon: '🐱', channelCount: 13,
      presets: {
        cat_alarm_stare: { note: '警觉·盯 · 竖耳缩瞳' },
        cat_hunt_fixate: { note: '狩猎·锁定 · 伏低' },
        cat_startle_fluff: { note: '惊吓·炸毛 · 飞机耳' },
        cat_curious_tilt: { note: '好奇·歪头 · 一耳前一耳后' },
        cat_cuddle_squint: { note: '撒娇·眯眼 · 慢眨眼' },
        cat_content_bliss: { note: '满足·飘然 · 眯眼成线' },
        cat_annoyed_swish: { note: '不耐烦 · 耳朵背过去' },
        cat_scared_flatten: { note: '恐惧·贴地 · 全飞机耳' },
        cat_sad_whimper: { note: '委屈·呜咽 · 眼湿润' },
        cat_angry_hiss: { note: '愤怒·哈气 · 瞳孔缩线' },
        cat_sleepy_droop: { note: '困倦·迷离 · 眼皮下垂' },
        cat_play_pounce: { note: '玩耍·扑击 · 瞳孔放大' },
      },
      groups: [
        { label: '警觉 · 攻击', keys: ['cat_alarm_stare', 'cat_hunt_fixate', 'cat_angry_hiss'] },
        { label: '恐惧 · 退缩', keys: ['cat_startle_fluff', 'cat_scared_flatten', 'cat_sad_whimper'] },
        { label: '亲昵 · 放松', keys: ['cat_cuddle_squint', 'cat_content_bliss', 'cat_sleepy_droop'] },
        { label: '好奇 · 玩耍', keys: ['cat_curious_tilt', 'cat_play_pounce', 'cat_annoyed_swish'] },
      ],
      hint: '🐱 猫情绪预设 · 参数待填充',
    },
    dog: {
      label: '狗', icon: '🐶', channelCount: 13,
      presets: {
        dog_alert_bark: { note: '警觉·吠 · 竖耳' },
        dog_happy_wag: { note: '开心·摇尾 · 放松眼' },
        dog_sad_puppy: { note: '委屈·幼犬眼 · 挑眉上翻' },
        dog_scared_tuck: { note: '恐惧·夹尾 · 耳后贴' },
        dog_angry_growl: { note: '愤怒·低吼 · 竖耳前倾' },
        dog_curious_cock: { note: '好奇·歪头 · 单耳竖' },
        dog_submissive_look: { note: '服从·回避 · 眼神避开' },
        dog_play_bow: { note: '邀玩·趴 · 瞳孔放大' },
        dog_guilty_side: { note: '心虚·偷瞄 · 耳耷拉' },
        dog_content_sigh: { note: '满足·叹气 · 半闭眼' },
      },
      groups: [
        { label: '警觉 · 攻击', keys: ['dog_alert_bark', 'dog_angry_growl', 'dog_scared_tuck'] },
        { label: '亲昵 · 放松', keys: ['dog_happy_wag', 'dog_content_sigh', 'dog_sad_puppy'] },
        { label: '好奇 · 玩耍', keys: ['dog_curious_cock', 'dog_play_bow', 'dog_guilty_side'] },
        { label: '服从 · 回避', keys: ['dog_submissive_look'] },
      ],
      hint: '🐶 狗情绪预设 · 参数待填充',
    },
  };

  /* ═══════════════════════════════════════════════════════
     第1节 · 控制面加载
     ═══════════════════════════════════════════════════════ */
  function applyControlSurface(data) {
    STATE.schema = data.schema || STATE.schema;
    STATE.zones = data.zones || {};
    STATE.presetGroups = data.preset_groups || [];
    STATE.presets = data.presets || {};
    STATE.shapeOpts = data.shape_opts || [];
    STATE.macroIds = data.macro_ids || [];
    STATE.holdIds = data.hold_ids || [];
    STATE.validShapes = data.valid_shapes || [];
    STATE.neutral = data.neutral || STATE.neutral;
    STATE.pipeTabs = data.pipe_tabs || [];
  }

  async function loadControlSurface() {
    if (location.protocol === 'file:') {
      DOM.presetStatus.className = 'preset-status err';
      DOM.presetStatus.textContent = '⚠ 请通过 HTTP 访问';
      return false;
    }
    try {
      const r = await fetch('/control_surface.json', { cache: 'no-store' });
      if (!r.ok) throw new Error(r.statusText);
      const data = await r.json();
      applyControlSurface(data);
      DOM.presetStatus.className = 'preset-status ok';
      DOM.presetStatus.textContent = '✅ v' + data.version + ' 就绪 · ' + Object.keys(STATE.presets).length + ' 种情绪';
      return true;
    } catch (e) {
      DOM.presetStatus.className = 'preset-status err';
      DOM.presetStatus.textContent = '⚠ 控制面加载失败';
      return false;
    }
  }

  /* ═══════════════════════════════════════════════════════
     第2节 · 预设按钮 & 物种切换
     ═══════════════════════════════════════════════════════ */
  function buildPresets() {
    DOM.presetList.innerHTML = '';
    const species = SPECIES[STATE.currentSpecies];
    const groups = STATE.currentSpecies === 'human' ? STATE.presetGroups : species.groups;
    const presets = STATE.currentSpecies === 'human' ? STATE.presets : species.presets;

    groups.forEach((g) => {
      const hd = document.createElement('div');
      hd.className = 'preset-group';
      hd.textContent = g.label;
      DOM.presetList.appendChild(hd);

      g.keys.forEach((key) => {
        const data = presets[key];
        if (!data) return;
        const btn = document.createElement('button');
        btn.className = 'preset-btn';
        btn.dataset.preset = key;
        btn.innerHTML = key + '<small>' + (data.note || '') + '</small>';
        btn.onclick = () => selectEmotion(key);
        DOM.presetList.appendChild(btn);
      });
    });
  }

  function switchSpecies(species) {
    STATE.currentSpecies = species;

    // 更新按钮高亮
    document.querySelectorAll('.species-btn').forEach((b) => {
      b.classList.toggle('active', b.dataset.species === species);
    });

    // 更新提示
    DOM.presetHint.textContent = SPECIES[species].hint;

    // 更新标题
    const count = species === 'human'
      ? Object.keys(STATE.presets).length
      : Object.keys(SPECIES[species].presets).length;
    DOM.emotionTitle.textContent = count + ' 种情绪预设';

    buildPresets();
    highlightPreset('');
    resetToNeutral();
  }

  function highlightPreset(name) {
    document.querySelectorAll('.preset-btn').forEach((b) => {
      b.classList.toggle('active', b.dataset.preset === name);
    });
  }

  async function selectEmotion(name) {
    const data = STATE.currentSpecies === 'human'
      ? STATE.presets[name]
      : SPECIES[STATE.currentSpecies].presets[name];
    if (!data || (!STATE.loading && STATE.activePreset === name)) {
      highlightPreset(name);
      return;
    }

    const token = ++STATE.loadToken;
    STATE.loading = true;
    STATE.activePreset = name;
    STATE.macro = { ...data.macro };
    STATE.holdSeg = { ...data.hold_seg };
    STATE.pipelineData = null;
    highlightPreset(name);

    try {
      if (token === STATE.loadToken) paint();
    } finally {
      if (token === STATE.loadToken) STATE.loading = false;
    }
  }

  function resetToNeutral() {
    STATE.loadToken++;
    STATE.activePreset = '';
    STATE.macro = { ...STATE.neutral.macro };
    STATE.holdSeg = { ...STATE.neutral.hold_seg };
    STATE.pipelineData = null;
    highlightPreset('');
    paint();
  }

  /* ═══════════════════════════════════════════════════════
     第3节 · 滑杆构建
     ═══════════════════════════════════════════════════════ */
  function buildKnob(k, spec) {
    const div = document.createElement('div');
    div.className = 'knob';

    const label = document.createElement('label');
    label.textContent = spec.label;

    const input = document.createElement('input');
    input.type = 'range';
    input.min = 0;
    input.max = 100;
    input.dataset.key = k;
    input.dataset.spec = spec.id;
    input.value = (k === 'macro' ? STATE.macro[spec.id] : STATE.holdSeg[spec.id]) || 0;

    const valSpan = document.createElement('span');
    valSpan.className = 'val';
    valSpan.textContent = input.value;

    const update = () => {
      const v = Number(input.value);
      if (k === 'macro') STATE.macro[spec.id] = v;
      else STATE.holdSeg[spec.id] = v;
      valSpan.textContent = v;
      STATE.activePreset = '';
      highlightPreset('');
      paint();
    };

    input.oninput = update;
    div.appendChild(label);
    div.appendChild(input);
    div.appendChild(valSpan);
    return div;
  }

  function buildZones() {
    ['rise', 'move', 'fall'].forEach((zid) => {
      const z = STATE.zones[zid];
      const root = document.getElementById('zone-' + zid);
      if (!z) { root.innerHTML = ''; return; }

      let html = '<div class="zone-header">' + z.title + '<span>' + (z.sub || '') + '</span></div>';

      if (z.shapes) {
        html += '<div class="shape-row" id="shape-row-' + zid + '">';
        STATE.shapeOpts.forEach((s) => {
          html += '<button class="shape-btn" data-shape="' + s.id + '" data-zone="' + zid + '">' + s.label + '</button>';
        });
        html += '</div>';
      }

      root.innerHTML = html;

      if (z.shapes) {
        root.querySelectorAll('.shape-btn').forEach((btn) => {
          btn.onclick = () => {
            STATE.holdSeg.shape = btn.dataset.shape;
            paint();
          };
        });
      }

      (z.knobs || []).forEach((spec) => {
        if (spec.type === 'shape') return;
        root.appendChild(buildKnob(spec.k, spec));
      });
    });
  }

  /* ═══════════════════════════════════════════════════════
     第4节 · SVG 脉冲曲线
     ═══════════════════════════════════════════════════════ */
  function paint() {
    // 更新滑杆值
    document.querySelectorAll('.knob input').forEach((inp) => {
      const k = inp.dataset.key;
      const id = inp.dataset.spec;
      if (!k || !id) return;
      const src = k === 'macro' ? STATE.macro : STATE.holdSeg;
      if (src[id] !== undefined) inp.value = src[id];
      const valSpan = inp.nextElementSibling;
      if (valSpan && valSpan.className === 'val') valSpan.textContent = inp.value;
    });

    // 更新形状按钮
    document.querySelectorAll('.shape-btn').forEach((b) => {
      b.classList.toggle('active', b.dataset.shape === STATE.holdSeg.shape);
    });

    // 绘制 SVG 曲线
    const W = 300, H = 100;
    const m = STATE.macro;
    const h = STATE.holdSeg;

    let html = '<rect width="300" height="100" fill="#fafbfd"/>'
      + '<rect x="0" y="0" width="60" height="100" fill="#dbeafe" opacity="0.4"/>'
      + '<rect x="60" y="0" width="180" height="100" fill="#fef3c7" opacity="0.4"/>'
      + '<rect x="240" y="0" width="60" height="100" fill="#e0e7ff" opacity="0.4"/>';

    const push = m.push / 100;
    const power = m.power / 100;
    const speed = m.speed / 100;
    const steady = m.steady / 100;
    const grip = m.grip / 100;
    const outro = m.outro / 100;

    const tPeak = 14 + (1 - speed) * 10;
    const peakY = H - (15 + power * 65);
    const tHold = 30 + steady * 60;
    const tOutro = tHold + (1 - outro) * 40;
    const holdY = peakY + (1 - grip) * 10;

    let d = 'M0,' + H;
    for (let t = 0; t <= tPeak; t++) {
      const u = t / tPeak;
      const y = H - u * (H - peakY) * (push > 0.5 ? 1 + (push - 0.5) * 0.4 : 1);
      d += ' L' + (t / 150 * W) + ',' + Math.round(y);
    }
    for (let t = tPeak + 1; t <= tHold; t++) {
      const u = (t - tPeak) / (tHold - tPeak);
      let y = peakY + (holdY - peakY) * u;
      if (h.shape === 'tremble') y += Math.sin(u * 20) * 4;
      if (h.shape === 'pulse') y += Math.sin(u * h.pulse_rate * 0.3) * h.pulse_depth * 0.3;
      if (h.shape === 'decay') y += u * 20;
      if (h.shape === 'swell') y -= Math.sin(Math.PI * u) * h.swell * 0.3;
      d += ' L' + (t / 150 * W) + ',' + Math.round(Math.max(peakY - 10, Math.min(H, y)));
    }
    for (let t = tHold + 1; t <= 150; t++) {
      const u = (t - tHold) / (150 - tHold);
      const ease = u < 0.5 ? 2 * u * u : -1 + (4 - 2 * u) * u;
      const y = holdY + (H - holdY) * ease;
      d += ' L' + (t / 150 * W) + ',' + Math.round(y);
    }

    html += '<path d="' + d + '" fill="none" stroke="' + (m.push > 50 ? '#3b82f6' : '#d97706') + '" stroke-width="2.5" stroke-linejoin="round"/>';
    html += '<line x1="' + (tPeak / 150 * W) + '" y1="0" x2="' + (tPeak / 150 * W) + '" y2="100" stroke="#3b82f6" stroke-width="0.5" stroke-dasharray="3,4" opacity="0.5"/>';
    html += '<line x1="' + (tHold / 150 * W) + '" y1="0" x2="' + (tHold / 150 * W) + '" y2="100" stroke="#d97706" stroke-width="0.5" stroke-dasharray="3,4" opacity="0.5"/>';
    DOM.curve.innerHTML = html;

    DOM.pulseInfo.textContent = '起峰:' + Math.round(tPeak) + 'f · 盯住:' + Math.round(tPeak) + '→' + Math.round(tHold) + 'f · 收场:' + Math.round(tHold) + '→150f · 力度:' + m.power;
  }

  /* ═══════════════════════════════════════════════════════
     第5节 · 数据包构建
     ═══════════════════════════════════════════════════════ */
  function buildPacket() {
    return {
      schema: STATE.schema,
      emotion: STATE.activePreset || '',
      macro: { ...STATE.macro },
      hold_seg: { ...STATE.holdSeg },
    };
  }

  /* ═══════════════════════════════════════════════════════
     第6节 · 交付链面板
     ═══════════════════════════════════════════════════════ */
  function buildPipeTabs() {
    DOM.pipeTabs.innerHTML = '';
    STATE.pipeTabs.forEach((tab) => {
      const btn = document.createElement('button');
      btn.className = 'pipe-tab';
      btn.innerHTML = tab.title + (tab.sub ? '<small>' + tab.sub + '</small>' : '');
      btn.dataset.tab = tab.id;
      btn.onclick = () => { STATE.activePipeTab = tab.id; renderPipeJson(); };
      DOM.pipeTabs.appendChild(btn);
    });
  }

  function renderPipeJson() {
    DOM.pipeTabs.querySelectorAll('.pipe-tab').forEach((b) => {
      b.classList.toggle('active', b.dataset.tab === STATE.activePipeTab);
    });

    if (!STATE.pipelineData) {
      DOM.pipeJson.textContent = JSON.stringify(buildPacket(), null, 2);
      DOM.pipeSource.textContent = '⚠ 前端草稿（非出厂定稿）· 选情绪或点编译';
      DOM.pipeSource.className = 'pipe-source warn';
      return;
    }

    const tab = STATE.activePipeTab;
    let obj;
    if (tab === '1_slider_packet') {
      obj = STATE.pipelineData.slider_packet || buildPacket();
    } else if (tab === '2_envelope') {
      obj = STATE.pipelineData.energy_envelope || STATE.pipelineData.envelope || {};
    } else if (tab === '3_dense_env' || tab === '4_dense_prior' || tab === '4b_pulse_quality_report') {
      obj = STATE.pipelineData.channel_tracks || STATE.pipelineData.channels || {};
      if (!DOM.pipeFull.checked) {
        const summary = {};
        Object.keys(obj).forEach((k) => {
          if (Array.isArray(obj[k]) && obj[k].length > 10) {
            summary[k] = '[150 frames, first 5]: ' + JSON.stringify(obj[k].slice(0, 5));
          } else {
            summary[k] = obj[k];
          }
        });
        obj = summary;
      }
    } else {
      obj = STATE.pipelineData;
    }
    DOM.pipeJson.textContent = JSON.stringify(obj, null, 2);
    DOM.pipeSource.textContent = '✓ 出厂定稿 · ' + (STATE.pipelineData.emotion || STATE.pipelineData.mood || '');
    DOM.pipeSource.className = 'pipe-source ok';
  }

  /* ═══════════════════════════════════════════════════════
     第7节 · API 通信
     ═══════════════════════════════════════════════════════ */
  async function fetchJSON(url, opts) {
    const r = await fetch(url, opts);
    const text = await r.text();
    if (!r.ok) throw new Error(text.slice(0, 200));
    try { return JSON.parse(text); } catch (e) {
      throw new Error('非 JSON 响应 — 请重启工作台');
    }
  }

  async function loadContext() {
    try {
      const r = await fetch('/workbench_context.json', { cache: 'no-cache' });
      if (!r.ok) return;
      const c = await r.json();
      if (c.natural_language) DOM.nl.value = c.natural_language;
      if (c.energy_map_note || c.prompt) DOM.prompt.value = c.energy_map_note || c.prompt;
      if (c.knowledge_base) DOM.kb.value = c.knowledge_base;
    } catch (e) { /* ignore */ }
  }

  async function loadSliderPacket() {
    try {
      const r = await fetch('/slider_packet.json', { cache: 'no-cache' });
      if (r.ok) {
        const pkt = await r.json();
        if (pkt && pkt.macro) {
          STATE.macro = { ...pkt.macro };
          STATE.holdSeg = { ...pkt.hold_seg };
          if (pkt.emotion && STATE.presets[pkt.emotion]) STATE.activePreset = pkt.emotion;
          STATE.pipelineData = null;
          paint();
        }
      }
    } catch (e) { /* no saved packet yet */ }
  }

  async function saveContext() {
    const body = {
      natural_language: DOM.nl.value.trim(),
      energy_map_note: DOM.prompt.value.trim(),
      knowledge_base: DOM.kb.value.trim(),
    };
    try {
      const j = await fetchJSON('/save_context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      notify(j.ok ? '✅ 上下文已保存' : '保存失败', j.ok ? 'success' : 'error');
    } catch (e) {
      notify('请先运行启动脚本', 'error');
    }
  }

  async function savePacket() {
    try {
      const j = await fetchJSON('/save_packet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPacket()),
      });
      notify(j.ok ? '✅ 已保存到资产库' : '保存失败', j.ok ? 'success' : 'error');
    } catch (e) {
      notify('保存失败: ' + e.message, 'error');
    }
  }

  /* ═══════════════════════════════════════════════════════
     第8节 · 2D 霓虹控制视频
     ═══════════════════════════════════════════════════════ */
  async function renderNeonControlVideo() {
    if (location.protocol === 'file:') {
      DOM.neonStatus.textContent = '⚠ 请通过 http://127.0.0.1:8765 访问';
      return;
    }

    DOM.btnRenderNeon.disabled = true;
    DOM.btnRenderNeon.textContent = '⏳ 渲染中…';
    DOM.neonStatus.textContent = '⏳ 编译管线: 滑杆→12×150→人律→平庸→视频…';
    DOM.neonPlaceholder.style.display = 'none';
    DOM.neonVideo.style.display = 'none';

    try {
      const pkt = buildPacket();
      const j = await fetchJSON('/render_control_video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pkt),
      });

      if (!j.ok) {
        DOM.neonStatus.textContent = '渲染失败: ' + (j.error || j.message || JSON.stringify(j));
        return;
      }

      const url = (j.path || '/control_video.mp4') + '?t=' + Date.now();
      DOM.neonVideo.src = url;
      DOM.neonVideo.style.display = 'block';
      DOM.neonVideo.load();
      DOM.neonVideo.onloadeddata = () => {
        DOM.neonStatus.textContent = '✓ 2D 霓虹控制流就绪 · 播放中';
        DOM.neonVideo.play().catch(() => {
          DOM.neonStatus.textContent += ' (点击播放)';
        });
      };
      DOM.neonVideo.onerror = () => {
        DOM.neonStatus.textContent = '视频加载失败，请检查浏览器控制台';
        DOM.neonVideo.style.display = 'none';
        DOM.neonPlaceholder.style.display = 'flex';
      };
    } catch (e) {
      DOM.neonStatus.textContent = '网络错误: ' + (e.message || e);
    } finally {
      DOM.btnRenderNeon.disabled = false;
      DOM.btnRenderNeon.textContent = '🎞 渲染 2D 控制流';
    }
  }

  /* ═══════════════════════════════════════════════════════
     第9节 · 人格矩阵
     ═══════════════════════════════════════════════════════ */
  const CANONICAL_KEYS = [
    "pupil_x", "pupil_y", "blink", "eyebrow", "pupil_scale", "iris_scale",
    "cornea_bulge", "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
  ];
  const CHANNEL_LABELS = {
    pupil_x: "视线左右", pupil_y: "视线上下", blink: "眼睑开合", eyebrow: "眉压",
    pupil_scale: "瞳孔缩放", iris_scale: "虹膜圈", cornea_bulge: "角膜鼓起",
    squint: "眯眼眶压", brow_raise: "挑眉", lid_upper: "上眼睑", lid_lower: "下眼睑",
    eye_gloss: "眼湿润高光",
  };

  async function loadPersonaMatrix() {
    if (location.protocol === 'file:') return;
    try {
      const r = await fetch('/persona_matrix.json', { cache: 'no-store' });
      if (!r.ok) return;
      STATE.personaMatrix = await r.json();

      DOM.personSelect.innerHTML = '';
      const ids = Object.keys(STATE.personaMatrix.personas || {});
      ids.forEach((pid) => {
        const opt = document.createElement('option');
        opt.value = pid;
        opt.textContent = STATE.personaMatrix.personas[pid].label + ' (' + pid + ')';
        DOM.personSelect.appendChild(opt);
      });

      if (ids.length > 0) {
        DOM.personSelect.value = ids[0];
        STATE.selectedPersonaId = ids[0];
        renderPersonaSliders(ids[0]);
      }

      DOM.personSelect.onchange = () => {
        STATE.selectedPersonaId = DOM.personSelect.value;
        renderPersonaSliders(DOM.personSelect.value);
      };
    } catch (e) {
      console.warn('人格矩阵加载失败', e);
    }
  }

  function renderPersonaSliders(pid) {
    const p = STATE.personaMatrix && STATE.personaMatrix.personas && STATE.personaMatrix.personas[pid];
    if (!p) {
      DOM.personSliders.innerHTML = '<p class="text-muted text-sm" style="padding:8px;text-align:center">无此人格数据</p>';
      return;
    }

    let html = '';
    CANONICAL_KEYS.forEach((key) => {
      const label = CHANNEL_LABELS[key] || key;
      const base = (p.base_offset && p.base_offset[key] !== undefined) ? p.base_offset[key] : 0.5;
      const scale = (p.scale_factor && p.scale_factor[key] !== undefined) ? p.scale_factor[key] : 0.3;

      html += '<div class="persona-item">';
      html += '<div class="label">' + label + ' <span>(' + key + ')</span></div>';

      html += '<div class="knob" style="margin-bottom:1px;gap:4px">';
      html += '<label style="width:auto;font-size:0.6rem">偏置</label>';
      html += '<input type="range" min="0" max="1" step="0.01" value="' + base + '" data-pid="' + pid + '" data-key="' + key + '" data-field="base_offset" style="flex:1;height:4px">';
      html += '<span class="val" style="width:28px;font-size:0.6rem">' + base.toFixed(2) + '</span>';
      html += '</div>';

      html += '<div class="knob" style="margin-bottom:1px;gap:4px">';
      html += '<label style="width:auto;font-size:0.6rem">系数</label>';
      html += '<input type="range" min="0" max="1" step="0.01" value="' + scale + '" data-pid="' + pid + '" data-key="' + key + '" data-field="scale_factor" style="flex:1;height:4px">';
      html += '<span class="val" style="width:28px;font-size:0.6rem">' + scale.toFixed(2) + '</span>';
      html += '</div>';

      html += '</div>';
    });

    html += '<div class="flex gap-2" style="padding:6px 2px 0">';
    html += '<button class="btn sm" id="btn-persona-reset" style="flex:1">↺ 重置</button>';
    html += '<button class="btn sm primary" id="btn-persona-save" style="flex:1">💾 保存</button>';
    html += '</div>';

    DOM.personSliders.innerHTML = html;

    DOM.personSliders.querySelectorAll('.knob input[type=range]').forEach((inp) => {
      inp.oninput = function () {
        const valSpan = this.nextElementSibling;
        if (valSpan) valSpan.textContent = parseFloat(this.value).toFixed(2);
      };
    });

    document.getElementById('btn-persona-reset').addEventListener('click', () => {
      renderPersonaSliders(pid);
    });

    document.getElementById('btn-persona-save').addEventListener('click', async () => {
      if (!STATE.personaMatrix || !STATE.personaMatrix.personas[pid]) return;
      const pData = STATE.personaMatrix.personas[pid];
      DOM.personSliders.querySelectorAll('.knob input[type=range]').forEach((inp) => {
        const dataKey = inp.dataset.key;
        const field = inp.dataset.field;
        if (dataKey && field && pData[field]) {
          pData[field][dataKey] = parseFloat(inp.value);
        }
      });

      try {
        const res = await fetchJSON('/persona_matrix.json', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'save', persona_id: pid, data: pData }),
        });
        notify(res.ok ? '✅ 已保存到 persona_matrix.json' : '❌ 保存失败: ' + (res.error || ''), res.ok ? 'success' : 'error');
      } catch (err) {
        notify('❌ 网络错误: ' + err.message, 'error');
      }
    });
  }

  /* ═══════════════════════════════════════════════════════
     第10节 · 资产库浏览器
     ═══════════════════════════════════════════════════════ */
  async function loadAssetBrowser() {
    if (location.protocol === 'file:') {
      DOM.assetTree.innerHTML = '<p class="text-muted text-sm" style="padding:8px;text-align:center">⚠ 请通过 HTTP 访问</p>';
      return;
    }
    try {
      const r = await fetch('/api/asset-browser', { cache: 'no-cache' });
      if (!r.ok) throw new Error(r.statusText);
      const data = await r.json();
      if (!data.ok || !data.root) throw new Error('无效响应');
      renderAssetTree(data.root);
    } catch (e) {
      DOM.assetTree.innerHTML = '<p class="text-muted text-sm" style="padding:8px;text-align:center">⚠ ' + e.message + '</p>';
    }
  }

  function renderAssetTree(items, depth) {
    if (depth === undefined) depth = 0;
    if (!items || items.length === 0) {
      DOM.assetTree.innerHTML = '<p class="text-muted text-sm" style="padding:8px;text-align:center">（空）</p>';
      return;
    }

    let html = '';
    items.forEach((item) => {
      const pad = depth * 14;
      if (item.type === 'dir') {
        html += '<div style="padding:1px 0"><span style="display:inline-block;width:' + pad + 'px"></span>📁 <strong>' + item.name + '</strong></div>';
        if (item.children) {
          item.children.forEach((child) => {
            const cpad = (depth + 1) * 14;
            if (child.type === 'dir') {
              html += '<div style="padding:1px 0"><span style="display:inline-block;width:' + cpad + 'px"></span>📁 ' + child.name + '</div>';
              if (child.children) {
                child.children.forEach((grand) => {
                  html += renderFileItem(grand, (depth + 2) * 14);
                });
              }
            } else {
              html += renderFileItem(child, cpad);
            }
          });
        }
      }
    });
    DOM.assetTree.innerHTML = html;
  }

  function renderFileItem(item, pad) {
    let icon = '📄';
    if (item.tag === '烘焙') icon = '🎯';
    else if (item.tag === '节拍表') icon = '📋';
    else if (item.tag === '人格') icon = '🧬';
    else if (item.tag === '情绪') icon = '🎭';

    let tagHtml = '';
    if (item.tag) {
      tagHtml = ' <span class="asset-tag">' + item.tag + '</span>';
    }
    let sizeHtml = '';
    if (item.size) {
      sizeHtml = ' <span class="asset-size">' + (item.size > 1024 ? (item.size / 1024).toFixed(1) + 'KB' : item.size + 'B') + '</span>';
    }

    const clickable = item.tag === '烘焙' && item.ext === '.json';
    const escapedName = item.name.replace(/'/g, "\\'");
    const onclick = clickable ? ' onclick="window.app.loadBakedAsset(\'' + escapedName + '\')"' : '';

    return '<div class="file-item' + (clickable ? ' clickable' : '') + '"' + onclick + '>'
      + '<span style="display:inline-block;width:' + pad + 'px"></span>'
      + '<span>' + icon + '</span> '
      + item.name + tagHtml + sizeHtml
      + '</div>';
  }

  async function loadBakedAsset(filename) {
    try {
      const r = await fetch('/api/asset-browser', { cache: 'no-cache' });
      const data = await r.json();
      let foundPath = '';

      function search(items, prefix) {
        for (let i = 0; i < items.length; i++) {
          const item = items[i];
          if (item.type === 'dir' && item.children) {
            search(item.children, prefix + item.name + '/');
          } else if (item.name === filename) {
            foundPath = prefix + item.name;
          }
        }
      }
      search(data.root, '预设资产/');
      if (!foundPath) { notify('未找到文件路径', 'error'); return; }

      const pkt = buildPacket();
      const result = await fetchJSON('/api/asset-load-baked', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: foundPath, packet: pkt }),
      });

      if (!result.ok) { notify('加载失败: ' + (result.error || ''), 'error'); return; }

      if (result.baked) {
        STATE.pipelineData = result.baked;
        STATE.activePipeTab = '5_baked_02_delivery';
        renderPipeJson();

        if (result.packet && result.packet.macro) {
          STATE.macro = { ...result.packet.macro };
          if (result.packet.hold_seg) STATE.holdSeg = { ...result.packet.hold_seg };
          if (result.packet.emotion) STATE.activePreset = result.packet.emotion;
          highlightPreset(STATE.activePreset);
          paint();
        }

        DOM.pipeSource.textContent = '✓ 已加载: ' + foundPath;
        DOM.pipeSource.className = 'pipe-source ok';
        notify('✅ 已加载烘焙资产', 'success');
      }
    } catch (e) {
      notify('加载失败: ' + e.message, 'error');
    }
  }

  /* ═══════════════════════════════════════════════════════
     第11节 · 狗全身体验测试
     ═══════════════════════════════════════════════════════ */
  async function runDogTest() {
    const nl = DOM.dogNl.value.trim() || '狗子被关进笼子里面的委屈样子';

    DOM.dogBtn.disabled = true;
    DOM.dogBtn.textContent = '⏳ 生成中…';
    DOM.dogStatus.innerHTML = '⏳ 编译12通道→生成工程底膜→节奏说明书…<br>';

    try {
      const j = await fetchJSON('/api/dog-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preset: 'dog_sad_puppy',
          nl: nl,
          out_dir: '/tmp/dog_test_ui',
          skip_body: true,
          skip_mesh: false,
        }),
      });

      if (!j.ok) {
        DOM.dogStatus.innerHTML = '❌ 失败: ' + (j.error || JSON.stringify(j));
        return;
      }

      const a = j.assets;
      DOM.dogStatus.innerHTML = ''
        + '✅ 狗测试资产生成完毕！<br>'
        + '📄 <a href="/api/asset-load-baked" onclick="event.preventDefault();alert(\'File: ' + a.baked_json + '\')" style="color:#6cf">02_烘焙_真人律.json</a><br>'
        + '📝 <a href="#" onclick="event.preventDefault();fetch(\'/api/export-metronome\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({baked_path:\'' + a.baked_json + '\'})}).then(r=>r.json()).then(j=>{var w=window.open();w.document.write(\'<pre>\'+j.metronome+\'</pre>\')})" style="color:#6cf">05_扩散节拍表.txt</a><br>'
        + '🎬 工程底膜: ' + (a.eye_mesh_video || '⏭ 跳过') + '<br>'
        + '📜 Wan Prompt: ' + a.wan_prompt + '<br>'
        + '🐶 情绪: ' + a.preset + '<br>'
        + '⏱ 帧数: ' + a.frame_count + ' @ ' + a.fps + 'fps';

    } catch (e) {
      DOM.dogStatus.innerHTML = '❌ 网络错误: ' + (e.message || e) + ' · 确认服务已启动';
    } finally {
      DOM.dogBtn.disabled = false;
      DOM.dogBtn.textContent = '🎞 生成狗测试资产';
    }
  }

  /* ═══════════════════════════════════════════════════════
  /* ═══════════════════════════════════════════════════════
     第12节 · 健康检查
     ═══════════════════════════════════════════════════════ */
  async function healthCheck() {
    if (location.protocol === 'file:') {
      DOM.pipeSource.textContent = '⚠ 请启动工作台';
      DOM.pipeSource.className = 'pipe-source warn';
      return false;
    }
    try {
      const h = await fetchJSON('/health', { cache: 'no-store' });
      if (h.ok) {
        DOM.pipeSource.textContent = '✓ 服务 v' + h.version;
        DOM.pipeSource.className = 'pipe-source ok';
        return true;
      }
    } catch (e) { /* ignore */ }
    DOM.pipeSource.textContent = '⚠ 服务异常';
    DOM.pipeSource.className = 'pipe-source warn';
    return false;
  }

  // ═══════════════════════════════════════════════════════
  // 客户资产库 API 调用
  // ═══════════════════════════════════════════════════════

  async function _apiPost(path, body) {
    try {
      const r = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      return await r.json();
    } catch (e) {
      console.error('[customer] POST', path, e);
      return { ok: false, error: String(e) };
    }
  }

  async function _apiGet(path) {
    try {
      const r = await fetch(path);
      return await r.json();
    } catch (e) {
      console.error('[customer] GET', path, e);
      return { ok: false, error: String(e) };
    }
  }

  async function loadCustomerList() {
    const data = await _apiGet('/api/customer-list');
    if (!data.ok) return;
    STATE.customers = data.customers || [];
    const sel = DOM.customerSelect;
    sel.innerHTML = '<option value="">— 不选择 —</option>';
    STATE.customers.forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c.customer_id;
      opt.textContent = c.display_name || c.customer_id;
      sel.appendChild(opt);
    });
    // 恢复之前选择的客户
    if (STATE.activeCustomerId) {
      sel.value = STATE.activeCustomerId;
    }
  }

  async function loadProjectList(customerId) {
    if (!customerId) {
      DOM.projectSelect.innerHTML = '<option value="">— 先选客户 —</option>';
      DOM.customerProjectBlock.style.display = 'none';
      DOM.customerActions.style.display = 'none';
      return;
    }
    // 当前没有直接列出项目的 API，用客户信息推断
    // 实际可通过 GET /api/customer/{cid}/project 扩展
    // 这里简化：仅通过客户上下文恢复
    DOM.customerProjectBlock.style.display = 'block';
    const sel = DOM.projectSelect;
    sel.innerHTML = '<option value="">— 不选择 —</option>';
    if (STATE.activeProjectId) {
      sel.value = STATE.activeProjectId;
    }
    DOM.customerActions.style.display = 'block';
  }

  async function saveCustomerContext() {
    const cid = DOM.customerSelect.value;
    const pid = DOM.projectSelect.value || '';
    STATE.activeCustomerId = cid;
    STATE.activeProjectId = pid;
    const data = await _apiPost('/api/customer-context/save', {
      customer_id: cid,
      project_id: pid,
    });
    if (data.ok) {
      DOM.customerStatus.textContent = cid
        ? `✅ 当前: ${cid}${pid ? ' / ' + pid : ''}`
        : '已清除';
    }
    loadProjectList(cid);
  }

  async function createCustomer() {
    const name = prompt('输入客户名称：');
    if (!name || !name.trim()) return;
    const data = await _apiPost('/api/customer/create', { display_name: name.trim() });
    if (data.ok) {
      await loadCustomerList();
      DOM.customerSelect.value = data.customer_id;
      STATE.activeCustomerId = data.customer_id;
      await saveCustomerContext();
      DOM.customerStatus.textContent = `✅ 已创建客户 ${data.customer_id}: ${name.trim()}`;
    } else {
      alert('创建失败: ' + (data.error || 'unknown'));
    }
  }

  async function createProject() {
    const cid = DOM.customerSelect.value;
    if (!cid) { alert('请先选择客户'); return; }
    const name = prompt('输入项目名称：');
    if (!name || !name.trim()) return;
    const species = STATE.currentSpecies || 'human';
    const data = await _apiPost(`/api/customer/${cid}/project/create`, {
      project_name: name.trim(),
      species: species,
    });
    if (data.ok) {
      STATE.activeProjectId = data.project_id;
      await loadCustomerList();
      DOM.projectSelect.value = data.project_id;
      DOM.customerStatus.textContent = `✅ 已创建项目 ${data.project_id}: ${name.trim()}`;
    } else {
      alert('创建项目失败: ' + (data.error || 'unknown'));
    }
  }

  async function saveCurrentAdjustment() {
    const cid = DOM.customerSelect.value;
    const pid = DOM.projectSelect.value;
    if (!cid || !pid) { alert('请先选择客户和项目'); return; }
    // 收集当前滑杆包
    const packet = collectCurrentPacket();
    if (!packet) { alert('无法获取当前滑杆包'); return; }
    const note = prompt('调整说明（可选）：') || '';
    const data = await _apiPost(`/api/customer/${cid}/project/${pid}/save-adjustment`, {
      packet: packet,
      note: note,
    });
    if (data.ok) {
      DOM.customerStatus.textContent = `✅ 已保存 v${data.version}`;
    } else {
      alert('保存调整失败: ' + (data.error || 'unknown'));
    }
  }

  function collectCurrentPacket() {
    // 从 STATE 收集当前滑杆包
    const macro = STATE.macro || {};
    const holdSeg = STATE.holdSeg || {};
    return {
      schema: STATE.schema || 'slider-packet-v1',
      emotion: STATE.activePreset || '',
      species: STATE.currentSpecies || 'human',
      macro: { ...macro },
      hold_seg: { ...holdSeg },
    };
  }

  async function loadCustomerContext() {
    const data = await _apiGet('/api/customer-context');
    if (data && data.customer_id) {
      STATE.activeCustomerId = data.customer_id;
      STATE.activeProjectId = data.project_id || '';
    }
  }

  /* ═══════════════════════════════════════════════════════
     事件绑定
     ═══════════════════════════════════════════════════════ */
  function bindEvents() {
    DOM.btnSaveCtx.onclick = saveContext;
    DOM.btnSavePacket.onclick = savePacket;
    DOM.btnCopy.onclick = () => navigator.clipboard.writeText(DOM.pipeJson.textContent);
    DOM.pipeFull.onchange = renderPipeJson;
    DOM.btnNeutral.onclick = resetToNeutral;
    DOM.btnRenderNeon.onclick = renderNeonControlVideo;
    DOM.dogBtn.onclick = runDogTest;

    document.querySelectorAll('.species-btn').forEach((b) => {
      b.onclick = () => switchSpecies(b.dataset.species);
    });

    // 客户资产库事件
    DOM.customerSelect.onchange = async () => {
      STATE.activeCustomerId = DOM.customerSelect.value;
      await loadProjectList(STATE.activeCustomerId);
      await saveCustomerContext();
    };
    DOM.projectSelect.onchange = async () => {
      STATE.activeProjectId = DOM.projectSelect.value;
      await saveCustomerContext();
    };
    DOM.btnCustomerNew.onclick = createCustomer;
    DOM.btnProjectNew.onclick = createProject;
    DOM.btnCustomerSaveCtx.onclick = saveCustomerContext;
    DOM.btnCustomerSaveAdj.onclick = saveCurrentAdjustment;
  }

  /* ═══════════════════════════════════════════════════════
     启动
     ═══════════════════════════════════════════════════════ */
  async function boot() {
    await healthCheck();
    const ok = await loadControlSurface();
    if (!ok) return;

    STATE.macro = { ...STATE.neutral.macro };
    STATE.holdSeg = { ...STATE.neutral.hold_seg };

    buildPipeTabs();
    buildPresets();
    buildZones();
    loadContext();
    try { await loadSliderPacket(); } catch (e) { /* ignore */ }
    loadPersonaMatrix();
    loadAssetBrowser();
    // 客户资产库
    await loadCustomerContext();
    await loadCustomerList();
    if (STATE.activeCustomerId) {
      DOM.customerSelect.value = STATE.activeCustomerId;
      await loadProjectList(STATE.activeCustomerId);
    }
    bindEvents();
    paint();
  }

  // 暴露给全局（资产库浏览器 onclick 回调）
  window.app = { loadBakedAsset };

  // 启动
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();