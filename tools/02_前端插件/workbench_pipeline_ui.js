/**
 * 能量工作台 · 交付链 JSON 展示（优先 pipeline_cache，否则浏览器预览版）
 * 与 gaze_engine/delivery_pipeline.py 同源；缓存由 build_workbench_pipeline_cache.py 生成
 */
(function (global) {
  const FC = 150;
  const KEYS = [
    "pupil_x", "pupil_y", "blink", "eyebrow", "pupil_scale", "iris_scale",
    "cornea_bulge", "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
  ];

  function slug(name) {
    return name.replace(/[^\w\u4e00-\u9fff]+/g, "_").replace(/^_|_$/g, "") || "preset";
  }

  function clamp(v) {
    return Math.max(0, Math.min(100, Math.round(Number(v))));
  }

  function lerp(a, b, t) {
    return a + (b - a) * (clamp(t) / 100);
  }

  /* —— 浏览器预览用曲线草稿（非出厂真值） —— */
  const MOTHER_DRAFT = {
    schema_version: "0.2-envelope-draft-preview",
    channel_tracks: {
      pupil_x: {
        keyframes: [
          { t: 0, v: 0, phase: "蓄力" },
          { t: 12, v: 0, phase: "蓄力", easing: "smoothstep" },
          { t: 14, v: 0, phase: "启动", easing: "linear" },
          { t: 17, v: 0.34, phase: "启动", easing: "ease_out_expo", _note: "过冲" },
          { t: 23, v: 0.3, phase: "启动", easing: "smoothstep", _note: "回弹" },
          { t: 55, v: 0.32, phase: "保持", easing: "linear" },
          { t: 120, v: 0.22, phase: "缓和", easing: "ease_in_quad" },
          { t: 149, v: 0, phase: "缓和", easing: "ease_in_quad" },
        ],
      },
      pupil_y: {
        keyframes: [
          { t: 0, v: 0, phase: "蓄力" },
          { t: 15, v: -0.07, phase: "启动", easing: "smoothstep" },
          { t: 20, v: -0.13, phase: "启动", easing: "ease_out_expo" },
          { t: 25, v: -0.11, phase: "启动", easing: "smoothstep" },
          { t: 55, v: -0.09, phase: "保持", easing: "linear" },
          { t: 149, v: 0, phase: "缓和" },
        ],
      },
      eyebrow: {
        keyframes: [
          { t: 0, v: 0.04, phase: "蓄力" },
          { t: 18, v: 0.14, phase: "蓄力", easing: "smoothstep" },
          { t: 32, v: 0.36, phase: "启动", easing: "smoothstep" },
          { t: 55, v: 0.4, phase: "保持", easing: "linear" },
          { t: 149, v: 0.06, phase: "缓和" },
        ],
      },
      blink: {
        keyframes: [
          { t: 0, v: 0, phase: "保持" },
          { t: 86, v: 0.12, phase: "保持", easing: "smoothstep" },
          { t: 90, v: 0, phase: "保持" },
          { t: 149, v: 0, phase: "缓和" },
        ],
      },
    },
  };

  function deepClone(o) {
    return JSON.parse(JSON.stringify(o));
  }

  function applyEase(u, mode) {
    u = Math.max(0, Math.min(1, u));
    if (mode === "linear") return u;
    if (mode === "smoothstep") return u * u * (3 - 2 * u);
    if (mode === "ease_out_expo") return u >= 1 ? 1 : 1 - Math.pow(2, -10 * u);
    if (mode === "ease_in_quad") return u * u;
    return u;
  }

  function interpolateTrack(kfs, channel) {
    const pts = kfs.map((k) => [k.t | 0, k.v, k]).sort((a, b) => a[0] - b[0]);
    const out = [];
    for (let t = 0; t < FC; t++) {
      if (t <= pts[0][0]) {
        out.push(pts[0][1]);
        continue;
      }
      if (t >= pts[pts.length - 1][0]) {
        out.push(pts[pts.length - 1][1]);
        continue;
      }
      for (let i = 0; i < pts.length - 1; i++) {
        const [t0, v0,] = pts[i];
        const [t1, v1, m1] = pts[i + 1];
        if (t0 <= t && t <= t1 && t1 !== t0) {
          const u = (t - t0) / (t1 - t0);
          const ease = m1.easing || "smoothstep";
          out.push(v0 + (v1 - v0) * applyEase(u, ease));
          break;
        }
      }
    }
    return out;
  }

  function compileDraftPreview(pkt, presetName) {
    const draft = deepClone(MOTHER_DRAFT);
    const m = pkt.macro;
    const energy = lerp(0.72, 1.18, m.power) * (m.push >= 50 ? 1 : 0.78);
    const timeShift = Math.round(lerp(3, -3, m.speed));
    const scale = (ch, v) => {
      const kfs = draft.channel_tracks[ch]?.keyframes;
      if (!kfs) return;
      kfs.forEach((k) => {
        if (k.t >= 14 && k.t <= 120) k.v = +(k.v * energy).toFixed(4);
        k.t = Math.max(0, Math.min(149, (k.t | 0) + (ch === "eyebrow" ? 0 : timeShift)));
      });
    };
    ["pupil_x", "pupil_y", "eyebrow"].forEach((ch) => scale(ch));
    draft.revision = "workbench-draft-preview:" + presetName;
    draft.slider_packet = pkt;
    draft.keys = KEYS;
    draft._comment = "浏览器预览草稿；出厂请以 pipeline_cache 为准";
    return draft;
  }

  function buildDenseFromDraft(draft) {
    const ch = {};
    KEYS.forEach((k) => {
      const kfs = draft.channel_tracks[k]?.keyframes;
      ch[k] = kfs ? interpolateTrack(kfs, k) : new Array(FC).fill(0);
    });
    return {
      schema: "dense-12x150",
      frame_count: FC,
      fps: 30,
      channels: ch,
      _note: "浏览器包络展开预览（出厂请以 pipeline_cache 为准）",
    };
  }

  function rewriteSaccade(series, speed, energy) {
    const zeta = lerp(0.72, 0.38, speed);
    const wn = lerp(9, 20, speed);
    const t0 = 12,
      t1 = 28;
    const out = series.slice();
    const target = out[t1];
    let x = out[t0],
      v = 0;
    const dt = 1 / 30;
    for (let t = t0; t <= t1; t++) {
      const err = target - x;
      const a = wn * wn * err - 2 * zeta * wn * v;
      v += a * dt;
      x += v * dt;
      out[t] = x * energy;
    }
    return out;
  }

  function addFixationNoise(px, py, pkt) {
    const seed = 97;
    const amp = 0.006 + ((100 - pkt.macro.steady) / 100) * 0.008;
    const hz = 12;
    for (let t = 25; t < 110; t++) {
      const w =
        Math.sin((2 * Math.PI * hz * t) / 30 + seed) * amp +
        0.35 * Math.sin((4.6 * Math.PI * hz * t) / 30) * amp;
      px[t] += w;
      py[t] += w * 1.05;
    }
  }

  function applyHumanPriorPreview(dense, pkt) {
    const ch = dense.channels;
    const m = pkt.macro;
    const energy = lerp(0.72, 1.18, m.power);
    ch.pupil_x = rewriteSaccade(ch.pupil_x, m.speed, energy);
    ch.pupil_y = rewriteSaccade(ch.pupil_y, m.speed, energy * 0.9);
    addFixationNoise(ch.pupil_x, ch.pupil_y, pkt);
    return {
      schema: "dense-12x150-human-prior-preview",
      frame_count: FC,
      channels: ch,
      _note: "真人默认律浏览器预览",
    };
  }

  function bakeSparse(draft, denseHp, pkt, report) {
    const phases = denseHp.channels.pupil_x.map((_, t) =>
      t < 14 ? "蓄力" : t < 25 ? "启动" : t < 120 ? "保持" : "缓和"
    );
    const tracks = {};
    KEYS.forEach((k) => {
      if (k === "blink" && draft.channel_tracks.blink) {
        tracks[k] = deepClone(draft.channel_tracks.blink);
        return;
      }
      const ser = denseHp.channels[k] || new Array(FC).fill(0);
      tracks[k] = {
        role: draft.channel_tracks[k]?.role || "",
        keyframes: ser.map((v, t) => ({
          t,
          v: +v.toFixed(6),
          phase: phases[t],
          easing: "linear",
        })),
      };
    });
    return {
      schema_version: "0.2-baked-human-prior-preview",
      _baked_dense: true,
      revision: "workbench-baked:" + (pkt.emotion || "custom"),
      slider_packet: pkt,
      channel_tracks: tracks,
      keys: KEYS,
      human_prior_report: report,
      _comment: "烘焙定稿预览；出厂请用 pipeline_cache",
    };
  }

  function summarizeDense(dense) {
    const sampleT = [0, 12, 15, 17, 21, 25, 55, 86, 120, 149];
    const ch = {};
    KEYS.forEach((k) => {
      const s = dense.channels[k] || [];
      if (!s.length) return;
      ch[k] = {
        min: +Math.min(...s).toFixed(5),
        max: +Math.max(...s).toFixed(5),
        samples: Object.fromEntries(sampleT.map((t) => [t, +(s[t] || 0).toFixed(5)])),
      };
    });
    return {
      schema: dense.schema,
      frame_count: dense.frame_count,
      channel_summary: ch,
      _note: "摘要；勾选「完整 JSON」查看 150 帧全量",
    };
  }

  function summarizeBaked(baked) {
    const px = baked.channel_tracks?.pupil_x?.keyframes || [];
    const n = px.length;
    return {
      schema_version: baked.schema_version,
      _baked_dense: baked._baked_dense,
      revision: baked.revision,
      keyframe_count_per_channel: n,
      pupil_x_samples: [0, 15, 21, 55, 149].map((t) => px[t]),
      blink_keyframes: baked.channel_tracks?.blink?.keyframes,
      human_prior_report: baked.human_prior_report,
      pulse_quality_report: baked.pulse_quality_report,
      _pulse_quality_fix_log: baked._pulse_quality_fix_log,
      _note: "摘要；完整 JSON 约 " + (n * KEYS.length) + " 点",
    };
  }

  function buildEnvelopePreview(pkt) {
    const m = pkt.macro;
    const peak = 0.25 + (m.power / 100) * 0.22;
    const env = [];
    for (let t = 0; t < FC; t++) {
      let e = 0;
      if (t < 15) e = peak * (t / 15);
      else if (t < 92) e = peak;
      else e = peak * Math.max(0, 1 - (t - 92) / 57);
      env.push(+e.toFixed(6));
    }
    return {
      schema: "energy-envelope-v1",
      frame_count: FC,
      fps: 30,
      peak_level: peak,
      envelope: env,
      _note: "浏览器近似包络",
    };
  }

  function runPreviewPipeline(pkt, presetName) {
    const draft = compileDraftPreview(pkt, presetName || "custom");
    const env = buildEnvelopePreview(pkt);
    const dense0 = buildDenseFromDraft(draft);
    const denseHp = applyHumanPriorPreview(deepClone(dense0), pkt);
    const report = {
      enabled: true,
      source: "browser-preview",
      speed: pkt.macro.speed,
      overshoot_hint: "见 pupil_x t15 vs t21",
    };
    const baked = bakeSparse(draft, denseHp, pkt, report);
    return {
      preset: presetName || "custom",
      _source: "browser-preview",
      stages: {
        "1_slider_packet": pkt,
        "2_energy_envelope": env,
        "3_dense_from_envelope": dense0,
        "4_dense_after_human_prior": denseHp,
        "4b_pulse_quality_report": { enabled: false, _note: "需 Python 缓存" },
        "5_baked_02_delivery": baked,
        "6_human_prior_report": report,
      },
    };
  }

  async function fetchPipeline(presetName, pkt) {
    const s = slug(presetName || "custom");
    try {
      const r = await fetch("/03_工具脚本/pipeline_cache/" + s + ".json", { cache: "no-cache" });
      if (r.ok) {
        const data = await r.json();
        data._source = "python-cache";
        return data;
      }
    } catch (e) {
      /* file:// 或未生成缓存 */
    }
    return runPreviewPipeline(pkt, presetName);
  }

  global.WorkbenchPipeline = {
    FC,
    KEYS,
    slug,
    fetchPipeline,
    runPreviewPipeline,
    summarizeDense,
    summarizeBaked,
  };
})(typeof window !== "undefined" ? window : globalThis);
