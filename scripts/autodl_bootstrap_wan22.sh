#!/usr/bin/env bash
# AutoDL 一键装机：ComfyUI + Wan 2.2 fp8 + VideoHelperSuite
# 用法（SSH 登录后）：
#   export AUTO_DL=1
#   bash autodl_bootstrap_wan22.sh
# 或从本仓库 scp 上去后执行。
set -euo pipefail

DATA_ROOT="${DATA_ROOT:-/root/autodl-tmp}"
COMFY_ROOT="${COMFY_ROOT:-$DATA_ROOT/ComfyUI}"
HF_BASE="${HF_BASE:-https://hf-mirror.com/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files}"
HF_BASE_21="${HF_BASE_21:-https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files}"
BUNDLE_DIR="$COMFY_ROOT/input/diffusion_bundle"

echo "==> 数据盘: $DATA_ROOT"
df -h "$DATA_ROOT" || true

mkdir -p "$DATA_ROOT"

# ── 1. ComfyUI ──────────────────────────────────────────────
if [[ -f "$COMFY_ROOT/main.py" ]]; then
  echo "==> ComfyUI 已存在: $COMFY_ROOT"
else
  echo "==> clone ComfyUI → $COMFY_ROOT"
  git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git "$COMFY_ROOT"
  pip install -r "$COMFY_ROOT/requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple -q
fi

cd "$COMFY_ROOT"
mkdir -p models/diffusion_models models/loras models/text_encoders models/vae
mkdir -p custom_nodes input/diffusion_bundle output user/default/workflows
mkdir -p "$DATA_ROOT/scripts"

# ── 2. 插件 ─────────────────────────────────────────────────
install_node() {
  local name="$1" url="$2"
  if [[ -d "custom_nodes/$name" ]]; then
    echo "    已有 $name"
  else
    echo "    clone $name"
    git clone --depth 1 "$url" "custom_nodes/$name"
  fi
}

echo "==> 安装 custom_nodes"
install_node ComfyUI-VideoHelperSuite https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
install_node ComfyUI-Manager https://github.com/ltdrdata/ComfyUI-Manager.git

# ── 3. 模型（存在则跳过）────────────────────────────────────
dl() {
  local dir="$1" file="$2" url="$3"
  local dest="models/$dir/$file"
  if [[ -f "$dest" ]]; then
    echo "    跳过（已有）$dest"
    return
  fi
  echo "    下载 $file ..."
  wget -c -O "$dest" "$url" || { rm -f "$dest"; echo "FAIL: $url"; exit 1; }
}

echo "==> 下载 Wan 2.2 模型（fp8，国内 hf-mirror）"
dl diffusion_models wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors \
  "$HF_BASE/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
dl diffusion_models wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors \
  "$HF_BASE/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
dl loras wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors \
  "$HF_BASE/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors"
dl loras wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors \
  "$HF_BASE/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"
dl vae wan_2.1_vae.safetensors \
  "$HF_BASE/vae/wan_2.1_vae.safetensors"
dl text_encoders umt5_xxl_fp8_e4m3fn_scaled.safetensors \
  "$HF_BASE_21/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"

# ── 4. 启动脚本 ─────────────────────────────────────────────
START="$DATA_ROOT/scripts/start_comfy.sh"
cat > "$START" << EOF
#!/usr/bin/env bash
cd "$COMFY_ROOT"
echo "ComfyUI → http://0.0.0.0:8188  （AutoDL 控制台添加自定义服务 8188）"
exec python main.py --listen 0.0.0.0 --port 8188
EOF
chmod +x "$START"

# ── 5. 自检 ─────────────────────────────────────────────────
echo ""
echo "==> 模型自检"
for f in \
  models/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors \
  models/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors \
  models/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors \
  models/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors \
  models/vae/wan_2.1_vae.safetensors \
  models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors
do
  if [[ -f "$COMFY_ROOT/$f" ]]; then
    ls -lh "$COMFY_ROOT/$f"
  else
    echo "MISSING: $f"
    exit 1
  fi
done

echo ""
echo "=============================================="
echo " 装机完成"
echo " ① 启动: bash $START"
echo " ② AutoDL 控制台 → 自定义服务 → 端口 8188"
echo " ③ 上传扩散包 → $BUNDLE_DIR"
echo " ④ 加载工作流 eye_wan22_fun_control_150.json（待导入）"
echo "=============================================="
