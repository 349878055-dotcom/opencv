#!/usr/bin/env python3
"""Find correct Python paths on AutoDL server."""
import paramiko

HOST = "connect.bjb1.seetacloud.com"
PORT = 44948
USER = "root"
PASS = "BN6kmLOhYX2B"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

commands = [
    "which python3 || which python",
    "ls /root/miniconda3/bin/python* 2>/dev/null || echo 'no miniconda3'",
    "ls /opt/conda/bin/python* 2>/dev/null || echo 'no /opt/conda'",
    "ls /usr/local/bin/python* 2>/dev/null | head -5",
    "find / -maxdepth 3 -name 'python3' -type f 2>/dev/null | head -5",
    "/root/miniconda3/bin/python3 --version 2>/dev/null || echo 'miniconda3 python not found'",
]

try:
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    for cmd in commands:
        print(f"$ {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print(out)
        if err:
            print(f"  {err}")
        print()
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()