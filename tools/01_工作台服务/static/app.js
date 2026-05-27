/* ═══════════════════════════════════════════════════════
   能量工作台 v13 · 主应用
   ═══════════════════════════════════════════════════════ */
(function(){'use strict';

/* ── DOM 引用 ── */
const $ = id => document.getElementById(id);
const D = {
  nl:$('nl-input'), prompt:$('prompt-input'), kb:$('kb-input'),
  presetStatus:$('preset-status'), presetList:$('preset-list'),
  presetHint:$('preset-hint'), emotionTitle:$('emotion-title'),
  pulseInfo:$('pulse-info'), l1Msg:$('l1-fix-msg'),
  curve:$('curve'), zoneRise:$('zone-rise'), zoneMove:$('zone-move'), zoneFall:$('zone-fall'),
  neonPlaceholder:$('neon-placeholder'), neonVideo:$('neon-video'),
  neonStatus:$('neon-status'), btnRenderNeon:$('btn-render-neon'),
  pipeTabs:$('pipe-tabs'), pipeJson:$('pipe-json'), pipeSource:$('pipe-source'),
  pipeFull:$('pipe-full'), btnSaveCtx:$('btn-save-ctx'),
  btnSavePacket:$('btn-save-packet'), btnCopy:$('btn-copy'), btnNeutral:$('btn-neutral'),
  assetTree:$('asset-tree'),
  styleCard:$('style-card'), styleTitle:$('style-title'), styleList:$('style-list'),
  styleHint:$('style-hint'), styleBadge:$('style-badge'),
  customerSelect:$('customer-select'), projectSelect:$('project-select'),
  btnCustomerNew:$('btn-customer-new'), btnProjectNew:$('btn-project-new'),
  btnCustomerSaveCtx:$('btn-customer-save-ctx'), btnCustomerSaveAdj:$('btn-customer-save-adj'),
  customerProjectBlock:$('customer-project-block'), customerActions:$('customer-actions'),
  customerStatus:$('customer-status'),
  photoUploadInput:$('photo-upload-input'), btnPhotoUpload:$('btn-photo-upload'),
  photoPreview:$('photo-preview'), photoDetectionResult:$('photo-detection-result'),
};

/* ── 状态 ── */
const S = {
  schema:'slider-packet-v1', zones:{}, presetGroups:[], presets:{},
  shapeOpts:[], macroIds:[], holdIds:[], validShapes:[], pipeTabs:[],
  neutral:{macro:{push:50,power:50,speed:50,steady:50,grip:50,outro:50},hold_seg:{shape:'flat',pulse_rate:0,pulse_depth:0,swell:0}},
  macro:{}, holdSeg:{}, activePreset:'', pipelineData:null, activePipeTab:'1_slider_packet',
  loadToken:0, loading:false, currentSpecies:'human',
  customers:[], projects:[], activeCustomerId:'', activeProjectId:'', currentPacket:null,
  currentStyleId:'', styles:null,
};
S.macro={...S.neutral.macro}; S.holdSeg={...S.neutral.hold_seg};

const clamp = v => Math.max(0,Math.min(100,Math.round(Number(v))));

/* ── 物种数据 ── */
const SPECIES = {
  human:{label:'人类',icon:'🙂',hint:'选情绪 = 自动填充滑杆 · 再微调 = 自定义'},
  cat:{label:'猫',icon:'🐱',hint:'🐱 猫情绪预设',
    presets:{
      cat_alarm_stare:'警觉·盯 · 竖耳缩瞳', cat_hunt_fixate:'狩猎·锁定 · 伏低',
      cat_startle_fluff:'惊吓·炸毛 · 飞机耳', cat_curious_tilt:'好奇·歪头 · 一耳前一耳后',
      cat_cuddle_squint:'撒娇·眯眼 · 慢眨眼', cat_content_bliss:'满足·飘然 · 眯眼成线',
      cat_annoyed_swish:'不耐烦 · 耳朵背过去', cat_scared_flatten:'恐惧·贴地 · 全飞机耳',
      cat_sad_whimper:'委屈·呜咽 · 眼湿润', cat_angry_hiss:'愤怒·哈气 · 瞳孔缩线',
      cat_sleepy_droop:'困倦·迷离 · 眼皮下垂', cat_play_pounce:'玩耍·扑击 · 瞳孔放大',
    },
    groups:[
      {label:'警觉 · 攻击',keys:['cat_alarm_stare','cat_hunt_fixate','cat_angry_hiss']},
      {label:'恐惧 · 退缩',keys:['cat_startle_fluff','cat_scared_flatten','cat_sad_whimper']},
      {label:'亲昵 · 放松',keys:['cat_cuddle_squint','cat_content_bliss','cat_sleepy_droop']},
      {label:'好奇 · 玩耍',keys:['cat_curious_tilt','cat_play_pounce','cat_annoyed_swish']},
    ]},
  dog:{label:'狗',icon:'🐶',hint:'🐶 狗情绪预设',
    presets:{
      dog_alert_bark:'警觉·吠 · 竖耳', dog_happy_wag:'开心·摇尾 · 放松眼',
      dog_sad_puppy:'委屈·幼犬眼 · 挑眉上翻', dog_scared_tuck:'恐惧·夹尾 · 耳后贴',
      dog_angry_growl:'愤怒·低吼 · 竖耳前倾', dog_curious_cock:'好奇·歪头 · 单耳竖',
      dog_submissive_look:'服从·回避 · 眼神避开', dog_play_bow:'邀玩·趴 · 瞳孔放大',
      dog_guilty_side:'心虚·偷瞄 · 耳耷拉', dog_content_sigh:'满足·叹气 · 半闭眼',
    },
    groups:[
      {label:'警觉 · 攻击',keys:['dog_alert_bark','dog_angry_growl','dog_scared_tuck']},
      {label:'亲昵 · 放松',keys:['dog_happy_wag','dog_content_sigh','dog_sad_puppy']},
      {label:'好奇 · 玩耍',keys:['dog_curious_cock','dog_play_bow','dog_guilty_side']},
      {label:'服从 · 回避',keys:['dog_submissive_look']},
    ]},
};

/* ── 风格包 / 品种数据（与 预设资产/风格包/ 目录完全一致）──── */
const STYLE_ICONS = {
  human:{icon:'🧬', label:'人格风格'},
  cat:{icon:'🐱', label:'猫品种'},
  dog:{icon:'🐶', label:'狗品种'},
};
/* ── 确保风格包 DOM 元素存在（防止 HTML 缓存导致缺失） ── */
function ensureStyleCard(){
  if(D.styleCard) return;
  // 在情绪预设卡片之后动态插入风格卡
  const emotionCard=document.querySelector('.card:nth-child(2)');
  if(!emotionCard) return;
  const wrapper=document.createElement('div');
  wrapper.innerHTML=
    '<div class="card" id="style-card">'
    +'<div class="card-header"><span id="style-title">🎨 风格包</span>'
    +'<span class="style-badge" id="style-badge" style="font-size:0.62rem;color:var(--muted)"></span></div>'
    +'<p class="preset-hint" id="style-hint">选情绪后显示对应的风格/品种选项</p>'
    +'<div class="preset-scroll" id="style-list"></div></div>';
  const card=wrapper.firstElementChild;
  emotionCard.parentNode.insertBefore(card, emotionCard.nextSibling);
  // 重新绑定 D 引用
  D.styleCard=card;
  D.styleTitle=card.querySelector('#style-title');
  D.styleList=card.querySelector('#style-list');
  D.styleHint=card.querySelector('#style-hint');
  D.styleBadge=card.querySelector('#style-badge');
}

async function loadStyles(){
  ensureStyleCard();
  try{
    const d=await fetchJSON('/api/styles');
    if(d.ok && d.styles) { S.styles=d.styles; return; }
  }catch(e){ /* fallback */ }
  // 后备数据（与 预设资产/风格包/ 完全一致）
  S.styles={
    human:[
      {id:'悲悯者_圣徒',     label:'悲悯者/圣徒',     notes:'悲天悯人，圣洁温厚'},
      {id:'呆滞者_傀儡',     label:'呆滞者/傀儡',     notes:'空洞失神，反应迟钝'},
      {id:'癫狂者_疯僧',     label:'癫狂者/疯僧',     notes:'疯癫狂乱，不可预测'},
      {id:'狠厉者_铁血将军', label:'狠厉者/铁血将军', notes:'铁血无情，杀气凌厉'},
      {id:'魅惑者_部落巫医', label:'魅惑者/部落巫医', notes:'妖冶诱惑，神秘感十足'},
      {id:'魅惑者_温碧霞',   label:'魅惑者/温碧霞',   notes:'温碧霞风格，眼波流转'},
      {id:'怯弱者_逃兵',     label:'怯弱者/逃兵',     notes:'畏缩怯懦，眼神躲闪'},
      {id:'天选者_大祭司',   label:'天选者/大祭司',   notes:'冷峻克制，天生压迫感'},
      {id:'天真者_幼童',     label:'天真者/幼童',     notes:'天真无邪，纯净明亮'},
    ],
    cat:[
      {id:'british_cat', label:'英短/憨厚型',   notes:'英短/憨厚型 品种风格偏移'},
      {id:'ragdoll_cat', label:'布偶猫/温顺型', notes:'布偶猫/温顺型 品种风格偏移'},
      {id:'siamese_cat', label:'暹罗猫/高冷型', notes:'暹罗猫/高冷型 品种风格偏移'},
      {id:'stray_cat',   label:'田园猫/机敏型', notes:'田园猫/机敏型 品种风格偏移'},
    ],
    dog:[
      {id:'poodle_giant', label:'巨型贵宾犬/优雅型', notes:'巨型贵宾犬/优雅型 品种风格偏移'},
    ],
  };
  // 立即渲染默认物种（human）的风格按钮
  renderStyleButtons();
}

function renderStyleButtons(){
  const items=S.styles?.[S.currentSpecies];
  if(!items||!items.length) return;
  D.styleList.innerHTML='';
  items.forEach(item=>{
    const btn=document.createElement('button'); btn.className='style-btn';
    btn.dataset.style=item.id;
    btn.innerHTML=item.label+'<small>'+(item.notes||'')+'</small>';
    btn.onclick=()=>selectStyle(item.id);
    D.styleList.appendChild(btn);
  });
  const meta=STYLE_ICONS[S.currentSpecies]||{icon:'🎨', label:'风格'};
  D.styleTitle.textContent=meta.icon+' '+meta.label;
  D.styleBadge.textContent=items.length+' 个选项';
  D.styleCard.style.display='block';
}
/* ── 通知 ── */
function notify(msg,type='info'){
  const el=document.createElement('div');
  el.className='notification '+type; el.textContent=msg;
  document.body.appendChild(el);
  setTimeout(()=>el.remove(),3000);
}

/* ── API 工具 ── */
async function fetchJSON(url,opts={}){
  const r=await fetch(url,{cache:'no-store',...opts});
  const t=await r.text();
  if(!r.ok) throw new Error(t.slice(0,200));
  return JSON.parse(t);
}
async function apiPost(path,body){
  try{ return await fetchJSON(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); }
  catch(e){ return {ok:false,error:String(e)}; }
}

/* ── 第1节：控制面加载 ── */
function applySurface(data){
  S.schema=data.schema||S.schema; S.zones=data.zones||{};
  S.presetGroups=data.preset_groups||[]; S.presets=data.presets||{};
  S.shapeOpts=data.shape_opts||[]; S.macroIds=data.macro_ids||[];
  S.holdIds=data.hold_ids||[]; S.validShapes=data.valid_shapes||[];
  S.neutral=data.neutral||S.neutral; S.pipeTabs=data.pipe_tabs||[];
}
async function loadControlSurface(){
  if(location.protocol==='file:'){ D.presetStatus.className='preset-status err'; D.presetStatus.textContent='⚠ 请通过 HTTP 访问'; return false; }
  try{
    const d=await fetchJSON('/control_surface.json');
    applySurface(d);
    D.presetStatus.className='preset-status ok';
    D.presetStatus.textContent='✅ v'+d.version+' 就绪 · '+Object.keys(S.presets).length+' 种情绪';
    return true;
  }catch(e){ D.presetStatus.className='preset-status err'; D.presetStatus.textContent='⚠ 控制面加载失败'; return false; }
}

/* ── 第2节：预设按钮 & 物种 ── */
function buildPresets(){
  D.presetList.innerHTML='';
  const sp=SPECIES[S.currentSpecies];
  const groups=S.currentSpecies==='human'?S.presetGroups:sp.groups;
  const presets=S.currentSpecies==='human'?S.presets:sp.presets;
  groups.forEach(g=>{
    const hd=document.createElement('div'); hd.className='preset-group'; hd.textContent=g.label;
    D.presetList.appendChild(hd);
    g.keys.forEach(key=>{
      const data=presets[key]; if(!data) return;
      const btn=document.createElement('button'); btn.className='preset-btn';
      btn.dataset.preset=key;
      btn.innerHTML=key+'<small>'+(data.note||data)+'</small>';
      btn.onclick=()=>selectEmotion(key);
      D.presetList.appendChild(btn);
    });
  });
}
function switchSpecies(sp){
  S.currentSpecies=sp;
  document.querySelectorAll('.species-btn').forEach(b=>b.classList.toggle('active',b.dataset.species===sp));
  D.presetHint.textContent=SPECIES[sp].hint;
  const count=sp==='human'?Object.keys(S.presets).length:Object.keys(SPECIES[sp].presets).length;
  D.emotionTitle.textContent=count+' 种情绪预设';
  S.currentStyleId='';
  renderStyleButtons();
  buildPresets(); highlightPreset(''); resetToNeutral();
}
function highlightPreset(name){
  document.querySelectorAll('.preset-btn').forEach(b=>b.classList.toggle('active',b.dataset.preset===name));
}
async function selectEmotion(name){
  const data=S.currentSpecies==='human'?S.presets[name]:SPECIES[S.currentSpecies].presets[name];
  if(!data||(!S.loading&&S.activePreset===name)){ highlightPreset(name); return; }
  const token=++S.loadToken; S.loading=true;
  S.activePreset=name; S.macro={...data.macro}; S.holdSeg={...data.hold_seg}; S.pipelineData=null;
  highlightPreset(name);
  renderStyleButtons();
  try{ if(token===S.loadToken) paint(); }finally{ if(token===S.loadToken) S.loading=false; }
}
function resetToNeutral(){
  S.loadToken++; S.activePreset=''; S.macro={...S.neutral.macro}; S.holdSeg={...S.neutral.hold_seg}; S.pipelineData=null;
  highlightPreset(''); paint();
  S.currentStyleId='';
}

/* ── 风格包 / 品种选择（数据源自后端 /api/styles 或后备 FALLBACK_STYLES） ── */
function buildStyleList(){
  const items=S.styles?.[S.currentSpecies];
  if(!items||!items.length){
    console.warn('[style] 无风格数据, species='+S.currentSpecies, S.styles);
    D.styleList.innerHTML='<p class="text-muted text-sm" style="padding:12px;text-align:center">⚠ 无可用风格包数据</p>';
    D.styleCard.style.display='block';
    return;
  }
  const meta=STYLE_ICONS[S.currentSpecies]||{icon:'🎨', label:'风格'};
  D.styleTitle.textContent=meta.icon+' '+meta.label;
  D.styleHint.textContent='选情绪后，选择对应的'+meta.label+'以叠加风格偏移';
  D.styleBadge.textContent=items.length+' 个选项';
  D.styleList.innerHTML='';
  items.forEach(item=>{
    const btn=document.createElement('button'); btn.className='style-btn';
    btn.dataset.style=item.id;
    btn.innerHTML=item.label+'<small>'+(item.notes||'')+'</small>';
    btn.onclick=()=>selectStyle(item.id);
    if(item.id===S.currentStyleId) btn.classList.add('active');
    D.styleList.appendChild(btn);
  });
}
function highlightStyle(id){
  D.styleList.querySelectorAll('.style-btn').forEach(b=>b.classList.toggle('active',b.dataset.style===id));
}
function selectStyle(id){
  S.currentStyleId=id;
  highlightStyle(id);
  // 可在此处触发风格包加载/叠加逻辑
  notify('✅ 已选风格: '+id,'success');
}

/* ── 第3节：滑杆构建 ── */
function buildKnob(k,spec){
  const div=document.createElement('div'); div.className='knob';
  const label=document.createElement('label'); label.textContent=spec.label;
  const input=document.createElement('input'); input.type='range'; input.min=0; input.max=100;
  input.dataset.key=k; input.dataset.spec=spec.id;
  input.value=(k==='macro'?S.macro[spec.id]:S.holdSeg[spec.id])||0;
  const valSpan=document.createElement('span'); valSpan.className='val'; valSpan.textContent=input.value;
  const update=()=>{
    const v=Number(input.value);
    if(k==='macro') S.macro[spec.id]=v; else S.holdSeg[spec.id]=v;
    valSpan.textContent=v; S.activePreset=''; highlightPreset(''); paint();
  };
  input.oninput=update;
  div.appendChild(label); div.appendChild(input); div.appendChild(valSpan);
  return div;
}
function buildZones(){
  ['rise','move','fall'].forEach(zid=>{
    const z=S.zones[zid]; const root=document.getElementById('zone-'+zid);
    if(!z){ root.innerHTML=''; return; }
    let html='<div class="zone-header">'+z.title+'<span>'+(z.sub||'')+'</span></div>';
    if(z.shapes){
      html+='<div class="shape-row" id="shape-row-'+zid+'">';
      S.shapeOpts.forEach(s=>{html+='<button class="shape-btn" data-shape="'+s.id+'" data-zone="'+zid+'">'+s.label+'</button>';});
      html+='</div>';
    }
    root.innerHTML=html;
    if(z.shapes) root.querySelectorAll('.shape-btn').forEach(btn=>{btn.onclick=()=>{S.holdSeg.shape=btn.dataset.shape; paint();};});
    (z.knobs||[]).forEach(spec=>{if(spec.type!=='shape') root.appendChild(buildKnob(spec.k,spec));});
  });
}

/* ── 第4节：SVG 脉冲曲线 ── */
function paint(){
  document.querySelectorAll('.knob input').forEach(inp=>{
    const k=inp.dataset.key,id=inp.dataset.spec; if(!k||!id)return;
    const src=k==='macro'?S.macro:S.holdSeg;
    if(src[id]!==undefined) inp.value=src[id];
    const vs=inp.nextElementSibling; if(vs&&vs.className==='val') vs.textContent=inp.value;
  });
  document.querySelectorAll('.shape-btn').forEach(b=>b.classList.toggle('active',b.dataset.shape===S.holdSeg.shape));
  const W=300,H=100,m=S.macro,h=S.holdSeg;
  let html='<rect width="300" height="100" fill="#fafbfd"/>'
    +'<rect x="0" y="0" width="60" height="100" fill="#dbeafe" opacity="0.4"/>'
    +'<rect x="60" y="0" width="180" height="100" fill="#fef3c7" opacity="0.4"/>'
    +'<rect x="240" y="0" width="60" height="100" fill="#e0e7ff" opacity="0.4"/>';
  const push=m.push/100,power=m.power/100,speed=m.speed/100,steady=m.steady/100,grip=m.grip/100,outro=m.outro/100;
  const tPeak=14+(1-speed)*10,peakY=H-(15+power*65),tHold=30+steady*60,tOutro=tHold+(1-outro)*40,holdY=peakY+(1-grip)*10;
  let d='M0,'+H;
  for(let t=0;t<=tPeak;t++){const u=t/tPeak;d+=' L'+(t/150*W)+','+Math.round(H-u*(H-peakY)*(push>0.5?1+(push-0.5)*0.4:1));}
  for(let t=tPeak+1;t<=tHold;t++){
    const u=(t-tPeak)/(tHold-tPeak); let y=peakY+(holdY-peakY)*u;
    if(h.shape==='tremble') y+=Math.sin(u*20)*4;
    if(h.shape==='pulse') y+=Math.sin(u*h.pulse_rate*0.3)*h.pulse_depth*0.3;
    if(h.shape==='decay') y+=u*20;
    if(h.shape==='swell') y-=Math.sin(Math.PI*u)*h.swell*0.3;
    d+=' L'+(t/150*W)+','+Math.round(Math.max(peakY-10,Math.min(H,y)));
  }
  for(let t=tHold+1;t<=150;t++){const u=(t-tHold)/(150-tHold);d+=' L'+(t/150*W)+','+Math.round(holdY+(H-holdY)*(u<0.5?2*u*u:-1+(4-2*u)*u));}
  html+='<path d="'+d+'" fill="none" stroke="'+(m.push>50?'#3b82f6':'#d97706')+'" stroke-width="2.5" stroke-linejoin="round"/>';
  html+='<line x1="'+(tPeak/150*W)+'" y1="0" x2="'+(tPeak/150*W)+'" y2="100" stroke="#3b82f6" stroke-width="0.5" stroke-dasharray="3,4" opacity="0.5"/>';
  html+='<line x1="'+(tHold/150*W)+'" y1="0" x2="'+(tHold/150*W)+'" y2="100" stroke="#d97706" stroke-width="0.5" stroke-dasharray="3,4" opacity="0.5"/>';
  D.curve.innerHTML=html;
  D.pulseInfo.textContent='起峰:'+Math.round(tPeak)+'f · 盯住:'+Math.round(tPeak)+'→'+Math.round(tHold)+'f · 收场:'+Math.round(tHold)+'→150f · 力度:'+m.power;
}

/* ── 第5节：数据包 ── */
function buildPacket(){ return {schema:S.schema,emotion:S.activePreset||'',macro:{...S.macro},hold_seg:{...S.holdSeg}}; }
function collectCurrentPacket(){ return {schema:S.schema||'slider-packet-v1',emotion:S.activePreset||'',species:S.currentSpecies||'human',macro:{...S.macro||{}},hold_seg:{...S.holdSeg||{}}}; }

/* ── 第6节：交付链面板 ── */
function buildPipeTabs(){
  D.pipeTabs.innerHTML='';
  S.pipeTabs.forEach(tab=>{
    const btn=document.createElement('button'); btn.className='pipe-tab';
    btn.innerHTML=tab.title+(tab.sub?'<small>'+tab.sub+'</small>':'');
    btn.dataset.tab=tab.id; btn.onclick=()=>{S.activePipeTab=tab.id;renderPipeJson();};
    D.pipeTabs.appendChild(btn);
  });
}
function renderPipeJson(){
  D.pipeTabs.querySelectorAll('.pipe-tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===S.activePipeTab));
  if(!S.pipelineData){
    D.pipeJson.textContent=JSON.stringify(buildPacket(),null,2);
    D.pipeSource.textContent='⚠ 前端草稿（非出厂定稿）· 选情绪或点编译'; D.pipeSource.className='pipe-source warn'; return;
  }
  const tab=S.activePipeTab; let obj;
  if(tab==='1_slider_packet') obj=S.pipelineData.slider_packet||buildPacket();
  else if(tab==='2_envelope') obj=S.pipelineData.energy_envelope||S.pipelineData.envelope||{};
  else if(['3_dense_env','4_dense_prior','4b_pulse_quality_report'].includes(tab)){
    obj=S.pipelineData.channel_tracks||S.pipelineData.channels||{};
    if(!D.pipeFull.checked){const s={};Object.keys(obj).forEach(k=>{s[k]=Array.isArray(obj[k])&&obj[k].length>10?'[150 frames, first 5]: '+JSON.stringify(obj[k].slice(0,5)):obj[k];});obj=s;}
  }else obj=S.pipelineData;
  D.pipeJson.textContent=JSON.stringify(obj,null,2);
  D.pipeSource.textContent='✓ 出厂定稿 · '+(S.pipelineData.emotion||S.pipelineData.mood||''); D.pipeSource.className='pipe-source ok';
}

/* ── 第7节：上下文 & 保存 ── */
async function loadContext(){
  try{const c=await fetchJSON('/workbench_context.json');if(c.natural_language)D.nl.value=c.natural_language;if(c.energy_map_note||c.prompt)D.prompt.value=c.energy_map_note||c.prompt;if(c.knowledge_base)D.kb.value=c.knowledge_base;}catch(e){}
}
async function saveContext(){
  const j=await apiPost('/save_context',{natural_language:D.nl.value.trim(),energy_map_note:D.prompt.value.trim(),knowledge_base:D.kb.value.trim()});
  notify(j.ok?'✅ 上下文已保存':'保存失败',j.ok?'success':'error');
}
async function savePacket(){
  const j=await apiPost('/save_packet',buildPacket());
  notify(j.ok?'✅ 已保存到资产库':'保存失败',j.ok?'success':'error');
}

/* ── 第8节：2D 霓虹控制视频 ── */
async function renderNeon(){
  D.btnRenderNeon.disabled=true; D.btnRenderNeon.textContent='⏳ 渲染中…';
  D.neonStatus.textContent='⏳ 编译管线…'; D.neonPlaceholder.style.display='none'; D.neonVideo.style.display='none';
  try{
    const j=await apiPost('/render_control_video',buildPacket());
    if(!j.ok){D.neonStatus.textContent='渲染失败: '+(j.error||j.message||JSON.stringify(j));return;}
    const url=(j.path||'/control_video.mp4')+'?t='+Date.now();
    D.neonVideo.src=url; D.neonVideo.style.display='block'; D.neonVideo.load();
    D.neonVideo.onloadeddata=()=>{D.neonStatus.textContent='✓ 2D 霓虹控制流就绪 · 播放中';D.neonVideo.play().catch(()=>{});};
    D.neonVideo.onerror=()=>{D.neonStatus.textContent='视频加载失败';D.neonVideo.style.display='none';D.neonPlaceholder.style.display='flex';};
  }catch(e){D.neonStatus.textContent='网络错误: '+(e.message||e);}
  finally{D.btnRenderNeon.disabled=false; D.btnRenderNeon.textContent='🎞 渲染 2D 控制流';}
}

/* ── 第9节：资产库浏览器 ── */
async function loadAssetBrowser(){
  try{
    const d=await fetchJSON('/api/asset-browser');
    if(!d.ok||!d.root) throw new Error('无效响应');
    let html='';
    function walk(items,depth){
      if(!items||!items.length){html='<p class="text-muted text-sm" style="padding:8px;text-align:center">（空）</p>';return;}
      items.forEach(item=>{
        if(item.type==='dir'){
          html+='<div style="padding:1px 0"><span style="display:inline-block;width:'+(depth*14)+'px"></span>📁 <strong>'+item.name+'</strong></div>';
          if(item.children) walk(item.children,depth+1);
        }else{
          const icon=item.tag==='烘焙'?'🎯':item.tag==='节拍表'?'📋':item.tag==='人格'?'🧬':item.tag==='情绪'?'🎭':'📄';
          const tag=item.tag?' <span class="asset-tag">'+item.tag+'</span>':'';
          const size=item.size?' <span class="asset-size">'+(item.size>1024?(item.size/1024).toFixed(1)+'KB':item.size+'B')+'</span>':'';
          const clickable=item.tag==='烘焙'&&item.ext==='.json';
          html+='<div class="file-item'+(clickable?' clickable':'')+'"'+(clickable?' onclick="window.app.loadBaked(\''+item.name.replace(/'/g,"\\'")+'\')"':'')+'>'
            +'<span style="display:inline-block;width:'+(depth*14)+'px"></span><span>'+icon+'</span> '+item.name+tag+size+'</div>';
        }
      });
    }
    walk(d.root,0);
    D.assetTree.innerHTML=html;
  }catch(e){D.assetTree.innerHTML='<p class="text-muted text-sm" style="padding:8px;text-align:center">⚠ '+e.message+'</p>';}
}
async function loadBakedAsset(filename){
  try{
    const d=await fetchJSON('/api/asset-browser');
    let found='';
    function search(items,prefix){items?.forEach(item=>{if(item.type==='dir'&&item.children)search(item.children,prefix+item.name+'/');else if(item.name===filename)found=prefix+item.name;});}
    search(d.root,'');
    if(!found){notify('未找到文件路径','error');return;}
    const result=await apiPost('/api/asset-load-baked',{path:found,packet:buildPacket()});
    if(!result.ok){notify('加载失败: '+(result.error||''),'error');return;}
    if(result.baked){
      S.pipelineData=result.baked; S.activePipeTab='5_baked_02_delivery'; renderPipeJson();
      if(result.packet?.macro){S.macro={...result.packet.macro};if(result.packet.hold_seg)S.holdSeg={...result.packet.hold_seg};if(result.packet.emotion)S.activePreset=result.packet.emotion;highlightPreset(S.activePreset);paint();}
      D.pipeSource.textContent='✓ 已加载: '+found; D.pipeSource.className='pipe-source ok';
      notify('✅ 已加载烘焙资产','success');
    }
  }catch(e){notify('加载失败: '+e.message,'error');}
}

/* ── 第12节：客户资产库 ── */
async function loadCustomerList(){
  const d=await apiPost('/api/customer-list',{});
  if(!d.ok) return;
  S.customers=d.customers||[];
  D.customerSelect.innerHTML='<option value="">— 不选择 —</option>';
  S.customers.forEach(c=>{const o=document.createElement('option');o.value=c.customer_id;o.textContent=c.display_name||c.customer_id;D.customerSelect.appendChild(o);});
  if(S.activeCustomerId) D.customerSelect.value=S.activeCustomerId;
}
async function loadCustomerPhotos(cid){
  if(!cid){D.photoPreview.innerHTML='';D.photoDetectionResult.textContent='';D.btnPhotoUpload.disabled=true;return;}
  const d=await apiPost('/api/customer/photos/'+cid,{});
  if(!d.ok){D.btnPhotoUpload.disabled=false;return;}
  D.btnPhotoUpload.disabled=false;
  D.photoPreview.innerHTML='';
  if(d.photos?.length) d.photos.forEach(p=>{const img=document.createElement('img');img.src=p.url;img.style.cssText='width:80px;height:80px;object-fit:cover;border-radius:4px;border:1px solid #dee2e6';img.title=p.name;D.photoPreview.appendChild(img);});
  if(d.has_template_params&&d.template_params){
    const t=d.template_params,parts=[];if(t.eye_distance&&t.eye_distance!==1)parts.push('眼距 '+t.eye_distance+'x');if(t.eye_size&&t.eye_size!==1)parts.push('眼大小 '+t.eye_size+'x');
    D.photoDetectionResult.textContent='✅ 底膜已适配: '+(parts.join(', ')||'标准'); D.photoDetectionResult.style.color='#28a745';
  }else if(d.photos?.length){D.photoDetectionResult.textContent='⏳ 照片已上传，点击"检测底膜"完成适配';D.photoDetectionResult.style.color='#ffc107';}
  else{D.photoDetectionResult.textContent='📸 上传正面照片自动适配底膜';D.photoDetectionResult.style.color='#6c757d';}
}
async function loadProjectList(cid){
  if(!cid){D.projectSelect.innerHTML='<option value="">— 先选客户 —</option>';D.customerProjectBlock.style.display='none';D.customerActions.style.display='none';return;}
  D.customerProjectBlock.style.display='block';
  D.projectSelect.innerHTML='<option value="">— 不选择 —</option>';
  if(S.activeProjectId) D.projectSelect.value=S.activeProjectId;
  await loadCustomerPhotos(cid);
}
async function saveCustomerContext(){
  const cid=D.customerSelect.value,pid=D.projectSelect.value||'';
  S.activeCustomerId=cid; S.activeProjectId=pid;
  const d=await apiPost('/api/customer-context/save',{customer_id:cid,project_id:pid});
  if(d.ok) D.customerStatus.textContent=cid?'✅ 当前: '+cid+(pid?' / '+pid:''):'已清除';
  await loadProjectList(cid);
}
async function createCustomer(){
  const name=prompt('输入客户名称：'); if(!name||!name.trim()) return;
  const d=await apiPost('/api/customer/create',{display_name:name.trim()});
  if(d.ok){await loadCustomerList();D.customerSelect.value=d.customer_id;S.activeCustomerId=d.customer_id;await saveCustomerContext();D.customerStatus.textContent='✅ 已创建客户 '+d.customer_id+': '+name.trim();}
  else alert('创建失败: '+(d.error||'unknown'));
}
async function createProject(){
  const cid=D.customerSelect.value; if(!cid){alert('请先选择客户');return;}
  const name=prompt('输入项目名称：'); if(!name||!name.trim()) return;
  const d=await apiPost('/api/customer/'+cid+'/project/create',{project_name:name.trim(),species:S.currentSpecies||'human'});
  if(d.ok){S.activeProjectId=d.project_id;await loadCustomerList();D.projectSelect.value=d.project_id;D.customerStatus.textContent='✅ 已创建项目 '+d.project_id+': '+name.trim();}
  else alert('创建项目失败: '+(d.error||'unknown'));
}
async function saveCurrentAdjustment(){
  const cid=D.customerSelect.value,pid=D.projectSelect.value; if(!cid||!pid){alert('请先选择客户和项目');return;}
  const note=prompt('调整说明（可选）：')||'';
  const d=await apiPost('/api/customer/'+cid+'/project/'+pid+'/save-adjustment',{packet:collectCurrentPacket(),note:note});
  if(d.ok) D.customerStatus.textContent='✅ 已保存 v'+d.version; else alert('保存调整失败: '+(d.error||'unknown'));
}
async function uploadCustomerPhoto(){
  const cid=D.customerSelect.value; if(!cid){alert('请先选择客户');return;}
  const file=D.photoUploadInput.files?.[0]; if(!file){alert('请选择一张照片');return;}
  D.btnPhotoUpload.disabled=true; D.btnPhotoUpload.textContent='⏳ 检测中…'; D.photoDetectionResult.textContent='正在分析照片…';
  try{
    const b64=await new Promise((res,rej)=>{const r=new FileReader();r.onload=()=>res(r.result.split(',')[1]);r.onerror=rej;r.readAsDataURL(file);});
    const r=await apiPost('/api/customer/upload-photo',{customer_id:cid,species:S.currentSpecies||'human',photo_name:file.name,photo_data:b64});
    if(r.ok){
      const adj=r.adjustments||{},parts=[];if(adj.eye_distance)parts.push('眼距 '+adj.eye_distance+'x');if(adj.eye_size)parts.push('眼大小 '+adj.eye_size+'x');if(adj.ear_droop!==undefined)parts.push('耳垂 '+adj.ear_droop);
      D.photoDetectionResult.textContent='✅ 底膜已自动适配: '+(parts.join(', ')||'标准'); D.photoDetectionResult.style.color='#28a745';
      D.customerStatus.textContent='✅ 客户 '+cid+': 底膜已检测 ('+parts.join(', ')+')';
      await loadCustomerPhotos(cid);
    }else{D.photoDetectionResult.textContent='❌ 检测失败: '+(r.error||'未知错误');D.photoDetectionResult.style.color='#dc3545';}
  }catch(e){D.photoDetectionResult.textContent='❌ 网络错误: '+e.message;D.photoDetectionResult.style.color='#dc3545';}
  finally{D.btnPhotoUpload.disabled=false; D.btnPhotoUpload.textContent='检测底膜'; D.photoUploadInput.value='';}
}
async function loadCustomerContext(){
  const d=await apiPost('/api/customer-context',{});
  if(d?.customer_id){S.activeCustomerId=d.customer_id;S.activeProjectId=d.project_id||'';}
}

/* ── 启动 ── */
async function boot(){
  if(location.protocol==='file:'){D.pipeSource.textContent='⚠ 请启动工作台';D.pipeSource.className='pipe-source warn';return;}
  try{const h=await fetchJSON('/health');D.pipeSource.textContent=h.ok?'✓ 服务 v'+h.version:'⚠ 服务异常';D.pipeSource.className=h.ok?'pipe-source ok':'pipe-source warn';}catch(e){D.pipeSource.textContent='⚠ 服务异常';D.pipeSource.className='pipe-source warn';}
  const ok=await loadControlSurface(); if(!ok) return;
  S.macro={...S.neutral.macro}; S.holdSeg={...S.neutral.hold_seg};
  buildPipeTabs(); buildPresets(); buildZones(); loadContext();
  await loadStyles(); loadAssetBrowser();
  await loadCustomerContext(); await loadCustomerList();
  if(S.activeCustomerId){D.customerSelect.value=S.activeCustomerId;await loadProjectList(S.activeCustomerId);}

  // 事件绑定
  D.btnSaveCtx.onclick=saveContext; D.btnSavePacket.onclick=savePacket;
  D.btnCopy.onclick=()=>navigator.clipboard.writeText(D.pipeJson.textContent);
  D.pipeFull.onchange=renderPipeJson; D.btnNeutral.onclick=resetToNeutral;
  D.btnRenderNeon.onclick=renderNeon;
  document.querySelectorAll('.species-btn').forEach(b=>{b.onclick=()=>switchSpecies(b.dataset.species);});
  D.customerSelect.onchange=async()=>{S.activeCustomerId=D.customerSelect.value;await loadProjectList(S.activeCustomerId);await saveCustomerContext();};
  D.projectSelect.onchange=async()=>{S.activeProjectId=D.projectSelect.value;await saveCustomerContext();};
  D.btnCustomerNew.onclick=createCustomer; D.btnProjectNew.onclick=createProject;
  D.btnCustomerSaveCtx.onclick=saveCustomerContext; D.btnCustomerSaveAdj.onclick=saveCurrentAdjustment;
  D.btnPhotoUpload.onclick=uploadCustomerPhoto;
  D.photoUploadInput.onchange=()=>{D.btnPhotoUpload.disabled=!D.photoUploadInput.files?.length;};
  paint();
}

window.app={loadBaked:loadBakedAsset};

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else boot();
})();