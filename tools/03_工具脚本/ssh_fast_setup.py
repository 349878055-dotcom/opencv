#!/usr/bin/env python3
"""Fast setup: check existing models + start background downloads on AutoDL."""
import paramiko
import time

HOST = "connect.bjb1.seetacloud.com"
PORT = 44948
USER = "root"
PASS = "BN6kmLOhYX2B"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

def run(cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    return stdout.read().decode().strip(), stderr.read().decode().strip(), exit_code

try:
    print("[*] Connecting...")
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    print("[✓] Connected!\n")

    # === Check existing Wan models ===
    print("=== Step 1: Search for existing Wan models ===")
    cmds = [
        "find /autodl-pub /root -name '*wan*' -o -name '*Wan*' 2>/dev/null | head -20",
        "find /autodl-pub /root -name '*umt5*' 2>/dev/null | head -10",
        "find /autodl-pub -name '*.gguf' 2>/dev/null | head -10",
        "ls /root/ComfyUI/models/vae/ 2>/dev/null",
        "ls /root/ComfyUI/models/text_encoders/ 2>/dev/null",
        "ls /root/ComfyUI/models/unet/ 2>/dev/null",
    ]
    for cmd in cmds:
        out, err, code = run(cmd)
        if out:
            print(f"$ {cmd}")
            print(out[:2000])

    # === Step 2: Create model dirs + symlinks ===
    print("\n=== Step 2: Setup model directories ===")
    setup_script = """
    mkdir -p /root/autodl-tmp/comfyui/{vae,text_encoders,unet}
    cd /root/ComfyUI/models
    for d in vae text_encoders unet; do
      if [ -d "/root/autodl-tmp/comfyui/$d" ] && [ ! -L "$d" ]; then
        rm -rf "$d" 2>/dev/null; ln -sf "/root/autodl-tmp/comfyui/$d" "$d"
        echo "linked $d"
      fi
    done
    ls -la /root/ComfyUI/models/vae /root/ComfyUI/models/text_encoders /root/ComfyUI/models/unet 2>/dev/null
    """
    out, err, code = run(setup_script)
    print(out)
    if err:
        print(f"  [err] {err[:500]}")

    # === Step 3: Start background downloads (fast: run nohup + disown) ===
    print("\n=== Step 3: Start background downloads ===")
    dl_script = """
    cd /root/autodl-tmp/comfyui
    PY=/root/miniconda3/bin/python3
    
    # Install PyYAML (quick)
    $PY -m pip install pyyaml -q 2>/dev/null && echo "pyyaml ok"
    
    # VAE (243MB - fast)
    if [ ! -f vae/wan_2.1_vae.safetensors ]; then
      echo "DL_VAE: starting..."
      nohup curl -L --connect-timeout 30 --max-time 600 \\
        -o vae/wan_2.1_vae.safetensors \\
        "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors" \\
        > /tmp/dl_vae.log 2>&1 &
      echo "DL_VAE pid=$!"
    else
      echo "VAE exists: $(ls -lh vae/wan_2.1_vae.safetensors | awk '{print $5}')"
    fi
    
    # CLIP (1.9GB - medium)
    if [ ! -f text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors ]; then
      echo "DL_CLIP: starting..."
      nohup curl -L --connect-timeout 30 --max-time 3600 \\
        -o text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \\
        "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \\
        > /tmp/dl_clip.log 2>&1 &
      echo "DL_CLIP pid=$!"
    else
      echo "CLIP exists: $(ls -lh text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors | awk '{print $5}')"
    fi
    
    # UNET (16GB - slow, background)
    if [ ! -f unet/wan2.1-i2v-14b-480p-Q3_K_S.gguf ]; then
      echo "DL_UNET: starting..."
      nohup curl -L --connect-timeout 30 --max-time 86400 \\
        -o unet/wan2.1-i2v-14b-Q3_K_S.gguf \\
        "https://hf-mirror.com/city96/wan2.1-i2v-14b-Q3_K_S-GGUF/resolve/main/wan2.1-i2v-14b-Q3_K_S.gguf" \\
        > /tmp/dl_unet.log 2>&1 &
      echo "DL_UNET pid=$!"
    else
      echo "UNET exists: $(ls -lh unet/wan2.1-i2v-14b-480p-Q3_K_S.gguf | awk '{print $5}')"
    fi
    
    echo "---"
    echo "dl processes:"
    ps aux | grep 'curl.*wan\|curl.*safetensors' | grep -v grep || echo "(none running)"
    """
    out, err, code = run(dl_script, timeout=60)
    print(out)
    if err:
        print(f"  [err] {err[:500]}")

    # === Step 4: Check all running downloads ===
    print("\n=== Step 4: Active downloads ===")
    out, err, code = run("ps aux | grep 'curl.*/tmp/dl_' | grep -v grep; echo '---'; ls -lh /tmp/dl_*.log 2>/dev/null")
    print(out)

    print("\n=== DONE ===")
    print("Downloads running in background. To check later:")
    print("  python3 -c \"import paramiko; c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy()); c.connect('connect.bjb1.seetacloud.com', 44948, 'root', 'BN6kmLOhYX2B'); stdin,stdout,stderr=c.exec_command('ls -lh /root/autodl-tmp/comfyui/vae/ /root/autodl-tmp/comfyui/text_encoders/ /root/autodl-tmp/comfyui/unet/ 2>/dev/null'); print(stdout.read().decode()); c.close()\"")

except Exception as e:
    print(f"[✗] Error: {e}")
finally:
    client.close()
    print("\n[*] Disconnected (downloads continue on server).")