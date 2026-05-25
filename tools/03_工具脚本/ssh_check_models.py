#!/usr/bin/env python3
"""Check if Wan models already exist on the A800 instance."""
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

    cmds = [
        "echo '=== Check Wan models in ComfyUI/models ==='",
        "find /root/ComfyUI/models -name '*wan*' -o -name '*Wan*' 2>/dev/null | head -20",
        "find /root/ComfyUI/models -name '*umt5*' 2>/dev/null | head -10",
        "find /root/ComfyUI/models -name '*.gguf' 2>/dev/null | head -10",
        "echo '=== Check autodl-fs (file storage) ==='",
        "ls -la /root/autodl-fs/ 2>/dev/null || echo '/root/autodl-fs not mounted'",
        "echo '=== Check autodl-pub/data for Wan models ==='",
        "find /autodl-pub/data -name '*wan*' -o -name '*Wan*' 2>/dev/null | head -20",
        "find /autodl-pub/data -name '*umt5*' 2>/dev/null | head -10",
        "echo '=== Check autodl-tmp ==='",
        "ls -la /root/autodl-tmp/comfyui/ 2>/dev/null || echo 'no comfyui in autodl-tmp'",
        "echo '=== Check disk space ==='",
        "df -h /root/autodl-tmp/ /root/autodl-fs/ 2>/dev/null",
    ]
    for cmd in cmds:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
        out = stdout.read().decode().strip()
        if out:
            print(out)
        err = stderr.read().decode().strip()
        if err:
            print(f"  [err] {err[:200]}")
        print()

except Exception as e:
    print(f"[✗] Error: {e}")
finally:
    client.close()