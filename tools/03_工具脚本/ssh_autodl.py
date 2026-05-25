#!/usr/bin/env python3
"""SSH into AutoDL cloud server and check status."""
import paramiko
import sys
import time

HOST = "connect.bjb1.seetacloud.com"
PORT = 44948
USER = "root"
PASS = "BN6kmLOhYX2B"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"[*] Connecting to {HOST}:{PORT}...")
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    print("[✓] Connected!\n")

    commands = [
        "hostname && whoami",
        "nvidia-smi --query-gpu=gpu_name,memory.total,memory.used --format=csv,noheader",
        "df -h /autodl-pub 2>/dev/null | tail -1 || echo '/autodl-pub not mounted'",
        "ls /root/ComfyUI/ 2>/dev/null | head -5 || echo 'ComfyUI not found'",
        "curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -m json.tool 2>/dev/null || echo 'Ollama not running'",
        "ls /autodl-pub/data/comfyui/ 2>/dev/null || echo 'comfyui dir not found'",
    ]

    for cmd in commands:
        print(f"$ {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print(out)
        if err:
            print(f"  [stderr] {err}")
        print()

except Exception as e:
    print(f"[✗] Error: {e}")
    sys.exit(1)
finally:
    client.close()
    print("[*] Connection closed.")
