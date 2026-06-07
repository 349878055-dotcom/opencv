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
  calibrateImg: $('calibrate-img'),
  calibrateLoadErr: $('calibrate-load-err'),
  calibrateMainCanvas: $('calibrate-main-canvas'),
  btnCalibrateUndo: $('btn-calibrate-undo'), btnCalibrateReset: $('btn-calibrate-reset'),
  btnCalibrateSubmit: $('btn-calibrate-submit'),
  btnMediapipeDetect: $('btn-mediapipe-detect'),
  optionalCalibPanel: $('optional-calib-panel'),
  membranePreviewWrap: $('membrane-preview-wrap'), membranePreviewBreed: $('membrane-preview-breed'),
  membranePreviewCustom: $('membrane-preview-custom'),
  membranePreviewNote: $('membrane-preview-note'), membraneBreedRef: $('membrane-breed-ref'),
  membraneDiffBody: $('membrane-diff-body'),
  membraneDiffEmpty: $('membrane-diff-empty'), membraneDiffWrap: $('membrane-diff-wrap'),
  membraneDiagWrap: $('membrane-diag-wrap'), membraneDiagFormula: $('membrane-diag-formula'),
  membranePipelineList: $('membrane-pipeline-list'), membraneShapeBody: $('membrane-shape-body'),
  membraneWarnList: $('membrane-warn-list'),
  membraneRetuneWrap: $('membrane-retune-wrap'), membraneRetuneHint: $('membrane-retune-hint'),
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
  btnStep2Prev: $('btn-step2-prev'), btnStep2Next: $('btn-step2-next'),
  btnPomotRun: $('btn-pomot-run'), pomotSummary: $('pomot-summary'),
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
  /* ── 低膜-人脸叠加校验 ── */
  overlayVerifyWrap: $('overlay-verify-wrap'),
  overlayPreviewImg: $('overlay-preview-img'),
  alignViewTabs: $('align-view-tabs'),
  alignmentErrorPanel: $('alignment-error-panel'),
  btnOverlayRetake: $('btn-overlay-retake'),
  btnOverlayConfirm: $('btn-overlay-confirm'),
  /* ── 管线调试 ── */
  pipelineDebugWrap: $('pipeline-debug-wrap'),
  btnDebugLoad: $('btn-debug-load'),
  debugContent: $('debug-content'),
};

let S = {
  token: localStorage.getItem('portal_token') || '',
  customer: null, customerId: '',
  projects: [], currentProject: null,
  currentStep: 1,
  photoFile: null, photoName: '', photoUrl: '', photoBlobUrl: '', imageWidth: 0, imageHeight: 0,
  detection: null, templateParams: null, calibrated: false, calibratedBreed: '',
  calibBreed: '',
  calibAnchors: {}, calibOrder: [],
  presets: {human:{emotions:[],styles:[]}}, // 仅索引 id/label，数值在预设资产库
  activeEmotion: '', activeStyle: '', activeSpecies: 'human',
  lastSplit: null, lastRoute: null, lastPacket: null, lastBaked: null,
  lastMetronome: '', lastPrompt: '', lastWanPositive: '', lastWanNegative: '',
  videoUrl: '', membraneInfo: null,
  membranePreviewUrl: '',
  membraneStatus: null,
  alignmentBundle: null,
  alignmentView: 'grid',
  savedSteps: [],
  lastProfile: null, lastBundle: null, bundleZipUrl: '',
};

/* ── 标定放大倍数（滚轮可调）── */
let CALIB_ZOOM_FACTOR = 3;

function archivePayload(extra={}){
  return {
    customer_id: S.customerId,
    project_id: S.currentProject?.project_id || '',
    species: S.activeSpecies,
    breed: S.activeStyle,
    emotion: S.activeEmotion || S.lastRoute?.preset_name || '',
    active_emotion: S.activeEmotion,
    active_style: S.activeStyle,
    action: (S.lastSplit && S.lastSplit.action) || '',
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
  return item?.label || styleId || '';
}

function getCalibBreed(){
  return '';
}

function syncCalibBreedUI(species){
  if(!D.calibBreedWrap) return;
  hide(D.calibBreedWrap);
  S.calibBreed = '';
}

function breedMismatchMessage(selected, calibrated){
  return '';
}

function assertBreedCalibrated(){
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
  const label = '🙂 人项目';
  return '<span class="species-tag human">'+label+'</span>';
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
    D.speciesBannerMsg.textContent = '标定完成后：到第②步选情绪 → 第③步生成';
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
    const icon = '🙂';
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
  S.calibAnchors = {};
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
      drawCalibrateView();
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

function overlayPreviewApiUrl(projectId, opts){
  /* 底膜线条叠加预览：?customer_id=...&project_id=...&show_eyelid=...&show_eyebrow=...&show_pupil=...&opacity=... */
  const p = projectId || S.currentProject?.project_id || '';
  const q = new URLSearchParams({
    customer_id: S.customerId, project_id: p,
  });
  if(opts){
    if(opts.show_eyelid != null) q.set('show_eyelid', opts.show_eyelid === true || opts.show_eyelid === '1' ? '1' : '0');
    if(opts.show_eyebrow != null) q.set('show_eyebrow', opts.show_eyebrow === true || opts.show_eyebrow === '1' ? '1' : '0');
    if(opts.show_pupil != null) q.set('show_pupil', opts.show_pupil === true || opts.show_pupil === '1' ? '1' : '0');
    if(opts.opacity != null) q.set('opacity', String(opts.opacity));
  }
  return '/api/portal/overlay-preview?' + q.toString();
}

function showOverlayVerifyPanel(){
  /* 标定完成后展示 MP vs CV 对齐诊断（与 diagnose_mapping_pipeline 同源） */
  if(D.overlayVerifyWrap){
    D.overlayVerifyWrap.classList.remove('hidden');
    loadAlignmentVerifyBundle();
    D.overlayVerifyWrap.scrollIntoView({behavior:'smooth', block:'nearest'});
  }
  if(D.pipelineDebugWrap) D.pipelineDebugWrap.classList.remove('hidden');
}

function alignmentVerifyBundleUrl(projectId){
  const p = projectId || S.currentProject?.project_id || '';
  return '/api/portal/alignment-verify/bundle?customer_id='
    + encodeURIComponent(S.customerId) + '&project_id=' + encodeURIComponent(p);
}

function setAlignmentView(view){
  S.alignmentView = view || 'grid';
  if(D.alignViewTabs){
    D.alignViewTabs.querySelectorAll('.align-view-tab').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.view === S.alignmentView);
    });
  }
  const b64 = S.alignmentBundle?.images?.[S.alignmentView];
  if(D.overlayPreviewImg){
    D.overlayPreviewImg.src = b64 ? ('data:image/png;base64,' + b64) : '';
  }
}

function _errClass(px){
  if(px < 8) return 'err-ok';
  if(px < 20) return 'err-warn';
  return 'err-bad';
}

function renderAlignmentErrors(errors){
  if(!D.alignmentErrorPanel) return;
  if(!errors){
    D.alignmentErrorPanel.classList.add('hidden');
    D.alignmentErrorPanel.textContent = '';
    return;
  }
  const lines = ['ALIGN ERROR (px)'];
  for(const [side, tag] of [['left','LEFT'],['right','RIGHT']]){
    const e = errors[side] || {};
    lines.push(`-- ${tag} --`);
    for(const [k, lbl] of [
      ['pupil_center_px','pupil'],
      ['iris_radius_px','iris r'],
      ['lid_top_px','lid top'],
      ['brow_peak_px','brow peak'],
    ]){
      const v = e[k];
      if(v == null) continue;
      const cls = _errClass(Number(v));
      lines.push(`<span class="${cls}">  ${lbl}: ${v}</span>`);
    }
  }
  D.alignmentErrorPanel.innerHTML = lines.join('<br>');
  D.alignmentErrorPanel.classList.remove('hidden');
}

async function loadAlignmentVerifyBundle(){
  const pid = S.currentProject?.project_id || '';
  if(!pid || !D.overlayPreviewImg) return;
  D.overlayPreviewImg.alt = '加载对齐诊断…';
  try {
    const res = await fetch(alignmentVerifyBundleUrl(pid));
    const d = await res.json();
    if(!d.ok) throw new Error(d.error || '对齐诊断加载失败');
    S.alignmentBundle = d;
    setAlignmentView(S.alignmentView || 'grid');
    renderAlignmentErrors(d.errors_px);
  } catch(e){
    S.alignmentBundle = null;
    if(D.overlayPreviewImg) D.overlayPreviewImg.alt = '对齐诊断加载失败: ' + e.message;
    renderAlignmentErrors(null);
  }
}

/* ── 管线调试数据加载 ── */
async function loadPipelineDebug(){
  /* 从后端加载全流程中间数据并显示 */
  if(!D.debugContent) return;
  const pid = S.currentProject ? (S.currentProject.project_id || '') : '';
  if(!pid){
    D.debugContent.textContent = '错误：未选择项目';
    D.debugContent.style.display = 'block';
    return;
  }
  try {
    const res = await fetch('/api/portal/pipeline-debug?customer_id='+encodeURIComponent(S.customerId)+'&project_id='+encodeURIComponent(pid));
    const d = await res.json();
    if(!d.ok) throw new Error(d.error || '加载失败');

    /* 构建结构化显示 */
    const lines = [];

    /* ▸ 基础信息 */
    lines.push('══════════════════ 管线调试数据 ══════════════════');
    lines.push(`客户: ${d.customer_id}  ·  项目: ${d.project_id}  ·  物种: ${d.species}`);
    lines.push(`照片尺寸: ${d.image_size[0]}×${d.image_size[1]}`);
    lines.push('');

    /* ▸ ① 检测原始数据 */
    lines.push('── ① 检测原始数据 ──');
    if(d.detection && Object.keys(d.detection).length){
      for(const [k,v] of Object.entries(d.detection)){
        lines.push(`  ${k}: ${JSON.stringify(v)}`);
      }
    } else {
      lines.push('  （无检测数据）');
    }
    lines.push('');

    /* ▸ ② 三点标定原始计算 */
    lines.push('── ② 三点标定原始计算 ──');
    if(d.anchor_calculation){
      const ac = d.anchor_calculation;
      lines.push(`  est_w: ${ac.est_w_px}px (${ac.est_w_formula})`);
      lines.push(`  说明: ${ac.est_w_explanation}`);
      if(ac.raw_anchor_adjustments && Object.keys(ac.raw_anchor_adjustments).length){
        lines.push(`  三点标定原始 adj:`);
        for(const [k,v] of Object.entries(ac.raw_anchor_adjustments)){
          lines.push(`    ${k}: ${v}`);
        }
      }
    }
    lines.push('');

    /* ▸ ③ 客户调整参数 */
    lines.push('── ③ 客户调整参数 ──');
    if(d.template_pipeline){
      const tp = d.template_pipeline;
      lines.push(`  标准模板参数:`);
      if(tp.standard_params){
        for(const [k,v] of Object.entries(tp.standard_params)){
          lines.push(`    ${k}: ${v}`);
        }
      }
      lines.push(`  客户调整量:`);
      if(tp.customer_adjustments){
        for(const [k,v] of Object.entries(tp.customer_adjustments)){
          lines.push(`    ${k}: ${v}`);
        }
      }
      lines.push(`  应用后参数:`);
      if(tp.applied_params){
        for(const [k,v] of Object.entries(tp.applied_params)){
          lines.push(`    ${k}: ${v}`);
        }
      }
    }
    lines.push('');

    /* ▸ ④ 渲染器常量 */
    lines.push('── ④ 渲染器常量 ──');
    if(d.renderer_constants){
      const rc = d.renderer_constants;
      lines.push(`  标准常量:`);
      if(rc.standard){
        for(const [k,v] of Object.entries(rc.standard)){
          lines.push(`    ${k}: ${v}`);
        }
      }
      lines.push(`  调整后常量:`);
      if(rc.adjusted){
        for(const [k,v] of Object.entries(rc.adjusted)){
          lines.push(`    ${k}: ${v}`);
        }
      }
    }
    lines.push('');

    /* ▸ ⑤ 模型锚点 vs 照片锚点 */
    lines.push('── ⑤ 锚点对比 ──');
    if(d.anchors){
      const a = d.anchors;
      if(a.photo && Object.keys(a.photo).length){
        lines.push(`  照片锚点 (像素):`);
        for(const [k,v] of Object.entries(a.photo)){
          lines.push(`    ${k}: [${v.join(', ')}]`);
        }
      }
      if(a.model_standard && a.model_standard.length){
        lines.push(`  模型锚点标准 (1024画布):`);
        const labels = ['左眼','右眼','鼻尖'];
        a.model_standard.forEach((p,i) => {
          lines.push(`    ${labels[i]||i}: [${p.join(', ')}]`);
        });
      }
      if(a.model_adjusted && a.model_adjusted.length){
        lines.push(`  模型锚点调整后 (1024画布, eye_dist=${(d.template_pipeline||{}).customer_adjustments?.eye_distance||'?'}):`);
        const labels = ['左眼','右眼','鼻尖'];
        a.model_adjusted.forEach((p,i) => {
          lines.push(`    ${labels[i]||i}: [${p.join(', ')}]`);
        });
      }
    }
    lines.push('');

    /* ▸ ⑥ 空间标定 */
    lines.push('── ⑥ 空间标定 ──');
    if(d.spatial_scale){
      const ss = d.spatial_scale;
      lines.push(`  照片眼距: ${ss.photo_eye_distance_px}px`);
      lines.push(`  模型眼距(标准): ${ss.model_eye_distance_standard}px`);
      lines.push(`  缩放比例: ${ss.scale_standard} (照片眼距/模型眼距)`);
      lines.push(`  输出尺寸: ${ss.output_w}×${ss.output_h}`);
    }
    if(d.spatial_calibration && d.spatial_calibration.matrix){
      const sc = d.spatial_calibration;
      lines.push(`  仿射矩阵:`);
      if(Array.isArray(sc.matrix)){
        sc.matrix.forEach((row,i) => {
          lines.push(`    [${row.join(', ')}]`);
        });
      }
    }
    lines.push('');

    /* ▸ ⑦ 几何适配器日志 */
    lines.push('── ⑦ 几何适配器日志 ──');
    lines.push(`  方法: ${d.geometry_adapter_method}`);
    lines.push(`  置信度: ${d.geometry_adapter_confidence}`);
    if(d.geometry_adapter_notes && d.geometry_adapter_notes.length){
      d.geometry_adapter_notes.forEach((n,i) => {
        lines.push(`  [${i+1}] ${n}`);
      });
    }
    lines.push('');
    lines.push('══════════════════ 调试数据结束 ══════════════════');

    D.debugContent.textContent = lines.join('\n');
    D.debugContent.style.display = 'block';
  } catch(e){
    D.debugContent.textContent = '❌ 加载失败: ' + e.message;
    D.debugContent.style.display = 'block';
  }
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
  D.membraneDiffBody.innerHTML = rows.map(r => {
    const before = r.before ?? r.breed ?? '—';
    const after = r.after ?? r.calibrated ?? '—';
    const delta = r.delta;
    const hint = r.hint || '';
    let deltaTxt = '';
    if(typeof delta === 'number' && !Number.isNaN(delta) && Math.abs(delta) > 0.0001){
      deltaTxt = ` (${delta > 0 ? '+' : ''}${delta})`;
    }
    return `<tr><td>${esc(r.label||r.key)}</td><td>${esc(String(before))}</td><td>${esc(String(after))}</td><td>${esc(hint)}${esc(deltaTxt)}</td></tr>`;
  }).join('');
}

function updateMembraneRetunePanel(diag){
  // 标注仅需左眼中心、右眼中心、鼻尖三点，不再需要微调眼形
  if(D.membraneRetuneWrap) hide(D.membraneRetuneWrap);
}

function renderMembraneDiagnostics(diag){
  if(!D.membraneDiagWrap) return;
  if(!diag || !diag.pipeline || !diag.pipeline.length){
    hide(D.membraneDiagWrap);
    return;
  }
  show(D.membraneDiagWrap);
  if(D.membraneDiagFormula) D.membraneDiagFormula.textContent = diag.formula || '';
  if(D.membranePipelineList){
    D.membranePipelineList.innerHTML = diag.pipeline.map(p => {
      let val = esc(p.value || '');
      // 步骤4（空间仿射）追加仿射矩阵分解
      if(p.step === 4 && diag.affine){
        const a = diag.affine;
        val += ` <span class="affine-detail">缩放X=${a.scale_x} 缩放Y=${a.scale_y} 旋转=${a.rotation_deg}° 平移=(${a.translate_x},${a.translate_y})</span>`;
      }
      return `<li><strong>${esc(p.step)}. ${esc(p.title)}</strong> — ${val}` + `<em>${esc(p.detail || '')}</em></li>`;
    }).join('');
  }
  if(D.membraneShapeBody){
    const rows = diag.shape_params || [];
    D.membraneShapeBody.innerHTML = rows.map(r =>
      `<tr><td>${esc(r.label||r.key)}</td><td>${esc(String(r.value))}</td>`
      + `<td>${esc(r.source||'')}</td><td>${esc(r.note||'')}</td></tr>`
    ).join('');
  }
  const warns = diag.warnings || [];
  if(D.membraneWarnList){
    if(!warns.length && !(diag.spatial && diag.spatial.hint)){ hide(D.membraneWarnList); D.membraneWarnList.innerHTML = ''; }
    else {
      show(D.membraneWarnList);
      const hint = (diag.spatial && diag.spatial.hint) ? `<li>ℹ ${esc(diag.spatial.hint)}</li>` : '';
      D.membraneWarnList.innerHTML = hint + warns.map(w => `<li>⚠ ${esc(w)}</li>`).join('');
    }
  }
  updateMembraneRetunePanel(diag);
}

function showMembraneCompare(data){
  if(!D.membranePreviewWrap) return;
  const note = data.membrane_note || '标定后线条底膜 · 红=眼眶 · 蓝=瞳孔 · 绿=眉脊';
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
  renderMembraneDiagnostics(data.membrane_diagnostics);
  show(D.membranePreviewWrap);
  D.membranePreviewWrap.scrollIntoView({behavior:'smooth', block:'nearest'});
}

function showMembranePreview(url, note){
  showMembraneCompare({ preview_url: url, preview_base64: url?.startsWith('data:') ? url.split(',')[1] : '', membrane_note: note });
}

function applyCalibratePreview(d){
  if(d.preview_url || d.preview_base64){
    showMembraneCompare(d);
    return true;
  }
  if(S.currentProject){
    showMembraneCompare({
      preview_url: membranePreviewApiUrl(S.currentProject.project_id)+'&variant=calibrated',
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
  if(D.membraneRetuneWrap) hide(D.membraneRetuneWrap);
}

function restoreCalibration(calib){
  if(!calib || !calib.anchors) return false;
  if(S.photoName && calib.photo_name && calib.photo_name !== S.photoName) return false;
  S.calibAnchors = {...calib.anchors};
  // 重建 calibOrder（保证撤销按钮功能正常）
  const steps = calibSteps();
  S.calibOrder = steps.filter(st => S.calibAnchors[st.key]).map(st => st.key);
  if(Array.isArray(calib.image_size) && calib.image_size.length >= 2){
    S.imageWidth = calib.image_size[0];
    S.imageHeight = calib.image_size[1];
  }
  // 恢复后同步相位（全部已标定 → done）
  S.calibPhase = 'done';
  S.calibZoomCenter = null;
  S.calibrated = true;
  S.calibratedBreed = calib.breed || '';
  if(calib.breed) S.activeStyle = calib.breed;
  S.detection = {
    method: calib.method || 'manual',
    confidence: calib.confidence ?? 1,
    adjustments: calib.adjustments,
  };
  drawCalibrateView();
  updateCalibHint();
  D.btnStep1Next.disabled = false;
  showMembraneCompare({
    preview_url: calib.preview_url || calib.preview_base64,
    adjustment_diff: calib.adjustment_diff,
    membrane_diagnostics: calib.membrane_diagnostics,
    membrane_note: calib.membrane_note || '标定后底膜线条',
  });
  updateMembraneRetunePanel(calib.membrane_diagnostics);
  showOverlayVerifyPanel();
  setStatus(D.status1, '✅ 已恢复上次标定 — 下方可核对底膜线条与照片吻合度');
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
  if(!del?.video_exists) return false;
  const meta = del.membrane_meta || {};
  if(!baked){
    return Boolean(meta.species && meta.baked_revision);
  }
  const rev = baked.revision || baked.gaze_emotion_id || baked.mood || '';
  return !rev || !meta.baked_revision || meta.baked_revision === rev;
}

function refreshDeliverablesPanel(del){
  del = del || {};
  const meta = del.membrane_meta || S.membraneInfo || {};
  const sp = meta.species || S.activeSpecies;
  const spLabel = '🙂 人';

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
    D.membraneVerifyLine.textContent = '完成④渲染后，此处会显示底膜类型。';
  }
}

function updateMembraneBadge(info){
  if(!info || !info.membrane_type){ hide(D.membraneBadge); return; }
  const sp = '🙂';
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

    function applyActivePresetFromPacket(pkt, baked){
      if(!pkt && !baked) return;
      const pid = baked?.preset_id || pkt?.preset_id;
      if(pid){ S.activeEmotion = pid; return; }
      if(pkt?.emotion && String(pkt.emotion).includes('/')) S.activeEmotion = pkt.emotion;
    }

    if(badBaked){
      setStatus(D.status3, ms.warning || '⚠ 请第③步重新「生成表情」以使用狗/猫底膜', true);
      S.lastBaked = null;
      S.lastPacket = d.pipeline?.packet || null;
      applyActivePresetFromPacket(S.lastPacket, null);
    } else if(d.pipeline?.packet){
      S.lastPacket = d.pipeline.packet;
      applyActivePresetFromPacket(S.lastPacket, null);
    }
    // 02 烘焙不落盘：不从磁盘恢复；须第③步重新生成（内存）或第④步即时编译
    if(!S.lastBaked && d.deliverables?.video_exists){
      setStatus(D.status4, 'ℹ 已有 MP4；若换情绪请第③步重新生成后再渲染', false);
    }
    if(d.slider_current?.packet){
      S.lastPacket = d.slider_current.packet;
      applyActivePresetFromPacket(S.lastPacket, S.lastBaked);
    }

    if(d.deliverables){
      const canShowVideo = d.deliverables.video_exists && (
        !S.lastBaked ? mp4MatchesBaked(d.deliverables, null) : mp4MatchesBaked(d.deliverables, S.lastBaked)
      );
      if(canShowVideo && !badBaked){
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
      let hasContent = false;
      let groupHtml = `<div class="preset-group-label">${esc(g.label)}</div>`;
      (g.keys || []).forEach((keyItem, idx) => {
        if(keyItem && typeof keyItem === 'object' && keyItem.category){
          const catId = keyItem.category;
          const catLabel = keyItem.label || catId;
          const variantIds = (keyItem.variants || []).map(v => `${catId}/${v}`);
          const rows = variantIds.map(id => emotionMap[id]).filter(Boolean);
          if(!rows.length) return;
          hasContent = true;
          rows.forEach(e => used.add(e.id));
          const catActive = rows.some(e => e.id === activeId);
          groupHtml += `<div class="preset-category${catActive ? ' active' : ''}">`;
          groupHtml += `<div class="preset-category-label">${esc(catLabel)}</div>`;
          groupHtml += `<div class="preset-category-variants">`;
          groupHtml += rows.map(e => btn(e, 'preset-btn-variant')).join('');
          groupHtml += `</div></div>`;
          return;
        }
        const id = resolveGroupEmotionId(g, idx, emotionMap);
        if(!id || used.has(id)) return;
        used.add(id);
        hasContent = true;
        groupHtml += btn(emotionMap[id], '');
      });
      if(hasContent) html += groupHtml;
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

  bindPresetButtons(D.presetContainer, (id) => {
    S.activeEmotion = id;
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

const CALIB_REQUIRED = [
  {key:'left_eye', label:'① 左眼中心', color:'#ef4444'},
  {key:'right_eye', label:'② 右眼中心', color:'#ef4444'},
  {key:'nose', label:'③ 鼻尖', color:'#3b82f6'},
];
function calibSteps(){
  return [...CALIB_REQUIRED];
}

function updateOptionalCalibPanel(){
  hide(D.optionalCalibPanel);
}

function resetPhotoUI(){
  hide(D.calibrateWrap);
  hideMembranePreview();
  D.btnUpload.disabled = !S.photoFile;
  D.btnStep1Next.disabled = !S.calibrated;
  S.calibrated = false;
  S.calibAnchors = {};
  S.calibOrder = [];
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
  setStatus(D.status1, '⏳ 上传照片 → MediaPipe 检测…');
  try {
    const b64 = await fileToBase64(S.photoFile);
    const d = await apiPost('/api/portal/project/upload-photo', {
      customer_id: S.customerId,
      project_id: S.currentProject.project_id,
      photo_data: b64,
      photo_name: S.photoFile.name,
      species: S.activeSpecies,
      breed: getCalibBreed(),
    });
    if(!d.ok) throw new Error(d.error||'上传或 MediaPipe 检测失败');
    S.photoName = d.photo_name;
    S.photoUrl = d.photo_url;
    S.imageWidth = d.image_width || 0;
    S.imageHeight = d.image_height || 0;
    startCalibrationUI();
    applySuggestedAnchors(d.suggested_anchors, d.detection);
    setStatus(D.status1, '⏳ MediaPipe 检测通过，正在自动标定…');
    await submitCalibrationAuto();
  } catch(e){
    setStatus(D.status1, '❌ '+e.message, true);
    S.calibrated = false;
    D.btnStep1Next.disabled = true;
  } finally { D.btnUpload.disabled = false; }
}

function applySuggestedAnchors(suggested, detection){
  if(!suggested) return;
  S.calibAnchors = {};
  const steps = calibSteps();
  for(const st of steps){
    const p = suggested[st.key];
    if(p && p.length >= 2){
      S.calibAnchors[st.key] = p;
    }
  }
  // 更新新标定状态
  _syncCalibPhase();
  drawCalibrateView();
  updateCalibHint();
  if(detection) S.detection = detection;
}

/* ══════════════════════════════════════════════
   标定预览 · MediaPipe-only（无手标）
   上传后自动检测+标定；画布仅展示 MP 锚点，不可点击修改
   ══════════════════════════════════════════════ */

/** 放大倍数（点击后显示原图 1/3 宽高的区域）—— 已在 line 90 声明 */

/** 同步 calibPhase / calibCurrentKey */
function _syncCalibPhase(){
  const steps = calibSteps();
  S.calibCurrentKey = null;
  for(const st of steps){
    if(!S.calibAnchors[st.key]){ S.calibCurrentKey = st.key; break; }
  }
  S.calibPhase = S.calibCurrentKey ? 'idle' : 'done';
  S.calibZoomCenter = null;
}

/** 主画布渲染：全图 / 放大 / 标记 */
function drawCalibrateView(){
  const cvs = D.calibrateMainCanvas;
  if(!cvs) return;
  const ctx = cvs.getContext('2d');
  const img = D.calibrateImg;
  if(!img || !img.complete || !img.naturalWidth) return;

  const iw = img.naturalWidth, ih = img.naturalHeight;
  const cw = cvs.width, ch = cvs.height;
  const isZoomed = S.calibPhase === 'zoomed' && S.calibZoomCenter;

  ctx.clearRect(0, 0, cw, ch);
  ctx.fillStyle = '#111';
  ctx.fillRect(0, 0, cw, ch);

  if(isZoomed){
    // ── 放大视图 ──
    const [zx, zy] = S.calibZoomCenter;
    const zoomHalf = Math.max(iw, ih) / (2 * CALIB_ZOOM_FACTOR);
    const srcX = Math.max(0, zx - zoomHalf);
    const srcY = Math.max(0, zy - zoomHalf);
    const srcW = Math.min(iw - srcX, zoomHalf * 2);
    const srcH = Math.min(ih - srcY, zoomHalf * 2);
    ctx.drawImage(img, srcX, srcY, srcW, srcH, 0, 0, cw, ch);

    // 十字准心
    ctx.strokeStyle = 'rgba(255,255,255,0.35)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(cw/2 - 30, ch/2); ctx.lineTo(cw/2 + 30, ch/2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cw/2, ch/2 - 30); ctx.lineTo(cw/2, ch/2 + 30); ctx.stroke();
    ctx.setLineDash([]);

    // 提示文字
    ctx.fillStyle = 'rgba(255,255,255,0.55)';
    ctx.font = '13px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    ctx.fillText('点击确认该点中心位置', cw/2, 6);

    // 缩放倍数指示（右上角）
    ctx.fillStyle = 'rgba(0,0,0,0.55)';
    ctx.fillRect(cw - 86, 4, 82, 22);
    ctx.fillStyle = '#fff';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    ctx.fillText('×' + CALIB_ZOOM_FACTOR.toFixed(1), cw - 8, 16);
  } else {
    // ── 全图视图（适配 canvas 大小）──
    const scale = Math.min(cw / iw, ch / ih) * 0.92;
    const dw = iw * scale, dh = ih * scale;
    const dx = (cw - dw) / 2, dy = (ch - dh) / 2;
    ctx.drawImage(img, 0, 0, iw, ih, dx, dy, dw, dh);

    // 已放置的锚点标记
    for(const key of ['left_eye', 'right_eye', 'nose']){
      const pt = S.calibAnchors[key];
      if(!pt) continue;
      const px = dx + pt[0] * scale;
      const py = dy + pt[1] * scale;
      const color = key === 'nose' ? '#3b82f6' : '#ef4444';
      const label = key === 'left_eye' ? 'L' : key === 'right_eye' ? 'R' : 'N';

      ctx.fillStyle = color;
      ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
      ctx.fillText(label, px, py - 8);
    }

    // 三点连线
    const le = S.calibAnchors.left_eye, re = S.calibAnchors.right_eye;
    if(le && re){
      const lx = dx + le[0]*scale, ly = dy + le[1]*scale;
      const rx = dx + re[0]*scale, ry = dy + re[1]*scale;
      ctx.strokeStyle = 'rgba(239,68,68,0.45)'; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(lx, ly); ctx.lineTo(rx, ry); ctx.stroke();
      const no = S.calibAnchors.nose;
      if(no){
        const mx = (lx + rx) / 2, my = (ly + ry) / 2;
        const nx = dx + no[0]*scale, ny = dy + no[1]*scale;
        ctx.strokeStyle = 'rgba(59,130,246,0.45)';
        ctx.beginPath(); ctx.moveTo(mx, my); ctx.lineTo(nx, ny); ctx.stroke();
      }
    }

    // 步骤指示器（左上角覆盖）
    const steps = calibSteps();
    let yOff = 4;
    ctx.font = '12px sans-serif';
    ctx.textBaseline = 'top';
    for(const st of steps){
      const done = !!S.calibAnchors[st.key];
      const active = S.calibCurrentKey === st.key;
      ctx.fillStyle = done ? '#22c55e' : (active ? '#f59e0b' : 'rgba(255,255,255,0.3)');
      ctx.textAlign = 'left';
      ctx.fillText((done ? '✓ ' : (active ? '➤ ' : '○ ')) + st.label, 6, yOff);
      yOff += 18;
    }
  }
}

/** 主画布点击：已禁用（MediaPipe-only，不支持手标） */
function handleCalibrateClick(e){
  return;
  /* legacy manual calibration disabled */
  const cvs = D.calibrateMainCanvas;
  if(!cvs || !D.calibrateImg || !D.calibrateImg.complete) return;
  const rect = cvs.getBoundingClientRect();
  const cw = cvs.width, ch = cvs.height;
  const img = D.calibrateImg;
  const iw = img.naturalWidth, ih = img.naturalHeight;
  const displayX = e.clientX - rect.left;
  const displayY = e.clientY - rect.top;

  if(S.calibPhase === 'zoomed' && S.calibZoomCenter){
    // ── 放大状态下点击 → 确认中心点 ──
    const [zx, zy] = S.calibZoomCenter;
    const zoomHalf = Math.max(iw, ih) / (2 * CALIB_ZOOM_FACTOR);
    const srcX = Math.max(0, zx - zoomHalf);
    const srcY = Math.max(0, zy - zoomHalf);
    const srcW = Math.min(iw - srcX, zoomHalf * 2);
    const srcH = Math.min(ih - srcY, zoomHalf * 2);
    const imgX = Math.min(iw, Math.max(0, srcX + (displayX / cw) * srcW));
    const imgY = Math.min(ih, Math.max(0, srcY + (displayY / ch) * srcH));

    if(S.calibCurrentKey){
      S.calibAnchors[S.calibCurrentKey] = [imgX, imgY];
      S.calibOrder.push(S.calibCurrentKey); // 记录顺序，支持撤销
    }
    // 移动到下一个特征
    _syncCalibPhase();
  } else {
    // ── 全图状态下点击 → 放大到该区域 ──
    const scale = Math.min(cw / iw, ch / ih) * 0.92;
    const dw = iw * scale, dh = ih * scale;
    const dx = (cw - dw) / 2, dy = (ch - dh) / 2;
    const imgX = Math.min(iw, Math.max(0, (displayX - dx) / scale));
    const imgY = Math.min(ih, Math.max(0, (displayY - dy) / scale));

    S.calibZoomCenter = [imgX, imgY];
    S.calibPhase = 'zoomed';
  }

  drawCalibrateView();
  updateCalibHint();
}

/** 滚轮缩放：放大状态下滚动鼠标滚轮继续调整放大倍数 */
function handleCalibrateWheel(e){
  if(S.calibPhase !== 'zoomed' || !S.calibZoomCenter) return;
  e.preventDefault();
  const step = e.deltaY < 0 ? 0.5 : -0.5; // 上滚放大，下滚缩小
  CALIB_ZOOM_FACTOR = Math.min(12, Math.max(1.5, CALIB_ZOOM_FACTOR + step));
  drawCalibrateView();
  updateCalibHint();
}

function startCalibrationUI(){
  show(D.calibrateWrap);
  hide(D.calibrateLoadErr);
  S.calibAnchors = {};
  _syncCalibPhase();
  D.btnCalibrateSubmit.disabled = true;
  D.calibrateImg.onload = () => {
    if(!S.imageWidth) S.imageWidth = D.calibrateImg.naturalWidth;
    if(!S.imageHeight) S.imageHeight = D.calibrateImg.naturalHeight;
    drawCalibrateView();
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
  if(S.photoBlobUrl){
    D.calibrateImg.src = S.photoBlobUrl;
  } else if(S.photoUrl){
    D.calibrateImg.src = S.photoUrl + '?t=' + Date.now();
  }
  updateCalibHint();
}

function updateCalibHint(){
  if(S.calibrated){
    D.calibrateHint.textContent = '✓ MediaPipe 自动标定已完成 — 请向下查看「低膜-人脸匹配校验」，核对红/绿/蓝线条与照片是否吻合';
    if(D.btnCalibrateSubmit) D.btnCalibrateSubmit.disabled = true;
    if(D.btnMediapipeDetect) D.btnMediapipeDetect.disabled = true;
    return;
  }
  const allDone = !!(S.calibAnchors.left_eye && S.calibAnchors.right_eye && S.calibAnchors.nose);
  if(allDone){
    D.calibrateHint.textContent = '✓ MediaPipe 已检测眼/鼻锚点，等待自动标定…';
    if(D.btnCalibrateSubmit) D.btnCalibrateSubmit.disabled = true;
    if(D.btnMediapipeDetect) D.btnMediapipeDetect.disabled = false;
    return;
  }
  D.calibrateHint.textContent = '等待 MediaPipe 检测…';
  if(D.btnCalibrateSubmit) D.btnCalibrateSubmit.disabled = true;
  if(D.btnMediapipeDetect) D.btnMediapipeDetect.disabled = false;
}

// ── 主画布点击 ──
if(D.calibrateMainCanvas) D.calibrateMainCanvas.addEventListener('click', handleCalibrateClick);

// ── 滚轮缩放（放大状态下用滚轮继续调整放大倍数）──
if(D.calibrateMainCanvas) D.calibrateMainCanvas.addEventListener('wheel', handleCalibrateWheel, {passive: false});

// ── 撤销：移除最后放置的锚点 ──
D.btnCalibrateUndo.onclick = function(){
  if(!S.calibOrder || S.calibOrder.length === 0) return;
  // 如果当前是放大状态，先退出到全图模式再撤销
  S.calibPhase = 'idle';
  S.calibZoomCenter = null;
  const lastKey = S.calibOrder.pop();
  delete S.calibAnchors[lastKey];
  _syncCalibPhase();
  drawCalibrateView();
  updateCalibHint();
};

// ── 重标：清空所有锚点 ──
D.btnCalibrateReset.onclick = function(){
  S.calibAnchors = {}; S.calibOrder = [];
  S.calibPhase = 'idle';
  S.calibZoomCenter = null;
  _syncCalibPhase();
  drawCalibrateView();
  updateCalibHint();
  D.btnStep1Next.disabled = true;
  S.calibrated = false;
};

// ── MediaPipe 自动标定（无手传 anchors）──
async function submitCalibrationAuto(){
  if(!S.photoName || !S.currentProject) throw new Error('缺少参考照片');
  if(D.btnCalibrateSubmit) D.btnCalibrateSubmit.disabled = true;
  const payload = {
    customer_id: S.customerId,
    project_id: S.currentProject.project_id,
    species: S.activeSpecies,
    photo_name: S.photoName,
    image_width: S.imageWidth,
    image_height: S.imageHeight,
  };
  const d = await apiPost('/api/portal/calibrate-template', payload);
  if(!d.ok) throw new Error(d.error||'MediaPipe 标定失败');
  await applyCalibrationResult(d);
}

async function applyCalibrationResult(d){
    S.templateParams = d.saved_params;
    S.detection = {method:'mediapipe', confidence:d.confidence, adjustments:d.adjustments};
    S.calibrated = true;
    S.calibratedBreed = d.breed || getCalibBreed();
    S.activeStyle = S.calibratedBreed;
    S.calibBreed = S.calibratedBreed;
    const gotPreview = applyCalibratePreview(d);
    D.btnStep1Next.disabled = false;
    addSavedStep('① MediaPipe 自动标定');
    const parts = [];
    if(d.spatial_calibration && d.spatial_calibration.affine_matrix) parts.push('空间仿射');
    if(d.adjustments && Object.keys(d.adjustments).length) parts.push('形状换算');
    const autoNote = parts.length ? '（'+parts.join(' + ')+'）' : '';
    setStatus(D.status1, gotPreview
      ? ('✅ MediaPipe 标定完成'+autoNote+' — 下方为底膜预览')
      : ('✅ MediaPipe 标定完成'+autoNote));
    showOverlayVerifyPanel();
  if(D.btnCalibrateSubmit) D.btnCalibrateSubmit.disabled = true;
  updateCalibHint();
}

// 保留按钮入口：重新触发 MediaPipe 标定（仍不传 anchors）
async function submitCalibration(){
  try {
    setStatus(D.status1, '⏳ 重新 MediaPipe 标定…');
    await submitCalibrationAuto();
  } catch(e){
    setStatus(D.status1, '❌ '+e.message, true);
    if(D.btnCalibrateSubmit) D.btnCalibrateSubmit.disabled = false;
    updateCalibHint();
  }
}


window.addEventListener('resize', () => { if(!D.calibrateWrap.classList.contains('hidden')) drawCalibrateView(); });

function fileToBase64(file){
  return new Promise((res,rej)=>{
    const r=new FileReader();
    r.onload=()=>res(r.result.split(',')[1]);
    r.onerror=rej;
    r.readAsDataURL(file);
  });
}

/* ── Step 3: Pomot（按钮驱动，暂不接 NL） ── */
async function runPomot(){
  if(!S.activeEmotion){ alert('请回第②步点选一个情绪'); return; }
  const btn = D.btnPomotRun;
  btn.disabled = true;
  setStatus(D.status3, '⏳ 生成中…');
  try {
    const d = await apiPost('/api/portal/pomot/round1', {
      species:S.activeSpecies, emotion:S.activeEmotion, breed:S.activeStyle,
      customer_id:S.customerId, project_id:S.currentProject?.project_id||'',
    });
    if(!d.ok) throw new Error(d.error||'失败');
    applyPomotResult(d);
    D.btnStep3Next.disabled = false;
    setStatus(D.status3, '✅ 管线完成（未写入客户资产库，第⑤步点「保存客户资料」）');
    addSavedStep('③ Pomot 生成（内存）');
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
  if(!S.lastBaked && !S.activeEmotion){ alert('请先生成管线（第③步）或选择情绪'); return; }
  if(!assertBreedCalibrated()) return;
  const ms = S.membraneStatus;
  if(ms && ms.action === 'regenerate'){
    alert(ms.warning + '\n\n请回第③步点击「生成表情」，再回来渲染。');
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
      emotion: S.activeEmotion,
      active_emotion: S.activeEmotion,
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
  if(!S.lastBaked && !S.activeEmotion){ alert('请先生成管线或选择情绪'); return; }
  if(!S.videoUrl){ alert('请先渲染 OpenCV 底膜视频（第④步）'); return; }
  D.btnExport.disabled = true;
  setStatus(D.status5, '⏳ 更新 04_Prompt…');
  try {
    const d = await apiPost('/api/portal/export', {
      baked: S.lastBaked, species: S.activeSpecies,
      breed: S.activeStyle, emotion: S.activeEmotion,
      active_emotion: S.activeEmotion,
      customer_id: S.customerId,
      project_id: S.currentProject?.project_id||'',
      action: (S.lastSplit && S.lastSplit.action) || '',
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
    if(D.delivPromptStatus) D.delivPromptStatus.textContent = '✓ 已更新 · ' + (S.lastPrompt.length || 0) + ' 字';
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
D.btnMediapipeDetect.onclick = submitCalibration;
D.btnStep1Next.onclick = () => goStep(2);
D.btnStep2Prev.onclick = () => goStep(1);
D.btnStep2Next.onclick = () => {
  if(!S.activeEmotion){ alert('请先点选一个情绪'); return; }
  goStep(3);
};
D.btnStep3Prev.onclick = () => goStep(2);
D.btnStep3Next.onclick = () => goStep(4);
D.btnStep4Prev.onclick = () => goStep(3);
D.btnStep4Next.onclick = () => goStep(5);
D.btnStep5Prev.onclick = () => goStep(4);
D.btnPomotRun.onclick = () => runPomot();
D.btnRenderVideo.onclick = renderVideo;
D.btnSaveAll.onclick = saveAll;
D.btnExport.onclick = doExport;
if(D.btnDownloadBundle) D.btnDownloadBundle.onclick = ()=>{
  if(!S.bundleZipUrl){ alert('请先点「保存客户资料」或「更新导出」'); return; }
  window.open(S.bundleZipUrl, '_blank');
};
if(D.btnCopyWanPos) D.btnCopyWanPos.onclick = ()=> copyText(S.lastWanPositive, D.btnCopyWanPos);
if(D.btnCopyWanNeg) D.btnCopyWanNeg.onclick = ()=> copyText(S.lastWanNegative, D.btnCopyWanNeg);
D.speciesSelect.onchange = async function(){
  S.activeSpecies = 'human';
  this.value = 'human';
  const lb = $('species-label');
  if(lb) lb.textContent = 'human';
  renderPresets('human');
  syncCalibBreedUI('human');
  if(!D.calibrateWrap.classList.contains('hidden') && !S.calibrated){
    S.calibAnchors = {}; S.calibOrder = [];
    S.calibPhase = 'idle'; S.calibZoomCenter = null;
    _syncCalibPhase();
    updateCalibHint(); drawCalibrateView();
  }
};

/* ── 低膜-人脸对齐诊断：视图切换 / 按钮 ── */
if(D.alignViewTabs){
  D.alignViewTabs.querySelectorAll('.align-view-tab').forEach(btn => {
    btn.onclick = () => setAlignmentView(btn.dataset.view || 'grid');
  });
}
if(D.btnOverlayConfirm){
  D.btnOverlayConfirm.onclick = () => {
    D.btnStep1Next.disabled = false;
    goStep(2);
  };
}
if(D.btnOverlayRetake){
  D.btnOverlayRetake.onclick = () => {
    /* 重置标定状态并隐藏叠加面板 + 调试面板 */
    S.calibAnchors = {}; S.calibOrder = [];
    S.calibPhase = 'idle'; S.calibZoomCenter = null;
    S.calibrated = false;
    D.btnStep1Next.disabled = true;
    if(D.overlayVerifyWrap) D.overlayVerifyWrap.classList.add('hidden');
    if(D.pipelineDebugWrap) D.pipelineDebugWrap.classList.add('hidden');
    if(D.calibrateWrap) D.calibrateWrap.classList.remove('hidden');
    _syncCalibPhase();
    drawCalibrateView();
    updateCalibHint();
  };
}

/* ── 管线调试按钮 ── */
if(D.btnDebugLoad){
  D.btnDebugLoad.onclick = loadPipelineDebug;
}

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
