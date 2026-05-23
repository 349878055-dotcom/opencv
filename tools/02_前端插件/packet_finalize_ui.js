/**
 * 滑杆禁区 · 与 slider_bounds.py 同源（tools/slider_forbidden_bounds.js）
 */
(function (global) {
  const RULES = global.SLIDER_FORBIDDEN_BOUNDS || { presets: {}, global_fixes: [], dead_zone: {} };
  const MACRO_IDS = ["push", "power", "speed", "steady", "grip", "outro"];

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, Math.round(Number(v))));
  }

  function inDeadZone(macro, dz) {
    const lo = dz.macro_low ?? 42;
    const hi = dz.macro_high ?? 58;
    return MACRO_IDS.every(k => macro[k] >= lo && macro[k] <= hi);
  }

  function matchWhen(macro, hold, when) {
    for (const [k, spec] of Object.entries(when || {})) {
      if (k === "hold_seg.shape" && hold.shape !== spec) return false;
      if (k === "hold_seg.shape_not" && hold.shape === spec) return false;
      if (k === "hold_seg.pulse_rate_min" && hold.pulse_rate < spec) return false;
      if (k === "hold_seg.pulse_depth_min" && hold.pulse_depth < spec) return false;
      if (k === "macro.speed_min" && macro.speed < spec) return false;
      if (k === "macro.power_max" && macro.power > spec) return false;
      if (k === "macro.power_min" && macro.power < spec) return false;
      if (k === "macro.steady_max" && macro.steady > spec) return false;
      if (k === "macro.steady_min" && macro.steady < spec) return false;
      if (k === "macro.grip_max" && macro.grip > spec) return false;
      if (k === "macro.push_max" && macro.push > spec) return false;
      if (k === "macro.outro_min" && macro.outro < spec) return false;
    }
    return true;
  }

  function applyPresetBox(macro, hold, preset, box, fixes) {
    MACRO_IDS.forEach(key => {
      const lo = (box.macro_min || {})[key] ?? 0;
      const hi = (box.macro_max || {})[key] ?? 100;
      if (macro[key] < lo) {
        fixes.push(preset + ": macro." + key + " " + macro[key] + "→" + lo);
        macro[key] = lo;
      } else if (macro[key] > hi) {
        fixes.push(preset + ": macro." + key + " " + macro[key] + "→" + hi);
        macro[key] = hi;
      }
    });
    const allowed = box.allowed_shapes || [];
    if (allowed.length && !allowed.includes(hold.shape)) {
      const def = allowed[0];
      fixes.push(preset + ": shape " + hold.shape + "→" + def);
      hold.shape = def;
    }
    ["pulse_rate", "pulse_depth", "swell"].forEach(k => {
      const lo = (box.hold_seg_min || {})[k] ?? 0;
      const hi = (box.hold_seg_max || {})[k] ?? 100;
      if (hold[k] < lo) { fixes.push(preset + ": " + k + "→" + lo); hold[k] = lo; }
      if (hold[k] > hi) { fixes.push(preset + ": " + k + "→" + hi); hold[k] = hi; }
    });
  }

  function applyGlobalFixes(macro, hold, box, fixes) {
    (RULES.global_fixes || []).forEach(rule => {
      if (rule.dead_zone) return;
      if (!matchWhen(macro, hold, rule.when)) return;
      const id = rule.id || "fix";
      if (rule.set) {
        Object.entries(rule.set).forEach(([key, val]) => {
          if (!key.startsWith("hold_seg.")) return;
          const f = key.split(".")[1];
          hold[f] = f === "shape" ? val : clamp(val, 0, 100);
          fixes.push(id + ": " + key);
        });
      }
      if (rule.set_macro_min) {
        Object.entries(rule.set_macro_min).forEach(([key, val]) => {
          let floor = clamp(val, 0, 100);
          if (box.macro_min && box.macro_min[key] != null) floor = Math.max(floor, box.macro_min[key]);
          if (macro[key] < floor) {
            fixes.push(id + ": macro." + key + "→" + floor);
            macro[key] = floor;
          }
        });
      }
      if (rule.set_macro_max) {
        Object.entries(rule.set_macro_max).forEach(([key, val]) => {
          let ceil = clamp(val, 0, 100);
          if (box.macro_max && box.macro_max[key] != null) ceil = Math.min(ceil, box.macro_max[key]);
          if (macro[key] > ceil) {
            fixes.push(id + ": macro." + key + "→" + ceil);
            macro[key] = ceil;
          }
        });
      }
    });
  }

  function finalize(macro, hold_seg, activePreset, presets) {
    const fixes = [];
    const m = { ...macro };
    const h = { ...hold_seg };
    const box = (RULES.presets || {})[activePreset];

    if (activePreset && box) {
      applyPresetBox(m, h, activePreset, box, fixes);
    }
    applyGlobalFixes(m, h, box || {}, fixes);

    const dz = RULES.dead_zone || {};
    if (activePreset && presets[activePreset] && inDeadZone(m, dz)) {
      const center = presets[activePreset].macro;
      MACRO_IDS.forEach(k => {
        if (center[k] != null && m[k] !== center[k]) {
          fixes.push("G1: macro." + k + " " + m[k] + "→" + center[k]);
          m[k] = center[k];
        }
      });
    }
    return { macro: m, hold_seg: h, fixes };
  }

  global.PacketFinalize = { finalize, RULES };
})(typeof window !== "undefined" ? window : globalThis);
