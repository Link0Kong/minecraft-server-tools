import sys
import paramiko

host = "115.29.161.32"
user = "mcpanel"
pwd = "{{MCPANEL_PASSWORD}}"
cmd = sys.argv[1] if len(sys.argv) > 1 else "echo hi"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect(host, username=user, password=pwd, timeout=15, banner_timeout=20, auth_timeout=20)
except Exception as e:
    print("SSH_FAIL:", type(e).__name__, e)
    sys.exit(1)

stdin, stdout, stderr = c.exec_command(cmd, timeout=60)
out = stdout.read().decode("utf-8", "replace")
err = stderr.read().decode("utf-8", "replace")
print(out)
if err.strip():
    print("[stderr]", err)
c.close()
