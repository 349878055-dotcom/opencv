/* 客户创作工作室 · portal.js v5
   单按钮入口 → 注册/登录 → 新建项目 → 照片 → 生成 → OpenCV预览 → 04+Wan导出
   数据持久化到 客户资产库/
*/
(function(){'use strict';

const $ = id => document.getElementById(id);
const D = {
  welcome: $('welcome-screen'), registerScreen: $('register-screen'), loginScreen: $('login-screen'),
  dashboard: $('dashboard'), wizard: $('wizard'),
  btnEnter: $('btn-enter'), linkLogin: $('link-login'),
  regName: $('reg-name'), regPwd: $('reg-pwd'), regPwd2: $('reg-pwd2'),
  registerError: $('register-error'), btnRegister: $('btn-register'),
  switchToLogin: $('switch-to-login'), switchToRegister: $('switch-to-register'),
  loginCid: $('login-cid'), loginPwd: $('login-pwd'), loginError: $('login-error'), btnLogin: $('btn-login'),
  loggedUser: $('logged-user'), btnLogout: $('btn-logout'),
  projectList: $('project-list'), projectCount: $('project-count'), btnNewProject: $('btn-new-project'),
  wizardBack: $('wizard-back'), wizardTitle: $('wizard-title'), stepBar: $('step-bar'),
  speciesBanner: $('species-banner'), speciesBannerTags: $('species-banner-tags'),
  speciesBannerMsg: $('species-banner-msg'),
  membraneAlertStep1: $('membrane-alert-step1'), membraneAlertStep4: $('membrane-alert-step4'),
  uploadZone: $('upload-zone'), photoInput: $('photo-input'),
  btnUpload: $('btn-upload'),
  calibrateWrap: $('calibrate-wrap'), calibrateHint: $('calibrate-hint'),
  calibrateStage: $('calibrate-stage'), calibrateImg: $('calibrate-img'),
  calibrateLoadErr: $('calibrate-load-err'),
  calibrateCanvas: $('calibrate-canvas'),
  btnCalibrateUndo: $('btn-calibrate-undo'), btnCalibrateReset: $('btn-calibrate-reset'),
  btnCalibrateSubmit: $('btn-calibrate-submit'),
  earAdjustPanel: $('ear-adjust-panel'), btnMarkEars: $('btn-mark-ears'),
  membranePreviewWrap: $('membrane-preview-wrap'), membranePreviewBreed: $('membrane-preview-breed'),
  membranePreviewCustom: $('membrane-preview-custom'),
  membranePreviewNote: $('membrane-preview-note'), membraneBreedRef: $('membrane-breed-ref'),
  membraneDiffBody: $('membrane-diff-body'),
  membraneDiffEmpty: $('membrane-diff-empty'), membraneDiffWrap: $('membrane-diff-wrap'),
  btnRenderMembrane: $('btn-render-membrane'),
  statusMembrane: $('status-membrane'),
  btnStep1Next: $('btn-step1-next'), status1: $('status-1'),
  speciesSelect: $('species-select'), calibBreedWrap: $('calib-breed-wrap'), calibBreedSelect: $('calib-breed-select'),
  presetContainer: $('preset-container'), styleContainer: $('style-container'),
  presetEmotionTitle: $('preset-emotion-title'), presetEmotionCount: $('preset-emotion-count'),
  presetEmotionHint: $('preset-emotion-hint'), presetStyleTitle: $('preset-style-title'),
  presetStyleCount: $('preset-style-count'), presetStyleHint: $('preset-style-hint'),
  energyPulseWrap: $('energy-pulse-wrap'), energyPulseCurve: $('energy-pulse-curve'),
  energyPulseInfo: $('energy-pulse-info'), energyPulseMacro: $('energy-pulse-macro'),
  energyPulseEmotion: $('energy-pulse-emotion'),
  nlInput: $('nl-input'), btnStep2Prev: $('btn-step2-prev'), btnStep2Next: $('btn-step2-next'),
  btnPomotRun: $('btn-pomot-run'), btnPomotRound2: $('btn-pomot-round2'), pomotSummary: $('pomot-summary'),
  btnStep3Prev: $('btn-step3-prev'), btnStep3Next: $('btn-step3-next'), status3: $('status-3'), stepSaves3: $('step-saves-3'),
  btnStep4Prev: $('btn-step4-prev'), btnRenderVideo: $('btn-render-video'), btnStep4Next: $('btn-step4-next'),
  videoWrap: $('video-wrap'), previewVideo: $('preview-video'), status4: $('status-4'),
  btnStep5Prev: $('btn-step5-prev'), btnSaveAll: $('btn-save-all'), btnExport: $('btn-export'),
  btnDownloadBundle: $('btn-download-bundle'), bundleStatus: $('bundle-status'),
  bundleZipLink: $('bundle-zip-link'), profilePathLine: $('profile-path-line'),
  delivVideoStatus: $('deliv-video-status'), delivVideoLink: $('deliv-video-link'),
  delivVideoMembrane: $('deliv-video-membrane'),
  delivPromptStatus: $('deliv-prompt-status'), delivPromptLink: $('deliv-prompt-link'),
  membraneVerifyLine: $('membrane-verify-line'), membraneBadge: $('membrane-badge'),
  wanClipWrap: $('wan-clip-wrap'), wanPositivePreview: $('wan-positive-preview'),
  wanNegativePreview: $('wan-negative-preview'), btnCopyWanPos: $('btn-copy-wan-pos'),
  btnCopyWanNeg: $('btn-copy-wan-neg'),
  status5: $('status-5'), stepSaves5: $('step-saves-5'),
};

let S = {
  token: localStorage.getItem('portal_token') || '',
  customer: null, customerId: '',
  projects: [], currentProject: null,
  currentStep: 1,
  photoFile: null, photoName: '', photoUrl: '', photoBlobUrl: '', imageWidth: 0, imageHeight: 0,
  detection: null, templateParams: null, calibrated: false, calibratedBreed: '',
  calibBreed: '',
  calibAnchors: {}, calibStepIdx: 0, calibMarkEars: false,
  presets: {human:{emotions:[],styles:[]}, cat:{emotions:[],styles:[]}, dog:{emotions:[],styles:[]}}, // 仅索引 id/label，数值在预设资产库
  activeEmotion: '', activeStyle: '', activeSpecies: 'human',
  lastSplit: null, lastRoute: null, lastPacket: null, lastBaked: null,
  lastMetronome: '', lastPrompt: '', lastWanPositive: '', lastWanNegative: '',
  videoUrl: '', membraneInfo: null,
  membranePreviewUrl: '',
  membraneStatus: null,
  savedSteps: [],
  lastProfile: null, lastBundle: null, bundleZipUrl: '',
};

function archivePayload(extra={}){
  return {
    customer_id: S.customerId,
    project_id: S.currentProject?.project_id || '',
    species: S.activeSpecies,
    breed: S.activeStyle,
    emotion: S.activeEmotion || S.lastRoute?.preset_name || '',
    active_emotion: S.activeEmotion,
    active_style: S.activeStyle,
    nl: D.nlInput?.value?.trim() || '',
    action: (S.lastSplit && S.lastSplit.action) || D.nlInput?.value?.trim() || '',
    photo_name: S.photoName,
    // 不传 packet：01_滑杆包由服务端从 baked.slider_packet 或 预设资产/情绪包 解析
    baked: S.lastBaked,
    metronome: S.lastMetronome,
    beat_text: S.lastMetronome,
    prompt_04: S.lastPrompt,
    wan_positive_clip: S.lastWanPositive,
    wan_negative_clip: S.lastWanNegative,
    split: S.lastSplit,
    route: S.lastRoute,
    detection: S.detection,
    template_params: S.templateParams,
    build_bundle: extra.build_bundle !== false,
    note: extra.note || '',
  };
}

function refreshArchiveUI(){
  if(D.profilePathLine){
    D.profilePathLine.textContent = S.lastProfile?.paths?.profile_file
      ? ('客户资料：'+ S.lastProfile.paths.profile_file)
      : '完成保存后，客户资料写入 客户资产库/项目/客户资料.json';
  }
  if(D.bundleStatus){
    const ready = S.lastBundle?.ready_for_diffusion;
    D.bundleStatus.textContent = ready
      ? '✓ 扩散引擎包已就绪（含 MP4 + Prompt + Wan± + 参考图）'
      : (S.lastBundle ? '⚠ 包已创建但缺少 MP4 或 Prompt' : '保存后自动生成 输出/扩散引擎包/');
    D.bundleStatus.style.color = ready ? '#15803d' : 'var(--text-muted)';
  }
  if(D.bundleZipLink){
    if(S.bundleZipUrl){
      D.bundleZipLink.href = S.bundleZipUrl;
      D.bundleZipLink.classList.remove('hidden');
    } else {
      D.bundleZipLink.classList.add('hidden');
    }
  }
}

async function saveCustomerArchive(extra={}){
  if(!S.customerId || !S.currentProject){ alert('请先登录并打开项目'); return null; }
  const d = await apiPost('/api/portal/archive', archivePayload(extra));
  if(!d.ok) throw new Error(d.error||'保存失败');
  S.lastProfile = d.profile || null;
  S.lastBundle = d.bundle || null;
  S.bundleZipUrl = d.bundle_zip_url || '';
  refreshArchiveUI();
  return d;
}

async function fetchJSON(url, opts={}){
  const r = await fetch(url, {cache:'no-store', ...opts});
  const t = await r.text();
  if(!r.ok) throw new Error(t.slice(0,300));
  return JSON.parse(t);
}

/** 启动时对齐后台 build；版本/能力不对则自动跳转 /portal 或显示红条。 */
async function ensurePortalFresh(){
  const banner = $('server-stale-banner');
  const meta = document.querySelector('meta[name="portal-build"]');
  const pageBuild = meta?.getAttribute('content') || '';

  if(!pageBuild || pageBuild === '__PORTAL_BUILD__'){
    location.replace('/portal');
    return false;
  }

  try {
    const v = await fetchJSON('/api/portal/version');
    window.__PORTAL_SERVER__ = v;

    if(!Array.isArray(v.features) || !v.features.includes('calibrate_preview')){
      if(banner){
        banner.textContent = '⚠ 后台服务过旧（缺少标定线条预览）。请双击「一键打开创作门户.sh」重启，再打开 http://127.0.0.1:8765/portal';
        show(banner);
      }
      return false;
    }
    if(!v.features.includes('project_archive')){
      if(banner){
        banner.textContent = '⚠ 后台过旧（缺少客户资料保存）。请重启工作台后再保存/下载 zip';
        show(banner);
      }
      return false;
    }

    if(v.portal_build && v.portal_build !== pageBuild){
      const k = 'portal_sync_'+v.portal_build;
      if(!sessionStorage.getItem(k)){
        sessionStorage.setItem(k, '1');
        location.replace('/portal?b='+v.portal_build);
        return false;
      }
    }

    const label = $('portal-build-label');
    if(label && v.portal_build) label.textContent = 'build '+v.portal_build;
    if(banner) hide(banner);
    return true;
  } catch(e){
    if(banner){
      banner.textContent = '⚠ 后台未启动或无法连接。请双击「一键打开创作门户.sh」，再访问 http://127.0.0.1:8765/portal';
      show(banner);
    }
    return false;
  }
}
async function apiPost(path, body){
  const r = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const t = await r.text();
  if(!r.ok){
    if(t.trim().startsWith('<!DOCTYPE')||t.trim().startsWith('<html')){
      throw new Error('后台 API 不存在(404) — 请双击「一键打开创作门户.sh」重启服务后再试');
    }
    throw new Error(t.slice(0,300));
  }
  return JSON.parse(t);
}
function esc(s){ const d=document.createElement('div'); d.textContent=s||''; return d.innerHTML; }
function copyText(text, btn){
  if(!text){ alert('暂无可复制内容'); return; }
  navigator.clipboard.writeText(text).then(()=>{
    if(btn){ const o=btn.textContent; btn.textContent='已复制'; setTimeout(()=>{ btn.textContent=o; }, 1200); }
  }).catch(()=> alert('复制失败，请手动选择文本'));
}
function splitWanFrom04(prompt04){
  if(!prompt04) return {positive:'', negative:''};
  const negMarker='## 负向 Prompt', beatMarker='## 扩散节拍表';
  const posMarker='## 正向 Prompt', narrativeMarker='## 叙事';
  let negative='';
  if(prompt04.includes(negMarker)) negative=prompt04.split(negMarker,1)[1].trim();
  const parts=[];
  if(prompt04.includes(posMarker)){
    let after=prompt04.split(posMarker,1)[1];
    if(after.includes(beatMarker)) parts.push(after.split(beatMarker,1)[0].trim());
    else parts.push(after.split(narrativeMarker,1)[0].trim());
  }
  if(prompt04.includes(beatMarker)){
    let beat=prompt04.split(beatMarker,1)[1];
    if(beat.includes(narrativeMarker)) parts.push(beat.split(narrativeMarker,1)[0].trim());
    else if(beat.includes(negMarker)) parts.push(beat.split(negMarker,1)[0].trim());
    else parts.push(beat.trim());
  }
  if(prompt04.includes(narrativeMarker)){
    let n=prompt04.split(narrativeMarker,1)[1];
    if(n.includes(negMarker)) n=n.split(negMarker,1)[0];
    parts.push(n.trim());
  }
  return {positive:parts.filter(Boolean).join('\n\n'), negative};
}
function styleLabelForSpecies(species, styleId){
  const data=S.presets[species]||{};
  const item=(data.styles||[]).find(s=>s.id===styleId);
  return item?.label || styleId || '品种模板';
}

function getCalibBreed(){
  if(S.activeSpecies === 'human') return '';
  if(D.calibBreedSelect?.value) return D.calibBreedSelect.value;
  return S.calibBreed || S.activeStyle || defaultStyleForSpecies(
    S.activeSpecies, (S.presets[S.activeSpecies]||{}).styles
  );
}

function syncCalibBreedUI(species){
  if(!D.calibBreedWrap || !D.calibBreedSelect) return;
  if(species === 'human'){
    hide(D.calibBreedWrap);
    S.calibBreed = '';
    return;
  }
  show(D.calibBreedWrap);
  const styles = (S.presets[species]||{}).styles || [];
  const prefer = S.calibratedBreed || S.calibBreed || S.activeStyle
    || defaultStyleForSpecies(species, styles);
  D.calibBreedSelect.innerHTML = styles.map(s =>
    `<option value="${esc(s.id)}">${esc(s.label)}</option>`
  ).join('');
  if(prefer && styles.some(s => s.id === prefer)) D.calibBreedSelect.value = prefer;
  else if(styles.length) D.calibBreedSelect.value = styles[0].id;
  S.calibBreed = D.calibBreedSelect.value;
}

function breedMismatchMessage(selected, calibrated){
  if(S.activeSpecies === 'human' || !calibrated || !selected || selected === calibrated) return '';
  return '品种「'+styleLabelForSpecies(S.activeSpecies, selected)+'」与标定品种「'
    +styleLabelForSpecies(S.activeSpecies, calibrated)+'」不一致 — 请回第①步重新标定';
}

function assertBreedCalibrated(){
  if(S.activeSpecies === 'human') return true;
  if(!S.calibrated || !S.calibratedBreed){
    alert('请先完成第①步照片配准（锚点标定，非美颜滑杆）');
    return false;
  }
  const sel = S.activeStyle || getCalibBreed();
  const msg = breedMismatchMessage(sel, S.calibratedBreed);
  if(msg){ alert(msg); return false; }
  return true;
}
function updateBreedBadges(){
  const label=styleLabelForSpecies(S.activeSpecies, S.activeStyle);
  document.querySelectorAll('.breed-badge-dynamic').forEach(el=>{ el.textContent=label; });
}
function refreshWanClipUI(){
  const pos=S.lastWanPositive||'';
  const neg=S.lastWanNegative||'';
  if(D.resultWanPos) D.resultWanPos.textContent=pos||'(尚未生成)';
  if(D.resultWanNeg) D.resultWanNeg.textContent=neg||'(尚未生成)';
  if(D.wanPositivePreview) D.wanPositivePreview.textContent=pos||'(导出或生成后显示)';
  if(D.wanNegativePreview) D.wanNegativePreview.textContent=neg||'(导出或生成后显示)';
  if(D.wanClipWrap){
    if(pos||neg) show(D.wanClipWrap); else hide(D.wanClipWrap);
  }
}
function renderPomotSummary(){
  if(!D.pomotSummary) return;
  if(!S.lastPrompt && !S.lastBaked){
    hide(D.pomotSummary);
    return;
  }
  const hasRhythm=S.lastPrompt.includes('跟随控制序列');
  const breed=styleLabelForSpecies(S.activeSpecies, S.activeStyle||S.lastRoute?.breed||'');
  const emotion=S.lastRoute?.preset_name||S.activeEmotion||S.lastBaked?.mood||'-';
  const rev=S.lastBaked?.revision||'-';
  D.pomotSummary.innerHTML=
    '<div><strong>情绪</strong> '+esc(emotion)
    +' · <strong>品种/风格</strong> '+esc(breed)
    +' · <strong>revision</strong> '+esc(rev)+'</div>'
    +'<div style="margin-top:4px">L3 跟随控制序列：'
    +(hasRhythm?'<span class="ok-tag">✓ 已写入</span>':'<span class="warn-tag">⚠ 缺失</span>')
    +' · 04 长度 '+ (S.lastPrompt.length||0) +' 字</div>';
  show(D.pomotSummary);
}
function show(el){ el.classList.remove('hidden'); }
function hide(el){ el.classList.add('hidden'); }
function setStatus(el, msg, isErr){ el.textContent=msg||''; el.style.color=isErr?'#dc3545':'var(--text-muted)'; }

function hideAllScreens(){
  hide(D.welcome); hide(D.registerScreen); hide(D.loginScreen);
  D.dashboard.classList.remove('active'); D.wizard.classList.remove('active');
}
function showWelcome(){ hideAllScreens(); show(D.welcome); hide(D.loggedUser); hide(D.btnLogout); }
function showRegister(){ hideAllScreens(); show(D.registerScreen); }
function showLogin(){
  hideAllScreens(); show(D.loginScreen);
  const hint = $('login-hint');
  const last = localStorage.getItem('portal_last_cid') || '';
  if(hint){
    hint.textContent = last
      ? ('上次登录：'+last+'（也可填显示名称，如 金涛）')
      : '登录凭据是 C00x 编号；注册成功后会自动分配，不是随便起的名字';
  }
  if(last && D.loginCid && !D.loginCid.value) D.loginCid.value = last;
}
function showDashboard(){
  hideAllScreens(); D.dashboard.classList.add('active');
  show(D.loggedUser); show(D.btnLogout);
  D.loggedUser.textContent = '👤 ' + (S.customer?.display_name || S.customerId);
}
function showWizard(){
  hideAllScreens(); D.wizard.classList.add('active');
  show(D.loggedUser); show(D.btnLogout);
}

/* ── 认证 ── */
async function doRegister(){
  const name=D.regName.value.trim(), pwd=D.regPwd.value, pwd2=D.regPwd2.value;
  D.registerError.classList.remove('active');
  if(!name){ D.registerError.textContent='请输入客户名称'; D.registerError.classList.add('active'); return; }
  if(!pwd||pwd.length<4){ D.registerError.textContent='密码至少4位'; D.registerError.classList.add('active'); return; }
  if(pwd!==pwd2){ D.registerError.textContent='两次密码不一致'; D.registerError.classList.add('active'); return; }
  D.btnRegister.disabled=true;
  try {
    const d = await apiPost('/api/auth/register', {display_name:name, password:pwd});
    if(!d.ok) throw new Error(d.error||'注册失败');
    const login = await apiPost('/api/auth/login', {customer_id:d.customer_id, password:pwd});
    if(!login.ok) throw new Error(login.error||'自动登录失败');
    S.token=login.token; S.customer=login.customer; S.customerId=login.customer_id;
    localStorage.setItem('portal_token', S.token);
    localStorage.setItem('portal_last_cid', login.customer_id);
    await loadPresets();
    await startNewProject(true);
  } catch(e){
    D.registerError.textContent='❌ '+e.message; D.registerError.classList.add('active');
  } finally { D.btnRegister.disabled=false; }
}

async function doLogin(){
  const cid=D.loginCid.value.trim(), pwd=D.loginPwd.value;
  D.loginError.classList.remove('active');
  if(!cid||!pwd){ D.loginError.textContent='请输入客户ID和密码'; D.loginError.classList.add('active'); return; }
  D.btnLogin.disabled=true;
  try {
    const d = await apiPost('/api/auth/login', {customer_id:cid, password:pwd});
    if(!d.ok) throw new Error(d.error||'登录失败');
    S.token=d.token; S.customer=d.customer; S.customerId=d.customer_id;
    localStorage.setItem('portal_token', S.token);
    localStorage.setItem('portal_last_cid', d.customer_id);
    await loadPresets();
    await loadProjects();
    showDashboard();
  } catch(e){
    D.loginError.textContent='❌ '+e.message; D.loginError.classList.add('active');
  } finally { D.btnLogin.disabled=false; }
}

function doLogout(){
  S.token=''; S.customer=null; S.customerId=''; S.projects=[]; S.currentProject=null;
  localStorage.removeItem('portal_token');
  showWelcome();
}

/* ── 项目 ── */
async function loadPresets(){
  try {
    const d = await fetchJSON('/api/portal/presets');
    if(d.ok) S.presets = d.presets;
  } catch(e){ console.warn('预设加载失败', e); }
}

async function loadProjects(){
  const d = await fetchJSON('/api/customer-portal/'+S.customerId);
  if(!d.ok) throw new Error(d.error||'加载失败');
  const projects = [];
  (d.photos||[]).forEach(ph => (ph.projects||[]).forEach(p => {
    if(!projects.find(x=>x.project_id===p.project_id)) projects.push({...p, photo:ph});
  }));
  (d.unlinked_projects||[]).forEach(p => {
    if(!projects.find(x=>x.project_id===p.project_id)) projects.push(p);
  });
  S.projects = projects;
  renderProjectList();
}

function speciesTagHtml(sp){
  const label = {dog:'🐶 狗项目', cat:'🐱 猫项目', human:'🙂 人项目'}[sp] || sp;
  return '<span class="species-tag '+esc(sp)+'">'+label+'</span>';
}

function membraneTagHtml(text, kind){
  return '<span class="membrane-tag '+esc(kind||'unk')+'">'+esc(text)+'</span>';
}

function updateSpeciesBanner(ms){
  if(!D.speciesBanner) return;
  ms = ms || S.membraneStatus;
  if(!ms){
    hide(D.speciesBanner);
    return;
  }
  show(D.speciesBanner);
  D.speciesBanner.classList.remove('ok','warn','info');
  const sp = ms.project_species || S.activeSpecies;
  let tags = speciesTagHtml(sp);
  tags += ' ' + membraneTagHtml('期望：'+ (ms.expected_membrane||''), 'unk');
  tags += ' ' + membraneTagHtml('生成：'+ (ms.baked_pipeline_label||''), ms.baked_pipeline==='dog'||ms.baked_pipeline==='cat'||ms.baked_pipeline==='human' ? 'ok' : 'bad');
  if(ms.video_membrane_type || ms.video_species){
    const vk = ms.video_species === sp ? 'ok' : (ms.video_species ? 'bad' : 'unk');
    tags += ' ' + membraneTagHtml('视频：'+ (ms.video_membrane_type || '未校验'), vk);
  }
  D.speciesBannerTags.innerHTML = tags;

  if(ms.is_valid){
    D.speciesBanner.classList.add('ok');
    D.speciesBannerMsg.textContent = '✓ 底膜类型正确，可以预览和导出';
  } else if(ms.status === 'pending' || ms.baked_pipeline === 'none'){
    D.speciesBanner.classList.add('info');
    D.speciesBannerMsg.textContent = '标定完成后：① 下方点「渲染 MP4」看狗底膜；或 ② 到第③步描述表情再生成';
  } else if(ms.warning){
    D.speciesBanner.classList.add('warn');
    D.speciesBannerMsg.textContent = ms.warning + (ms.action==='regenerate' ? ' → 请到第③步点「生成表情」' : ms.action==='render' ? ' → 请到第④步点「渲染」' : '');
  } else {
    D.speciesBanner.classList.add('info');
    D.speciesBannerMsg.textContent = '请先完成③生成 → ④渲染，此处会显示底膜是否为'+ (ms.expected_membrane||'正确类型');
  }
}

function updateMembraneAlerts(ms){
  ms = ms || S.membraneStatus;
  [D.membraneAlertStep1, D.membraneAlertStep4].forEach(el => {
    if(!el) return;
    el.classList.remove('danger','success','hidden');
  });
  if(!ms || ms.is_valid){
    if(D.membraneAlertStep1) hide(D.membraneAlertStep1);
    if(D.membraneAlertStep4 && ms && ms.is_valid){
      D.membraneAlertStep4.classList.add('success');
      D.membraneAlertStep4.textContent = '✓ 当前为「'+ (ms.video_membrane_type || ms.expected_membrane) +'」';
      show(D.membraneAlertStep4);
    } else if(D.membraneAlertStep4) hide(D.membraneAlertStep4);
    return;
  }
  if(ms.status === 'pending' || ms.baked_pipeline === 'none'){
    if(D.membraneAlertStep1) hide(D.membraneAlertStep1);
    if(D.membraneAlertStep4) hide(D.membraneAlertStep4);
    return;
  }
  const msg = ms.warning || '底膜类型待确认';
  if(D.membraneAlertStep1){
    D.membraneAlertStep1.classList.add('danger');
    D.membraneAlertStep1.textContent = msg;
    show(D.membraneAlertStep1);
  }
  if(D.membraneAlertStep4){
    D.membraneAlertStep4.classList.add('danger');
    D.membraneAlertStep4.textContent = msg + (ms.action==='regenerate' ? ' — 请回第③步重新「生成表情」，再到第④步渲染。' : '');
    show(D.membraneAlertStep4);
  }
}

function renderProjectList(){
  const n = S.projects.length;
  D.projectCount.textContent = n + ' 个';
  if(!n){
    D.projectList.innerHTML = '<p style="text-align:center;padding:32px;color:var(--text-muted)">还没有项目，点击「新建项目」开始</p>';
    return;
  }
  D.projectList.innerHTML = S.projects.map((p,i) => {
    const sp = p.species || 'human';
    const icon = sp==='dog'?'🐶':sp==='cat'?'🐱':'🙂';
    const ms = p.membrane_status || {};
    let tags = '<div class="project-tags">'+speciesTagHtml(sp);
    if(ms.baked_pipeline_label){
      const mk = ms.is_valid ? 'ok' : (ms.warning ? 'bad' : 'unk');
      tags += membraneTagHtml(ms.baked_pipeline_label, mk);
    }
    if(ms.video_membrane_type){
      const vk = ms.video_species === sp ? 'ok' : 'bad';
      tags += membraneTagHtml(ms.video_membrane_type, vk);
    } else if(ms.warning){
      tags += membraneTagHtml('底膜待确认', 'bad');
    }
    tags += '</div>';
    return `<div class="project-item" data-idx="${i}">
      <div class="icon">${icon}</div>
      <div style="flex:1"><div style="font-weight:600">${esc(p.project_name)}</div>
      <div style="font-size:0.78rem;color:var(--text-muted)">${p.project_id} · ${p.outputs?.length||0} 个输出</div>
      ${tags}</div>
      <span>→</span></div>`;
  }).join('');
  D.projectList.querySelectorAll('.project-item').forEach(el => {
    el.onclick = () => openProject(+el.dataset.idx);
  });
}

async function startNewProject(autoOpen){
  const name = autoOpen ? ('创作_'+new Date().toISOString().slice(0,10)) :
    prompt('项目名称：', '创作_'+new Date().toISOString().slice(0,10));
  if(!name) return;
  // 物种在第①步向导里选择；新建项目先用 human 占位，打开后可改
  const d = await apiPost('/api/customer/'+S.customerId+'/project/create', {project_name:name, species:'human'});
  if(!d.ok) throw new Error(d.error||'创建失败');
  await loadProjects();
  const np = S.projects.find(x=>x.project_id===d.project_id);
  if(np) openProject(S.projects.indexOf(np), true);
  else if(!autoOpen) alert('项目已创建');
}

function openProject(idx, isNew){
  const p = S.projects[idx];
  if(!p) return;
  S.currentProject = p;
  S.activeSpecies = p.species || 'human';
  S.savedSteps = [];
  S.photoFile = null; S.photoName = p.reference_photo || '';
  S.calibrated = false; S.calibratedBreed = ''; S.calibBreed = '';
  S.calibAnchors = {}; S.calibStepIdx = 0; S.calibMarkEars = false;
  S.lastSplit = null; S.lastRoute = null; S.lastPacket = null; S.lastBaked = null;
  S.lastMetronome = ''; S.lastPrompt = ''; S.lastWanPositive = ''; S.lastWanNegative = ''; S.videoUrl = ''; S.membraneInfo = null;
  S.templateParams = null;
  D.wizardTitle.textContent = '🎨 ' + p.project_name;
  D.speciesSelect.value = S.activeSpecies;
  const lb = $('species-label');
  if(lb) lb.textContent = S.activeSpecies;
  renderPresets(S.activeSpecies);
  syncCalibBreedUI(S.activeSpecies);
  resetPhotoUI();
  if(S.photoName){
    S.photoUrl = '/api/customer/photo-preview/'+S.customerId+'/'+encodeURIComponent(S.photoName);
    show(D.calibrateWrap);
    D.calibrateImg.onload = () => {
      if(!S.imageWidth) S.imageWidth = D.calibrateImg.naturalWidth;
      if(!S.imageHeight) S.imageHeight = D.calibrateImg.naturalHeight;
      resizeCalibCanvas(); drawCalibOverlay();
    };
    D.calibrateImg.onerror = () => {
      show(D.calibrateLoadErr);
      D.calibrateLoadErr.textContent = '⚠ 照片加载失败，请重新上传';
    };
    D.calibrateImg.src = S.photoUrl + '?t=' + Date.now();
  }
  goStep(isNew ? 1 : 1);
  showWizard();
  loadProjectState(p.project_id);
}

function membranePreviewApiUrl(projectId){
  return '/api/portal/membrane-preview?customer_id='+encodeURIComponent(S.customerId)
    +'&project_id='+encodeURIComponent(projectId||S.currentProject?.project_id||'');
}

function membranePreviewSrc(url){
  if(!url) return '';
  if(url.startsWith('data:')) return url;
  const sep = url.includes('?') ? '&' : '?';
  return url + sep + 't=' + Date.now();
}

function renderMembraneDiff(diff){
  if(!D.membraneDiffBody) return;
  const rows = Array.isArray(diff) ? diff : [];
  if(!rows.length){
    D.membraneDiffBody.innerHTML = '';
    if(D.membraneDiffEmpty) show(D.membraneDiffEmpty);
    return;
  }
  if(D.membraneDiffEmpty) hide(D.membraneDiffEmpty);
  D.membraneDiffBody.innerHTML = rows.map(r =>
    `<tr><td>${esc(r.label||r.key)}</td><td>${r.before}</td><td>${r.after}</td><td>${esc(r.hint||'')} (${r.delta>0?'+':''}${r.delta})</td></tr>`
  ).join('');
}

function showMembraneCompare(data){
  if(!D.membranePreviewWrap) return;
  const note = data.membrane_note || '左=品种默认 · 右=标定后 · 狗底膜（绿线含垂耳，人类底膜无垂耳）';
  if(D.membranePreviewNote) D.membranePreviewNote.textContent = note;
  if(D.membraneBreedRef){
    const ref = data.breed_reference || '';
    D.membraneBreedRef.textContent = ref ? ('参考：'+ref) : '';
  }

  const setImg = (el, b64, url) => {
    if(!el) return;
    if(b64) el.src = 'data:image/png;base64,'+b64;
    else if(url) el.src = membranePreviewSrc(url);
    else if(S.currentProject){
      const v = el === D.membranePreviewBreed ? 'breed' : 'calibrated';
      el.src = membranePreviewSrc(membranePreviewApiUrl(S.currentProject.project_id)+'&variant='+v);
    }
  };

  setImg(D.membranePreviewBreed, data.preview_breed_base64, data.breed_preview_url);
  setImg(D.membranePreviewCustom, data.preview_calibrated_base64 || data.preview_base64, data.calibrated_preview_url || data.preview_url);
  renderMembraneDiff(data.adjustment_diff);
  show(D.membranePreviewWrap);
  D.membranePreviewWrap.scrollIntoView({behavior:'smooth', block:'nearest'});
}

function showMembranePreview(url, note){
  showMembraneCompare({ preview_url: url, preview_base64: url?.startsWith('data:') ? url.split(',')[1] : '', membrane_note: note });
}

function applyCalibratePreview(d){
  if(S.activeSpecies !== 'dog') return false;
  if(d.preview_breed_base64 || d.preview_calibrated_base64 || d.breed_preview_url || d.preview_url){
    showMembraneCompare(d);
    return true;
  }
  if(S.currentProject){
    showMembraneCompare({
      breed_preview_url: membranePreviewApiUrl(S.currentProject.project_id)+'&variant=breed',
      calibrated_preview_url: membranePreviewApiUrl(S.currentProject.project_id)+'&variant=calibrated',
      adjustment_diff: d.adjustment_diff || [],
      membrane_note: d.membrane_note,
    });
    return true;
  }
  if(d.preview_error){
    setStatus(D.status1, '⚠ 标定已保存，但线条图生成失败：'+d.preview_error, true);
  }
  return false;
}

function hideMembranePreview(){
  S.membranePreviewUrl = '';
  if(D.membranePreviewWrap) hide(D.membranePreviewWrap);
}

function restoreCalibration(calib){
  if(!calib || !calib.anchors) return false;
  if(S.photoName && calib.photo_name && calib.photo_name !== S.photoName) return false;
  S.calibAnchors = {...calib.anchors};
  S.calibMarkEars = !!calib.ears_marked;
  if(Array.isArray(calib.image_size) && calib.image_size.length >= 2){
    S.imageWidth = calib.image_size[0];
    S.imageHeight = calib.image_size[1];
  }
  let idx = 0;
  ['left_eye','right_eye','nose'].forEach(k => { if(S.calibAnchors[k]) idx++; });
  if(S.calibMarkEars){
    if(S.calibAnchors.left_ear) idx++;
    if(S.calibAnchors.right_ear) idx++;
  } else if(idx >= 3) {
    idx = 3;
  }
  S.calibStepIdx = idx;
  S.calibrated = true;
  S.calibratedBreed = calib.breed || '';
  if(calib.breed) S.activeStyle = calib.breed;
  S.detection = {
    method: calib.method || 'manual',
    confidence: calib.confidence ?? 1,
    adjustments: calib.adjustments,
  };
  drawCalibOverlay();
  updateCalibHint();
  D.btnStep1Next.disabled = false;
  if(S.activeSpecies === 'dog'){
    showMembraneCompare({
      preview_breed_base64: calib.preview_breed_base64,
      preview_calibrated_base64: calib.preview_calibrated_base64 || calib.preview_base64,
      breed_preview_url: calib.breed_preview_url,
      calibrated_preview_url: calib.calibrated_preview_url || calib.preview_url,
      adjustment_diff: calib.adjustment_diff,
      membrane_note: calib.membrane_note || '左=品种默认 · 右=标定后',
    });
  }
  const breedLabel = calib.breed_label || (calib.breed === 'poodle_giant' ? '巨型贵宾犬' : '');
  setStatus(D.status1, '✅ 已恢复上次标定' + (breedLabel ? '（'+breedLabel+'）' : '') + ' — 无需重标');
  addSavedStep('① 标定已恢复');
  return true;
}

function formatFileSize(n){
  if(!n) return '';
  if(n < 1024) return n + ' B';
  if(n < 1048576) return (n/1024).toFixed(1) + ' KB';
  return (n/1048576).toFixed(1) + ' MB';
}

function mp4MatchesBaked(del, baked){
  if(!del?.video_exists || !baked) return false;
  const meta = del.membrane_meta || {};
  const rev = baked.revision || baked.gaze_emotion_id || baked.mood || '';
  return !rev || !meta.baked_revision || meta.baked_revision === rev;
}

function refreshDeliverablesPanel(del){
  del = del || {};
  const meta = del.membrane_meta || S.membraneInfo || {};
  const sp = meta.species || S.activeSpecies;
  const spLabel = {dog:'🐶 狗', cat:'🐱 猫', human:'🙂 人'}[sp] || sp;

  if(del.video_exists && del.video_url){
    D.delivVideoStatus.textContent = '✓ 已就绪 · ' + formatFileSize(del.video_size);
    D.delivVideoStatus.style.color = '#15803d';
    D.delivVideoLink.href = del.video_url + '?t=' + Date.now();
    D.delivVideoLink.classList.remove('hidden');
  } else if(del.video_exists){
    D.delivVideoStatus.textContent = '✓ 已就绪（链接刷新中…）';
    D.delivVideoStatus.style.color = '#15803d';
    D.delivVideoLink.classList.add('hidden');
  } else {
    D.delivVideoStatus.textContent = '✗ 未生成（请第④步渲染）';
    D.delivVideoStatus.style.color = '#dc2626';
    D.delivVideoLink.classList.add('hidden');
  }

  if(del.prompt_exists && del.prompt_url){
    D.delivPromptStatus.textContent = '✓ 已就绪 · ' + formatFileSize(del.prompt_size);
    D.delivPromptStatus.style.color = '#15803d';
    D.delivPromptLink.href = del.prompt_url + '?t=' + Date.now();
    D.delivPromptLink.classList.remove('hidden');
  } else if(del.prompt_exists){
    D.delivPromptStatus.textContent = '✓ 已就绪（链接刷新中…）';
    D.delivPromptStatus.style.color = '#15803d';
    D.delivPromptLink.classList.add('hidden');
  } else {
    D.delivPromptStatus.textContent = '✗ 未生成（点下方「更新 04_Prompt」）';
    D.delivPromptStatus.style.color = '#dc2626';
    D.delivPromptLink.classList.add('hidden');
  }

  if(D.delivVideoMembrane){
    const ms = S.membraneStatus;
    const meta = del.membrane_meta || S.membraneInfo || {};
    const vType = meta.membrane_type || ms?.video_membrane_type || '';
    const expect = ms?.expected_membrane || '';
    if(vType){
      const ok = ms && ms.video_species === ms.project_species;
      D.delivVideoMembrane.innerHTML = membraneTagHtml(vType, ok ? 'ok' : 'bad');
    } else if(del.video_exists){
      D.delivVideoMembrane.innerHTML = membraneTagHtml('⚠ 未校验（可能人底膜）', 'bad');
    } else {
      D.delivVideoMembrane.textContent = expect ? ('应为 '+expect) : '—';
    }
  }

  if(meta.membrane_type){
    D.membraneVerifyLine.textContent =
      '底膜类型：' + meta.membrane_type + '（' + (meta.renderer||'') + '，' + spLabel + '）';
  } else if(del.video_exists) {
    D.membraneVerifyLine.textContent = '底膜视频已存在，物种：' + spLabel + '（建议重新渲染以写入校验信息）';
  } else {
    D.membraneVerifyLine.textContent = '完成④渲染后，此处会显示是否为狗/猫/人底膜。';
  }
}

function updateMembraneBadge(info){
  if(!info || !info.membrane_type){ hide(D.membraneBadge); return; }
  const sp = {dog:'🐶', cat:'🐱', human:'🙂'}[info.species] || '';
  D.membraneBadge.textContent = sp + ' 当前预览：' + info.membrane_type + ' · ' + (info.renderer||'');
  show(D.membraneBadge);
}

async function loadProjectState(projectId){
  if(!S.customerId || !projectId) return;
  try {
    const d = await fetchJSON('/api/portal/project/state?customer_id='+encodeURIComponent(S.customerId)+'&project_id='+encodeURIComponent(projectId));
    if(!d.ok) return;

    if(d.template_params) S.templateParams = d.template_params;

    if(d.calibration) restoreCalibration(d.calibration);

    S.membraneStatus = d.membrane_status || null;
    updateSpeciesBanner(S.membraneStatus);
    updateMembraneAlerts(S.membraneStatus);

    const ms = S.membraneStatus;
    const badBaked = ms && (ms.action === 'regenerate' || ms.baked_pipeline === 'human_legacy');

    if(badBaked){
      setStatus(D.status3, ms.warning || '⚠ 请第③步重新「生成表情」以使用狗/猫底膜', true);
      S.lastBaked = null;
      S.lastPacket = d.pipeline?.packet || null;
    } else if(d.species_mismatch){
      setStatus(D.status3, '⚠ 已保存的烘焙是「'+d.baked_species+'」，与项目「'+d.species+'」不一致，请重新生成', true);
      S.lastBaked = null;
      S.lastPacket = null;
    } else if(d.pipeline){
      if(d.pipeline.packet){
        S.lastPacket = d.pipeline.packet;
        if(S.lastPacket.emotion) S.activeEmotion = S.lastPacket.emotion;
      }
      if(d.pipeline.baked){
        S.lastBaked = d.pipeline.baked;
        if(S.lastBaked.mood || S.lastBaked.gaze_emotion_id) D.btnStep3Next.disabled = false;
      }
    }
    if(d.slider_current?.packet){
      S.lastPacket = d.slider_current.packet;
      if(S.lastPacket.emotion) S.activeEmotion = S.lastPacket.emotion;
    }

    if(d.deliverables){
      if(d.deliverables.video_exists && !badBaked && mp4MatchesBaked(d.deliverables, S.lastBaked)){
        S.videoUrl = d.deliverables.video_url;
        D.previewVideo.src = S.videoUrl + '?t=' + Date.now();
        show(D.videoWrap);
        D.btnStep4Next.disabled = false;
      } else if(d.deliverables.video_exists && S.lastBaked && !mp4MatchesBaked(d.deliverables, S.lastBaked)){
        hide(D.videoWrap);
        S.videoUrl = '';
        D.btnStep4Next.disabled = true;
        setStatus(D.status4, '⚠ MP4 与当前生成数据不同步 — 请第④步重新点「渲染 OpenCV 视频」', true);
      }
      S.membraneInfo = d.deliverables.membrane_meta;
      updateMembraneBadge(S.membraneInfo);
      refreshDeliverablesPanel(d.deliverables);
    }

    if(d.deliverables?.prompt_exists && !S.lastPrompt){
      try {
        const pr = await fetch(d.deliverables.prompt_url + '?t=' + Date.now());
        if(pr.ok) S.lastPrompt = await pr.text();
      } catch(e){ /* ignore */ }
    }
    S.lastProfile = d.profile || null;
    S.lastBundle = d.bundle || null;
    if(d.bundle_dir && S.customerId && S.currentProject){
      S.bundleZipUrl = '/api/portal/download-bundle?customer_id='
        +encodeURIComponent(S.customerId)+'&project_id='
        +encodeURIComponent(S.currentProject.project_id);
    }
    refreshArchiveUI();
    if(S.lastPrompt && (!S.lastWanPositive || !S.lastWanNegative)){
      const wan=splitWanFrom04(S.lastPrompt);
      S.lastWanPositive=wan.positive; S.lastWanNegative=wan.negative;
    }
    syncEnergyPulseFromState();
    if(S.activeEmotion && D.presetContainer){
      D.presetContainer.querySelectorAll('.preset-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.id === S.activeEmotion);
      });
    }
  } catch(e){
    console.warn('项目状态恢复失败', e);
  }
}

/* ── 步骤导航 ── */
function goStep(n){
  S.currentStep = n;
  for(let i=1;i<=5;i++){
    const panel = $('panel-'+i);
    if(panel) panel.classList.toggle('hidden', i!==n);
    const stepEl = D.stepBar.querySelector('[data-step="'+i+'"]');
    if(stepEl){
      stepEl.classList.toggle('active', i===n);
      stepEl.classList.toggle('done', i<n);
    }
  }
  if(n===2) syncEnergyPulseFromState();
  updateSpeciesBanner(S.membraneStatus);
  updateMembraneAlerts(S.membraneStatus);
  if(n===5 && S.currentProject) loadProjectState(S.currentProject.project_id);
  refreshArchiveUI();
}

const STYLE_KIND = {
  human: { emotion: '人类情绪预设', style: '人格风格' },
  cat: { emotion: '猫情绪预设', style: '猫品种' },
  dog: { emotion: '狗情绪预设', style: '狗品种' },
};

function resolveGroupEmotionId(group, idx, emotionMap){
  const keys = group.keys || [];
  const labels = group.keys_label || [];
  const candidates = [keys[idx], labels[idx]].filter(Boolean);
  for(const c of candidates){
    if(emotionMap[c]) return c;
  }
  return '';
}

function defaultStyleForSpecies(species, styles){
  const ids = (styles || []).map(s => s.id);
  const fromCustomer = (S.customer?.breed || '').trim();
  if(fromCustomer && ids.includes(fromCustomer)) return fromCustomer;
  if(S.activeStyle && ids.includes(S.activeStyle)) return S.activeStyle;
  if(styles && styles.length === 1) return styles[0].id;
  return '';
}

function emotionButtonsHtml(emotions, groups, activeId){
  const emotionMap = Object.fromEntries((emotions || []).map(e => [e.id, e]));
  const used = new Set();
  let html = '';

  const btn = (e, cls) =>
    `<button type="button" class="preset-btn ${cls}${e.id === activeId ? ' active' : ''}" data-id="${esc(e.id)}" title="${esc(e.file || e.id)}">${esc(e.label)}</button>`;

  if(groups && groups.length){
    groups.forEach(g => {
      const row = [];
      (g.keys || []).forEach((_, idx) => {
        const id = resolveGroupEmotionId(g, idx, emotionMap);
        if(!id || used.has(id)) return;
        used.add(id);
        row.push(emotionMap[id]);
      });
      if(!row.length) return;
      html += `<div class="preset-group-label">${esc(g.label)}</div>`;
      html += row.map(e => btn(e, '')).join('');
    });
  }

  const rest = (emotions || []).filter(e => !used.has(e.id));
  if(rest.length){
    if(groups && groups.length) html += `<div class="preset-group-label">其他</div>`;
    html += rest.map(e => btn(e, '')).join('');
  }
  return html || '<span class="preset-empty">无预设（请检查 预设资产/情绪包/）</span>';
}

function styleButtonsHtml(styles, activeId){
  if(!styles || !styles.length){
    return '<span class="preset-empty">无品种/风格（请检查 预设资产/风格包/）</span>';
  }
  return styles.map(s =>
    `<button type="button" class="preset-btn style-btn${s.id === activeId ? ' active' : ''}" data-id="${esc(s.id)}" title="${esc(s.file || s.notes || s.id)}">${esc(s.label)}</button>`
  ).join('');
}

function bindPresetButtons(container, onPick){
  if(!container) return;
  container.querySelectorAll('.preset-btn').forEach(btn => {
    btn.onclick = () => {
      container.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      onPick(btn.dataset.id, btn.textContent);
    };
  });
}

const NEUTRAL_MACRO = {push:50, power:50, speed:50, steady:50, grip:50, outro:50};
const NEUTRAL_HOLD = {shape:'flat', pulse_rate:0, pulse_depth:0, swell:0};

/** macro+hold_seg → E(t) SVG；数值每次从 /api/portal/preset/emotion-preview 调取 */
function paintEnergyPulse(macro, hold, emotionLabel){
  const svg = D.energyPulseCurve;
  if(!svg) return;
  const m = {...NEUTRAL_MACRO, ...(macro || {})};
  const h = {...NEUTRAL_HOLD, ...(hold || {})};
  const W = 300, H = 100;
  let html = '<rect width="300" height="100" fill="#fafbfd"/>'
    +'<rect x="0" y="0" width="60" height="100" fill="#dbeafe" opacity="0.4"/>'
    +'<rect x="60" y="0" width="180" height="100" fill="#fef3c7" opacity="0.4"/>'
    +'<rect x="240" y="0" width="60" height="100" fill="#e0e7ff" opacity="0.4"/>';
  const push = m.push/100, power = m.power/100, speed = m.speed/100;
  const steady = m.steady/100, grip = m.grip/100, outro = m.outro/100;
  const tPeak = 14 + (1-speed)*10, peakY = H - (15+power*65);
  const tHold = 30 + steady*60, holdY = peakY + (1-grip)*10;
  let d = 'M0,'+H;
  for(let t=0; t<=tPeak; t++){
    const u = t/tPeak;
    d += ' L'+(t/150*W)+','+Math.round(H-u*(H-peakY)*(push>0.5?1+(push-0.5)*0.4:1));
  }
  for(let t=tPeak+1; t<=tHold; t++){
    const u = (t-tPeak)/(tHold-tPeak);
    let y = peakY + (holdY-peakY)*u;
    if(h.shape==='tremble') y += Math.sin(u*20)*4;
    if(h.shape==='pulse') y += Math.sin(u*h.pulse_rate*0.3)*h.pulse_depth*0.3;
    if(h.shape==='decay') y += u*20;
    if(h.shape==='swell') y -= Math.sin(Math.PI*u)*h.swell*0.3;
    d += ' L'+(t/150*W)+','+Math.round(Math.max(peakY-10, Math.min(H, y)));
  }
  for(let t=tHold+1; t<=150; t++){
    const u = (t-tHold)/(150-tHold);
    d += ' L'+(t/150*W)+','+Math.round(holdY+(H-holdY)*(u<0.5?2*u*u:-1+(4-2*u)*u));
  }
  const stroke = m.push>50 ? '#3b82f6' : '#d97706';
  html += '<path d="'+d+'" fill="none" stroke="'+stroke+'" stroke-width="2.5" stroke-linejoin="round"/>';
  html += '<line x1="'+(tPeak/150*W)+'" y1="0" x2="'+(tPeak/150*W)+'" y2="100" stroke="#3b82f6" stroke-width="0.5" stroke-dasharray="3,4" opacity="0.5"/>';
  html += '<line x1="'+(tHold/150*W)+'" y1="0" x2="'+(tHold/150*W)+'" y2="100" stroke="#d97706" stroke-width="0.5" stroke-dasharray="3,4" opacity="0.5"/>';
  svg.innerHTML = html;
  if(D.energyPulseInfo){
    D.energyPulseInfo.textContent = '起峰 '+Math.round(tPeak)+'f · 盯住 '+Math.round(tPeak)+'→'+Math.round(tHold)+'f · 收场 '+Math.round(tHold)+'→150f · 力度 '+m.power;
  }
  if(D.energyPulseMacro){
    D.energyPulseMacro.textContent = 'macro push='+m.push+' power='+m.power+' speed='+m.speed
      +' steady='+m.steady+' grip='+m.grip+' outro='+m.outro
      +' · hold '+h.shape+' rate='+h.pulse_rate+' depth='+h.pulse_depth;
  }
  if(D.energyPulseEmotion) D.energyPulseEmotion.textContent = emotionLabel ? ('· '+emotionLabel) : '';
  if(D.energyPulseWrap) show(D.energyPulseWrap);
}

function presetEmotionById(emotionId){
  return (S.presets[S.activeSpecies]?.emotions || []).find(e => e.id === emotionId) || null;
}

async function fetchEmotionPreview(emotionId){
  if(!emotionId || !S.activeSpecies) return null;
  try {
    const q = 'species='+encodeURIComponent(S.activeSpecies)+'&id='+encodeURIComponent(emotionId);
    const d = await fetchJSON('/api/portal/preset/emotion-preview?'+q);
    return d.ok ? d : null;
  } catch(e){
    console.warn('情绪预览调取失败', e);
    return null;
  }
}

async function paintEnergyPulseFromPreset(emotionId){
  const idx = presetEmotionById(emotionId);
  const label = idx?.label || emotionId;
  const prev = await fetchEmotionPreview(emotionId);
  if(prev?.macro){
    paintEnergyPulse(prev.macro, prev.hold_seg, prev.label || label);
  } else if(D.energyPulseWrap){
    hide(D.energyPulseWrap);
  }
}

function paintEnergyPulseFromPacket(pkt){
  if(pkt?.macro) paintEnergyPulse(pkt.macro, pkt.hold_seg, pkt.emotion || S.activeEmotion || '');
  else paintEnergyPulseFromPreset(S.activeEmotion);
}

function syncEnergyPulseFromState(){
  if(S.lastPacket?.macro) paintEnergyPulseFromPacket(S.lastPacket);
  else if(S.activeEmotion) paintEnergyPulseFromPreset(S.activeEmotion);
  else if(D.energyPulseWrap) hide(D.energyPulseWrap);
}

function renderPresets(species){
  const data = S.presets[species] || {emotions:[], styles:[], emotion_groups:[], meta:{}};
  const meta = data.meta || {};
  const kind = STYLE_KIND[species] || {emotion:'情绪预设', style:'风格'};
  const nEmo = meta.emotion_count ?? (data.emotions || []).length;
  const nStyle = meta.style_count ?? (data.styles || []).length;

  if(D.presetEmotionTitle) D.presetEmotionTitle.textContent = kind.emotion;
  if(D.presetEmotionCount) D.presetEmotionCount.textContent = String(nEmo);
  if(D.presetEmotionHint){
    D.presetEmotionHint.textContent = (meta.emotions_dir || `预设资产/情绪包/${species}/`)
      + ' · 门户只存选项，macro/pad 由服务端按需调取'
      + (data.emotion_groups?.length ? ' · 分组见 _groups.json' : '');
  }
  if(D.presetStyleTitle) D.presetStyleTitle.textContent = kind.style;
  if(D.presetStyleCount) D.presetStyleCount.textContent = String(nStyle);
  if(D.presetStyleHint){
    D.presetStyleHint.textContent = meta.styles_dir || `预设资产/风格包/${species}/`;
  }

  S.activeStyle = defaultStyleForSpecies(species, data.styles);
  if(S.calibratedBreed && (data.styles||[]).some(s => s.id === S.calibratedBreed)){
    S.activeStyle = S.calibratedBreed;
  }
  syncCalibBreedUI(species);
  D.presetContainer.innerHTML = emotionButtonsHtml(data.emotions, data.emotion_groups, S.activeEmotion);
  D.styleContainer.innerHTML = styleButtonsHtml(data.styles, S.activeStyle);

  bindPresetButtons(D.presetContainer, (id, label) => {
    S.activeEmotion = id;
    if(!D.nlInput.value.trim()) D.nlInput.value = label;
    paintEnergyPulseFromPreset(id);
  });
  syncEnergyPulseFromState();
  bindPresetButtons(D.styleContainer, (id) => {
    S.activeStyle = id;
    updateBreedBadges();
    const msg = breedMismatchMessage(id, S.calibratedBreed);
    if(msg && D.status2) setStatus(D.status2, msg, true);
  });
  S.activeSpecies = species;
  updateBreedBadges();
}

/* ── Step 1: 上传 + 手动标定 ── */

const CALIB_REQUIRED = {
  human: [
    {key:'left_eye', label:'① 左眼中心', color:'#ef4444'},
    {key:'right_eye', label:'② 右眼中心', color:'#ef4444'},
    {key:'nose', label:'③ 鼻尖', color:'#3b82f6'},
  ],
  dog: [
    {key:'left_eye', label:'① 左眼中心', color:'#ef4444'},
    {key:'right_eye', label:'② 右眼中心', color:'#ef4444'},
    {key:'nose', label:'③ 鼻尖', color:'#3b82f6'},
  ],
  cat: [
    {key:'left_eye', label:'① 左眼中心', color:'#ef4444'},
    {key:'right_eye', label:'② 右眼中心', color:'#ef4444'},
    {key:'nose', label:'③ 鼻尖', color:'#3b82f6'},
  ],
};
const CALIB_EARS = {
  dog: [
    {key:'left_ear', label:'④ 左耳尖（可选）', color:'#10b981'},
    {key:'right_ear', label:'⑤ 右耳尖（可选）', color:'#10b981'},
  ],
  cat: [
    {key:'left_ear', label:'④ 左耳尖（可选）', color:'#10b981'},
    {key:'right_ear', label:'⑤ 右耳尖（可选）', color:'#10b981'},
  ],
};

function calibSteps(){
  const steps = [...(CALIB_REQUIRED[S.activeSpecies] || CALIB_REQUIRED.human)];
  if(S.calibMarkEars && CALIB_EARS[S.activeSpecies]) steps.push(...CALIB_EARS[S.activeSpecies]);
  return steps;
}

function updateEarPanel(){
  hide(D.earAdjustPanel);
  if(S.calibStepIdx >= 3 && (S.activeSpecies==='dog'||S.activeSpecies==='cat') && !S.calibMarkEars){
    show(D.earAdjustPanel);
  }
}

function resetPhotoUI(){
  hide(D.calibrateWrap);
  hideMembranePreview();
  D.btnUpload.disabled = !S.photoFile;
  D.btnStep1Next.disabled = !S.calibrated;
  S.calibrated = false;
  S.calibAnchors = {};
  S.calibStepIdx = 0;
}

D.uploadZone.onclick = e => { if(e.target===D.uploadZone || e.target.tagName==='DIV') D.photoInput.click(); };
D.uploadZone.ondragover = e => { e.preventDefault(); D.uploadZone.classList.add('dragover'); };
D.uploadZone.ondragleave = () => D.uploadZone.classList.remove('dragover');
D.uploadZone.ondrop = e => { e.preventDefault(); D.uploadZone.classList.remove('dragover'); if(e.dataTransfer.files[0]) pickPhoto(e.dataTransfer.files[0]); };
D.photoInput.onchange = () => { if(D.photoInput.files[0]) pickPhoto(D.photoInput.files[0]); };

function revokePhotoBlob(){
  if(S.photoBlobUrl){ URL.revokeObjectURL(S.photoBlobUrl); S.photoBlobUrl = ''; }
}

function pickPhoto(file){
  revokePhotoBlob();
  S.photoFile = file;
  S.calibrated = false;
  S.photoName = '';
  S.photoBlobUrl = URL.createObjectURL(file);
  D.btnUpload.disabled = false;
  D.btnStep1Next.disabled = true;
  setStatus(D.status1, '照片已选，请点击「上传照片」');
}

async function uploadPhotoOnly(){
  if(!S.photoFile || !S.currentProject) return;
  D.btnUpload.disabled = true;
  setStatus(D.status1, '⏳ 上传中…');
  try {
    const b64 = await fileToBase64(S.photoFile);
    const d = await apiPost('/api/portal/project/upload-photo', {
      customer_id: S.customerId,
      project_id: S.currentProject.project_id,
      photo_data: b64,
      photo_name: S.photoFile.name,
      species: S.activeSpecies,
      skip_detect: true,
    });
    if(!d.ok) throw new Error(d.error||'上传失败');
    S.photoName = d.photo_name;
    S.photoUrl = d.photo_url;
    S.imageWidth = d.image_width || 0;
    S.imageHeight = d.image_height || 0;
    startCalibrationUI();
    const where = d.saved_paths?.customer_ref || '客户资产库/参考素材/';
    setStatus(D.status1, '✅ 已保存：'+where+' — 请在图上标定点');
  } catch(e){
    setStatus(D.status1, '❌ '+e.message, true);
  } finally { D.btnUpload.disabled = false; }
}

function startCalibrationUI(){
  show(D.calibrateWrap);
  hide(D.calibrateLoadErr);
  hide(D.earAdjustPanel);
  S.calibAnchors = {};
  S.calibStepIdx = 0;
  S.calibMarkEars = false;
  D.btnCalibrateSubmit.disabled = true;
  D.calibrateImg.onload = () => {
    if(!S.imageWidth) S.imageWidth = D.calibrateImg.naturalWidth;
    if(!S.imageHeight) S.imageHeight = D.calibrateImg.naturalHeight;
    resizeCalibCanvas();
    drawCalibOverlay();
    hide(D.calibrateLoadErr);
  };
  D.calibrateImg.onerror = () => {
    if(S.photoBlobUrl){
      D.calibrateImg.src = S.photoBlobUrl;
      return;
    }
    show(D.calibrateLoadErr);
    D.calibrateLoadErr.textContent = '⚠ 照片加载失败，请重新上传';
  };
  // 优先本地预览（即时显示），服务器 URL 作备份
  if(S.photoBlobUrl){
    D.calibrateImg.src = S.photoBlobUrl;
  } else if(S.photoUrl){
    D.calibrateImg.src = S.photoUrl + '?t=' + Date.now();
  }
  updateCalibHint();
}

function resizeCalibCanvas(){
  const img = D.calibrateImg;
  const cvs = D.calibrateCanvas;
  cvs.width = img.clientWidth;
  cvs.height = img.clientHeight;
}

function imgToDisplay(pt){
  const img = D.calibrateImg;
  const sx = img.clientWidth / img.naturalWidth;
  const sy = img.clientHeight / img.naturalHeight;
  return [pt[0]*sx, pt[1]*sy];
}

function displayToImg(x, y){
  const img = D.calibrateImg;
  const rect = img.getBoundingClientRect();
  const sx = img.naturalWidth / rect.width;
  const sy = img.naturalHeight / rect.height;
  return [(x - rect.left)*sx, (y - rect.top)*sy];
}

function drawCalibOverlay(){
  resizeCalibCanvas();
  const ctx = D.calibrateCanvas.getContext('2d');
  ctx.clearRect(0,0,D.calibrateCanvas.width, D.calibrateCanvas.height);
  const steps = calibSteps();
  const keys = Object.keys(S.calibAnchors);
  // 连线
  const le = S.calibAnchors.left_eye, re = S.calibAnchors.right_eye, nose = S.calibAnchors.nose;
  if(le && re){
    const a = imgToDisplay(le), b = imgToDisplay(re);
    ctx.strokeStyle = 'rgba(239,68,68,0.8)'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(a[0],a[1]); ctx.lineTo(b[0],b[1]); ctx.stroke();
  }
  if(le && re && nose){
    const m = imgToDisplay([(le[0]+re[0])/2, (le[1]+re[1])/2]);
    const n = imgToDisplay(nose);
    ctx.strokeStyle = 'rgba(59,130,246,0.8)';
    ctx.beginPath(); ctx.moveTo(m[0],m[1]); ctx.lineTo(n[0],n[1]); ctx.stroke();
  }
  ['left_ear','right_ear'].forEach(k => {
    if(S.calibAnchors[k] && le && re){
      const m = imgToDisplay([(le[0]+re[0])/2, (le[1]+re[1])/2]);
      const e = imgToDisplay(S.calibAnchors[k]);
      ctx.strokeStyle = 'rgba(16,185,129,0.8)';
      ctx.beginPath(); ctx.moveTo(m[0],m[1]); ctx.lineTo(e[0],e[1]); ctx.stroke();
    }
  });
  // 点
  steps.forEach(st => {
    const p = S.calibAnchors[st.key];
    if(!p) return;
    const d = imgToDisplay(p);
    ctx.fillStyle = st.color;
    ctx.beginPath(); ctx.arc(d[0], d[1], 6, 0, Math.PI*2); ctx.fill();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
  });
}

function updateCalibHint(){
  const steps = calibSteps();
  updateEarPanel();
  if(S.calibStepIdx >= steps.length){
    D.calibrateHint.textContent = '✓ 点已标完，请确认标定';
    D.btnCalibrateSubmit.disabled = false;
    return;
  }
  if(S.calibStepIdx >= 3 && !S.calibMarkEars && (S.activeSpecies==='dog'||S.activeSpecies==='cat')){
    D.calibrateHint.textContent = '眼/鼻已标完 — 可直接确认标定，或可选标耳尖';
    D.btnCalibrateSubmit.disabled = false;
    return;
  }
  D.calibrateHint.textContent = '请点击：' + steps[S.calibStepIdx].label;
  D.btnCalibrateSubmit.disabled = true;
}

D.calibrateStage.onclick = function(e){
  if(!D.calibrateImg.src) return;
  const steps = calibSteps();
  if(S.calibStepIdx >= steps.length) return;
  const st = steps[S.calibStepIdx];
  const pt = displayToImg(e.clientX, e.clientY);
  S.calibAnchors[st.key] = pt;
  S.calibStepIdx++;
  drawCalibOverlay();
  updateCalibHint();
};

D.btnMarkEars.onclick = function(){
  S.calibMarkEars = true;
  hide(D.earAdjustPanel);
  updateCalibHint();
};

D.btnCalibrateUndo.onclick = function(){
  const steps = calibSteps();
  if(S.calibStepIdx <= 0) return;
  S.calibStepIdx--;
  delete S.calibAnchors[steps[S.calibStepIdx].key];
  drawCalibOverlay();
  updateCalibHint();
};

D.btnCalibrateReset.onclick = function(){
  S.calibAnchors = {}; S.calibStepIdx = 0; S.calibMarkEars = false;
  delete S.calibAnchors.left_ear; delete S.calibAnchors.right_ear;
  drawCalibOverlay();
  updateCalibHint();
  D.btnStep1Next.disabled = true;
  S.calibrated = false;
};

async function submitCalibration(){
  if(!S.calibAnchors.left_eye || !S.calibAnchors.right_eye || !S.calibAnchors.nose){
    alert('请先标完左眼、右眼、鼻尖'); return;
  }
  D.btnCalibrateSubmit.disabled = true;
  setStatus(D.status1, '⏳ 保存标定…');
  const payload = {
    customer_id: S.customerId,
    project_id: S.currentProject.project_id,
    species: S.activeSpecies,
    breed: getCalibBreed(),
    photo_name: S.photoName,
    image_width: S.imageWidth,
    image_height: S.imageHeight,
    anchors: S.calibAnchors,
  };
  try {
    const d = await apiPost('/api/portal/calibrate-template', payload);
    if(!d.ok) throw new Error(d.error||'标定失败');
    S.templateParams = d.saved_params;
    S.detection = {method:'manual', confidence:1.0, adjustments:d.adjustments, breed:d.breed};
    S.calibrated = true;
    S.calibratedBreed = d.breed || getCalibBreed();
    S.activeStyle = S.calibratedBreed;
    S.calibBreed = S.calibratedBreed;
    const gotPreview = applyCalibratePreview(d);
    D.btnStep1Next.disabled = false;
    D.btnCalibrateSubmit.disabled = false;
    const breedHint = d.breed_label ? ' · '+d.breed_label : '';
    addSavedStep('① 手动标定底膜'+breedHint);
    setStatus(D.status1, gotPreview
      ? ('✅ 标定已保存'+breedHint+' — 下方即 OpenCV 线条底膜')
      : ('✅ 标定已保存'+breedHint));
  } catch(e){
    setStatus(D.status1, '❌ '+e.message, true);
    D.btnCalibrateSubmit.disabled = false;
    updateCalibHint();
  }
}

async function renderMembraneMp4(){
  if(!S.currentProject){ alert('请先创建项目'); return; }
  if(!assertBreedCalibrated()) return;
  if(S.activeSpecies !== 'dog'){ alert('当前仅狗项目支持标定后直接渲染'); return; }
  D.btnRenderMembrane.disabled = true;
  setStatus(D.statusMembrane, '⏳ 烘焙狗管线并渲染 MP4…');
  try {
    const d = await apiPost('/api/portal/render-membrane', {
      customer_id: S.customerId,
      project_id: S.currentProject.project_id,
      preset: S.activeEmotion || '委屈·幼犬眼',
    });
    if(!d.ok) throw new Error(d.error||'渲染失败');
    S.videoUrl = d.video_url + '?t=' + Date.now();
    S.lastBaked = null;
    S.membraneInfo = {
      species: d.species || 'dog',
      membrane_type: d.membrane_type || '狗工程底膜',
      renderer: d.renderer || 'DogAffineRenderer',
      frame_count: d.frames,
    };
    D.previewVideo.src = S.videoUrl;
    show(D.videoWrap);
    D.btnStep4Next.disabled = false;
    addSavedStep('④ 狗底膜 MP4（'+ (d.membrane_type||'狗工程底膜') +'）');
    setStatus(D.statusMembrane, '✅ '+ (d.membrane_type||'狗工程底膜') +' 已保存，可继续第②步描述表情或第⑤步导出');
    await loadProjectState(S.currentProject.project_id);
  } catch(e){
    setStatus(D.statusMembrane, '❌ '+e.message, true);
  } finally {
    D.btnRenderMembrane.disabled = false;
  }
}

window.addEventListener('resize', () => { if(!D.calibrateWrap.classList.contains('hidden')) drawCalibOverlay(); });

function fileToBase64(file){
  return new Promise((res,rej)=>{
    const r=new FileReader();
    r.onload=()=>res(r.result.split(',')[1]);
    r.onerror=rej;
    r.readAsDataURL(file);
  });
}

/* ── Step 3: Pomot ── */
async function runPomot(isRound2){
  const nl = D.nlInput.value.trim();
  if(!nl){ alert('请输入描述'); return; }
  const btn = isRound2 ? D.btnPomotRound2 : D.btnPomotRun;
  btn.disabled = true;
  setStatus(D.status3, isRound2 ? '⏳ 微调中…' : '⏳ 生成中…');
  try {
    let d;
    if(isRound2){
      if(!S.lastBaked && !S.lastPacket){ alert('请先生成'); return; }
      d = await apiPost('/api/portal/pomot/round2', {
        nl,
        customer_id: S.customerId,
        project_id: S.currentProject?.project_id || '',
        species: S.activeSpecies,
        emotion: S.activeEmotion,
        breed: S.activeStyle,
        previous_baked: S.lastBaked,
      });
    } else {
      d = await apiPost('/api/portal/pomot/round1', {
        nl, species:S.activeSpecies, emotion:S.activeEmotion, breed:S.activeStyle,
        customer_id:S.customerId, project_id:S.currentProject?.project_id||'',
      });
    }
    if(!d.ok) throw new Error(d.error||'失败');
    applyPomotResult(d);
    D.btnStep3Next.disabled = false;
    setStatus(D.status3, '✅ 管线完成（未写入客户资产库，第⑤步点「保存客户资料」）');
    addSavedStep(isRound2 ? '③ Pomot 微调（内存）' : '③ Pomot 生成（内存）');
  } catch(e){
    setStatus(D.status3, '❌ '+e.message, true);
  } finally { btn.disabled = false; }
}

function applyPomotResult(d){
  S.lastSplit = d.split; S.lastRoute = d.route;
  S.lastPacket = d.packet_dict; S.lastBaked = d.baked_json;
  S.lastMetronome = d.beat_text||''; S.lastPrompt = d.prompt_04||'';
  S.lastWanPositive = d.wan_positive_clip || '';
  S.lastWanNegative = d.wan_negative_clip || '';
  if(S.lastPrompt && (!S.lastWanPositive || !S.lastWanNegative)){
    const wan=splitWanFrom04(S.lastPrompt);
    if(!S.lastWanPositive) S.lastWanPositive=wan.positive;
    if(!S.lastWanNegative) S.lastWanNegative=wan.negative;
  }
  if(d.route?.preset_name) S.activeEmotion = d.route.preset_name;
  if(d.route?.breed) S.activeStyle = d.route.breed;
  updateBreedBadges();
  if(S.lastBaked?.species && S.lastBaked.species !== S.activeSpecies){
    setStatus(D.status3, '⚠ 生成结果物种是「'+S.lastBaked.species+'」，与当前「'+S.activeSpecies+'」不一致', true);
  }
  S.videoUrl = '';
  hide(D.videoWrap);
  D.btnStep4Next.disabled = true;
  setStatus(D.status4, '③ 已更新生成数据 — 请到第④步重新「渲染 OpenCV 视频」（标定预览是中性脸，MP4 是情绪动画）');
  if(S.currentProject) loadProjectState(S.currentProject.project_id);
  syncEnergyPulseFromState();
  refreshWanClipUI();
  renderPomotSummary();
}

/* ── Step 4: OpenCV 渲染 ── */
async function renderVideo(){
  if(!S.lastBaked){ alert('请先生成管线（第③步）'); return; }
  if(!assertBreedCalibrated()) return;
  const ms = S.membraneStatus;
  if(ms && ms.action === 'regenerate'){
    alert(ms.warning + '\n\n请回第③步点击「生成表情」，再回来渲染。');
    return;
  }
  if(S.lastBaked.schema_version && String(S.lastBaked.schema_version).includes('human-prior') && S.activeSpecies === 'dog'){
    alert('当前生成数据是旧版人类管线，不是狗底膜。\n请回第③步重新「生成表情」。');
    return;
  }
  D.btnRenderVideo.disabled = true;
  setStatus(D.status4, '⏳ 渲染 OpenCV 视频中…');
  try {
    const d = await apiPost('/api/portal/render-preview', {
      customer_id: S.customerId,
      project_id: S.currentProject?.project_id||'',
      baked: S.lastBaked,
      species: S.activeSpecies,
      breed: S.activeStyle || getCalibBreed(),
    });
    if(!d.ok) throw new Error(d.error||'渲染失败');
    S.videoUrl = d.video_url + '?t=' + Date.now();
    S.membraneInfo = {
      species: d.species,
      membrane_type: d.membrane_type,
      renderer: d.renderer,
      frame_count: d.frames,
    };
    D.previewVideo.src = S.videoUrl;
    show(D.videoWrap);
    updateMembraneBadge(S.membraneInfo);
    D.btnStep4Next.disabled = false;
    addSavedStep('④ OpenCV 视频渲染（'+ (d.membrane_type||'底膜') +'）');
    setStatus(D.status4, '✅ ' + (d.membrane_type||'底膜') + ' 已保存');
    if(S.currentProject) loadProjectState(S.currentProject.project_id);
  } catch(e){
    setStatus(D.status4, '❌ '+e.message, true);
  } finally { D.btnRenderVideo.disabled = false; }
}

/* ── 保存 / 导出 ── */
async function saveAll(){
  if(!S.lastPacket && !S.calibrated){ alert('还没有可保存的内容'); return; }
  D.btnSaveAll.disabled = true;
  setStatus(D.status5, '⏳ 保存客户资料…');
  try {
    const d = await saveCustomerArchive({note:'门户完整保存', build_bundle: true});
    addSavedStep('⑤ 客户资料（送扩散前完整包）');
    setStatus(D.status5, '✅ 已保存（客户资料.json + 扩散引擎包/）');
    await loadProjects();
  } catch(e){
    setStatus(D.status5, '❌ '+e.message, true);
  } finally { D.btnSaveAll.disabled = false; }
}

async function doExport(){
  if(!S.lastBaked){ alert('请先生成管线'); return; }
  if(!S.videoUrl){ alert('请先渲染 OpenCV 底膜视频（第④步）'); return; }
  D.btnExport.disabled = true;
  setStatus(D.status5, '⏳ 更新 04_Prompt…');
  try {
    const d = await apiPost('/api/portal/export', {
      baked: S.lastBaked, species: S.activeSpecies,
      breed: S.activeStyle, emotion: S.activeEmotion,
      action: (S.lastSplit && S.lastSplit.action) || D.nlInput.value.trim(),
      customer_id: S.customerId,
      project_id: S.currentProject?.project_id||'',
    });
    if(!d.ok) throw new Error(d.error||'导出失败');
    const del = d.deliverables || {};
    S.lastPrompt = del.prompt_04 || S.lastPrompt || '';
    S.lastWanPositive = del.wan_positive_clip || S.lastWanPositive || '';
    S.lastWanNegative = del.wan_negative_clip || S.lastWanNegative || '';
    if(S.lastPrompt && (!S.lastWanPositive || !S.lastWanNegative)){
      const wan=splitWanFrom04(S.lastPrompt);
      S.lastWanPositive=wan.positive; S.lastWanNegative=wan.negative;
    }
    D.resultPrompt.textContent = S.lastPrompt || '(尚未生成)';
    refreshWanClipUI();
    renderPomotSummary();
    if(del.membrane_meta) S.membraneInfo = del.membrane_meta;
    S.lastProfile = d.profile || null;
    S.lastBundle = d.bundle || null;
    S.bundleZipUrl = del.bundle_zip_url || S.bundleZipUrl || '';
    refreshDeliverablesPanel(del);
    refreshArchiveUI();
    addSavedStep('⑤ 04_Prompt 已更新');
    setStatus(D.status5, d.note || '✅ 两件套 + 扩散引擎包已就绪');
  } catch(e){
    setStatus(D.status5, '❌ '+e.message, true);
  } finally { D.btnExport.disabled = false; }
}

function addSavedStep(label){
  S.savedSteps.push(label);
  const html = S.savedSteps.map(s=>'<li>✓ '+esc(s)+'</li>').join('');
  D.stepSaves3.innerHTML = html;
  D.stepSaves5.innerHTML = html;
}

/* ── 事件 ── */
D.btnEnter.onclick = () => showRegister();
D.linkLogin.onclick = () => showLogin();
D.btnRegister.onclick = doRegister;
D.btnLogin.onclick = doLogin;
D.switchToLogin.onclick = () => showLogin();
D.switchToRegister.onclick = () => showRegister();
D.btnLogout.onclick = doLogout;
D.btnNewProject.onclick = () => startNewProject(false);
D.wizardBack.onclick = async () => { await loadProjects(); showDashboard(); };
D.btnUpload.onclick = uploadPhotoOnly;
D.btnCalibrateSubmit.onclick = submitCalibration;
D.btnRenderMembrane.onclick = renderMembraneMp4;
D.btnStep1Next.onclick = () => goStep(2);
D.btnStep2Prev.onclick = () => goStep(1);
D.btnStep2Next.onclick = () => goStep(3);
D.btnStep3Prev.onclick = () => goStep(2);
D.btnStep3Next.onclick = () => goStep(4);
D.btnStep4Prev.onclick = () => goStep(3);
D.btnStep4Next.onclick = () => goStep(5);
D.btnStep5Prev.onclick = () => goStep(4);
D.btnPomotRun.onclick = () => runPomot(false);
D.btnPomotRound2.onclick = () => runPomot(true);
D.btnRenderVideo.onclick = renderVideo;
D.btnSaveAll.onclick = saveAll;
D.btnExport.onclick = doExport;
if(D.btnDownloadBundle) D.btnDownloadBundle.onclick = ()=>{
  if(!S.bundleZipUrl){ alert('请先点「保存客户资料」或「更新导出」'); return; }
  window.open(S.bundleZipUrl, '_blank');
};
if(D.btnCopyWanPos) D.btnCopyWanPos.onclick = ()=> copyText(S.lastWanPositive, D.btnCopyWanPos);
if(D.btnCopyWanNeg) D.btnCopyWanNeg.onclick = ()=> copyText(S.lastWanNegative, D.btnCopyWanNeg);
if(D.calibBreedSelect) D.calibBreedSelect.onchange = function(){
  S.calibBreed = this.value;
  if(S.calibrated && S.calibratedBreed && S.calibBreed !== S.calibratedBreed){
    S.calibrated = false;
    S.calibratedBreed = '';
    D.btnStep1Next.disabled = true;
    hideMembranePreview();
    setStatus(D.status1, '⚠ 品种已变更，请重新完成锚点标定', true);
  }
};
D.speciesSelect.onchange = async function(){
  S.activeSpecies = this.value;
  const lb = $('species-label');
  if(lb) lb.textContent = this.value;
  renderPresets(this.value);
  syncCalibBreedUI(this.value);
  if(S.currentProject?.project_id){
    try {
      await apiPost('/api/customer/'+S.customerId+'/project/update', {
        project_id: S.currentProject.project_id,
        species: S.activeSpecies,
      });
      S.currentProject.species = S.activeSpecies;
    } catch(e){ console.warn('项目物种更新失败', e); }
  }
  if(!D.calibrateWrap.classList.contains('hidden') && !S.calibrated){
    S.calibAnchors = {}; S.calibStepIdx = 0; S.calibMarkEars = false;
    updateCalibHint(); drawCalibOverlay();
  }
};

/* ── 启动 ── */
async function boot(){
  if(location.protocol==='file:'){
    document.body.innerHTML='<div style="padding:40px;text-align:center"><h2>请通过 HTTP 访问</h2><p>启动服务后访问 /portal</p></div>';
    return;
  }
  if(!await ensurePortalFresh()) return;
  if(S.token){
    try {
      const d = await apiPost('/api/auth/verify', {token:S.token});
      if(d.ok){
        S.customer=d.customer; S.customerId=d.customer_id;
        await loadPresets();
        await loadProjects();
        showDashboard();
        return;
      }
    } catch(e){}
  }
  showWelcome();
}

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot);
else boot();

})();
