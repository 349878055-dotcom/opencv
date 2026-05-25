#!/usr/bin/env python3
"""Minimal: just start background downloads and disconnect ASAP."""
import paramiko

HOST = "connect.bjb1.seetacloud.com"
PORT = 44948
USER = "root"
PASS = "BN6kmLOhYX2B"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting...")
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    print("[✓] Connected!\n")

    # Single command: setup all downloads in background
    cmd = """
mkdir -p /root/autodl-tmp/comfyui/{vae,text_encoders,unet}
cd /root/ComfyUI/models
for d in vae text_encoders unet; do
  if [ -d "/root/autodl-tmp/comfyui/$d" ] && [ ! -L "$d" ]; then
    rm -rf "$d" 2>/dev/null; ln -sf "/root/autodl-tmp/comfyui/$d" "$d"
  fi
done
/root/miniconda3/bin/python3 -m pip install pyyaml -q 2>/dev/null

# VAE (243MB)
if [ ! -f /root/autodl-tmp/comfyui/vae/wan_2.1_vae.safetensors ]; then
  nohup curl -L --connect-timeout 30 --max-time 600 \\
    -o /root/autodl-tmp/comfyui/vae/wan_2.1_vae.safetensors \\
    "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors" \\
    > /tmp/dl_vae.log 2>&1 &
  echo "VAE_PID=$!"
fi

# CLIP (1.9GB)
if [ ! -f /root/autodl-tmp/comfyui/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors ]; then
  nohup curl -L --connect-timeout 30 --max-time 3600 \\
    -o /root/autodl-tmp/comfyui/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \\
    "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \\
    > /tmp/dl_clip.log 2>&1 &
  echo "CLIP_PID=$!"
fi

# UNET (16GB)
if [ ! -f /root/autodl-tmp/comfyui/unet/wan2.1-i2v-14b-Q3_K_S.gguf ]; then
  nohup curl -L --connect-timeout 30 --max-time 86400 \\
    -o /root/autodl-tmp/comfyui/unet/wan2.1-i2v-14b-Q3_K_S.gguf \\
    "https://hf-mirror.com/city96/wan2.1-i2v-14b-Q3_K_S-GGUF/resolve/main/wan2.1-i2v-14b-Q3_K_S.gguf" \\
    > /tmp/dl_unet.log 2>&1 &
  echo "UNET_PID=$!"
fi

echo "BACKGROUND_DOWNLOADS_STARTED"
ps aux | grep 'curl.*safetensors\|curl.*gguf\|curl.*wan' | grep -v grep
"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print(out)
    if err:
        print(f"  [stderr] {err[:500]}")

    print("\n[✓] Downloads started in background! You can shut down the server now.")
    print("    VAE (~1 min), CLIP (~5 min), UNET (~10 min)")
    print("    To check progress later, just reconnect and run:")
    print("      ls -lh /root/autodl-tmp/comfyui/vae/ /root/autodl-tmp/comfyui/text_encoders/ /root/autodl-tmp/comfyui/unet/")

except Exception as e:
    print(f"[✗] Error: {e}")
finally:
    client.close()
    print("[*] Disconnected.")