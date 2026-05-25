#!/usr/bin/env python3
"""Download models on AutoDL cloud server via SSH."""
import paramiko
import sys
import time

HOST = "connect.bjb1.seetacloud.com"
PORT = 44948
USER = "root"
PASS = "BN6kmLOhYX2B"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

def run(cmd, timeout=120):
    """Run command and print output."""
    print(f"\n$ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        # Show last 10 lines for long outputs
        lines = out.split('\n')
        if len(lines) > 10:
            print(f"... ({len(lines)} lines total)")
            print('\n'.join(lines[-10:]))
        else:
            print(out)
    if err:
        lines = err.split('\n')
        if len(lines) > 5:
            print(f"  [stderr] ... ({len(lines)} lines)")
            print('\n'.join(lines[-5:]))
        else:
            print(f"  [stderr] {err}")
    return out, err, exit_code

try:
    print("[*] Connecting to AutoDL server...")
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    print("[✓] Connected!\n")

    # Check ComfyUI model dirs
    run("ls /root/ComfyUI/models/ 2>/dev/null | head -20 || echo 'models dir not found'")

    # Check /autodl-pub/data structure
    run("ls -la /autodl-pub/data/ 2>/dev/null | head -10")

except Exception as e:
    print(f"[✗] Error: {e}")
finally:
    client.close()
    print("\n[*] Connection closed.")