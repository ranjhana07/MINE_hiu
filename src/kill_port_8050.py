import subprocess
import sys

try:
    out = subprocess.check_output(['netstat', '-ano', '-p', 'tcp'], universal_newlines=True)
except Exception as e:
    print('Error running netstat:', e)
    sys.exit(1)

pids = set()
for line in out.splitlines():
    if ':8050' in line:
        parts = line.split()
        if parts:
            pid = parts[-1]
            if pid.isdigit():
                pids.add(pid)

if not pids:
    print('NO PID on :8050')
    sys.exit(0)

for pid in pids:
    try:
        print(f'KILLING PID:{pid}')
        subprocess.check_call(['taskkill', '/F', '/PID', pid])
    except Exception as e:
        print(f'Failed to kill {pid}:', e)

print('DONE')
