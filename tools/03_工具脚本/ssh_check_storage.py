#!/usr/bin/env python3
"""Check writable paths on AutoDL server."""
import paramiko

HOST = "connect.bjb1.seetacloud.com"
PORT = 44948
USER = "root"
PASS = "BN6kmLOhYX2B"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

commands = [
    "df -h | grep -v tmpfs | grep -v overlay",
    "mount | grep -E '(autodl|data)'",
    "lsblk | head -20",
    "ls -la /root/ | head -20",
    "ls -la /root/autodl-tmp/ 2>/dev/null || echo 'no autodl-tmp'",
    "df -h /root/autodl-tmp 2>/dev/null || echo 'autodl-tmp not mounted'",
    "df -h /root 2>/dev/null",
    "find / -name 'autodl-*' -maxdepth 2 -type d 2>/dev/null | head -10",
    "cat /etc/fstab 2>/dev/null | head -20",
    "touch /root/test_write && echo 'root writable' && rm /root/test_write",
    "touch /autodl-pub/test_write 2>&1 || echo 'autodl-pub NOT writable'",
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