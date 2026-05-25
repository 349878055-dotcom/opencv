#!/usr/bin/env python3
"""Check status and restart missing downloads."""
import paramiko

HOST = "connect.bjb1.seetacloud.com"
PORT = 44948
USER = "root"
PASS = "BN6kmLOhYX2B"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    print("[✓] Connected\n")

    # Check current state
    cmds = [
        "echo '=== Running DLs ===' && ps aux | grep curl | grep -v grep || echo '(none)'",
        "echo '=== File sizes ===' && ls -lh /root/autodl-tmp/comfyui/vae/ /root/autodl-tmp/comfyui/text_encoders/ /root/autodl-tmp/comfyui/unet/ 2>/dev/null",
        "echo '=== Symlinks ===' && ls -la /root/ComfyUI/models/vae /root/ComfyUI/models/text_encoders /root/ComfyUI/models/unet 2>/dev/null",
        "echo '=== Disk ===' && df -h /root/autodl-tmp/",
    ]
    for cmd in cmds:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err.strip():
            print(f"  [err] {err[:300]}")

except Exception as e:
    print(f"[✗] Error: {e}")
finally:
    client.close()