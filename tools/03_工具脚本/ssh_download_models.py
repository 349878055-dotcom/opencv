#!/usr/bin/env python3
"""Download models and setup on AutoDL server (using /root/autodl-tmp/ for writable storage)."""
import paramiko

HOST = "connect.bjb1.seetacloud.com"
PORT = 44948
USER = "root"
PASS = "BN6kmLOhYX2B"
PYTHON = "/root/miniconda3/bin/python3"
DATA_DIR = "/root/autodl-tmp/comfyui"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

script = f"""#!/bin/bash
set -e
echo "=== Step 1: Create model directories on /root/autodl-tmp ==="
mkdir -p {DATA_DIR}/{{vae,text_encoders,unet,checkpoints,clip,clip_vision,controlnet,loras,upscale_models}}
echo "Directories: $(ls {DATA_DIR}/ | tr '\\n' ' ')"

echo ""
echo "=== Step 2: Install PyYAML ==="
{PYTHON} -m pip install pyyaml -q
echo "PyYAML installed"

echo ""
echo "=== Step 3: Create symlinks from ComfyUI/models to data disk ==="
cd /root/ComfyUI/models
for d in vae text_encoders unet checkpoints clip clip_vision controlnet loras upscale_models; do
  if [ -d "{DATA_DIR}/$d" ] && [ ! -L "$d" ]; then
    rm -rf "$d" 2>/dev/null
    ln -sf "{DATA_DIR}/$d" "$d"
    echo "  linked $d"
  fi
done
echo "Symlinks:"
ls -la /root/ComfyUI/models/vae /root/ComfyUI/models/text_encoders /root/ComfyUI/models/unet 2>/dev/null

echo ""
echo "=== Step 4: Download VAE (243MB) ==="
VAE_PATH={DATA_DIR}/vae/wan_2.1_vae.safetensors
if [ ! -f "$VAE_PATH" ] || [ "$(stat -c%s "$VAE_PATH" 2>/dev/null)" -lt 200000000 ]; then
  echo "Downloading VAE from hf-mirror..."
  curl -L --connect-timeout 30 --max-time 600 -o "$VAE_PATH" \\
    "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"
  echo "VAE done: $(ls -lh $VAE_PATH | awk '{{print $5}}')"
else
  echo "VAE cached: $(ls -lh $VAE_PATH | awk '{{print $5}}')"
fi

echo ""
echo "=== Step 5: Download CLIP (1.9GB) ==="
CLIP_PATH={DATA_DIR}/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors
if [ ! -f "$CLIP_PATH" ] || [ "$(stat -c%s "$CLIP_PATH" 2>/dev/null)" -lt 1800000000 ]; then
  echo "Downloading CLIP from hf-mirror..."
  curl -L --connect-timeout 30 --max-time 1800 -o "$CLIP_PATH" \\
    "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
  echo "CLIP done: $(ls -lh $CLIP_PATH | awk '{{print $5}}')"
else
  echo "CLIP cached: $(ls -lh $CLIP_PATH | awk '{{print $5}}')"
fi

echo ""
echo "=== Step 6: Download UNET (16GB) in background ==="
UNET_PATH={DATA_DIR}/unet/wan2.1-i2v-14b-480p-Q3_K_S.gguf
if [ ! -f "$UNET_PATH" ] || [ "$(stat -c%s "$UNET_PATH" 2>/dev/null)" -lt 15000000000 ]; then
  echo "Starting UNET download in background (nohup)..."
  nohup curl -L --connect-timeout 30 --max-time 86400 -o "$UNET_PATH" \\
    "https://hf-mirror.com/city96/wan2.1-i2v-14b-Q3_K_S-GGUF/resolve/main/wan2.1-i2v-14b-Q3_K_S.gguf" \\
    > /tmp/dl_unet.log 2>&1 &
  echo "UNET PID: $!"
  echo "Monitor: tail -f /tmp/dl_unet.log"
else
  echo "UNET cached: $(ls -lh $UNET_PATH | awk '{{print $5}}')"
fi

echo ""
echo "=== Step 7: Disk usage ==="
df -h /root/autodl-tmp/
echo "=== All steps done! ==="
"""

try:
    print("[*] Connecting to AutoDL server...")
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    print("[✓] Connected!\n")
    
    print("[*] Running setup (VAE + CLIP download, ~5-15 min)...")
    stdin, stdout, stderr = client.exec_command(script, timeout=3600)
    exit_code = stdout.channel.recv_exit_status()
    
    out = stdout.read().decode()
    if out:
        # Show only key info
        for line in out.split('\n'):
            if any(kw in line for kw in ['===', 'linked', 'Symlinks', 'VAE', 'CLIP', 'UNET', 'Disk', 'done', 'cached', 'PID', 'All steps']):
                print(line)
    
    err = stderr.read().decode()
    if err:
        for line in err.split('\n')[-5:]:
            if line.strip():
                print(f"  [stderr] {line}")
    
    if exit_code == 0:
        print("\n[✓] VAE + CLIP downloaded! UNET downloading in background.")
    else:
        print(f"\n[!] Exit code: {exit_code}")
    
    # Verify files
    print("\n[*] Verifying downloaded files...")
    stdin2, stdout2, stderr2 = client.exec_command(
        "ls -lh /root/autodl-tmp/comfyui/vae/ && ls -lh /root/autodl-tmp/comfyui/text_encoders/",
        timeout=10
    )
    print(stdout2.read().decode())

except Exception as e:
    print(f"[✗] Error: {e}")
finally:
    client.close()
    print("\n[*] Connection closed.")