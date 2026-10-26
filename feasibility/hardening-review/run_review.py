#!/usr/bin/env python3
"""Reproduce with fresh copied sources and owned fixtures; no builds/installations."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent

def run(argv, logfile):
    with logfile.open('w') as log:
        p = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = p.wait(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait(timeout=5)
            raise
    assert code == 0, f'failed ({code}); inspect {logfile}'

if __name__ == '__main__':
    output = subprocess.check_output([sys.executable,'-B',str(HERE/'prepare.py')],text=True,timeout=15)
    base = Path(output.strip())
    for worker, script in [('journal','test_followup.py'),('gate','run_tests.py'),('artifact','test_provider.py')]:
        run([sys.executable,'-B',str(base/worker/script)],base/(worker+'.log'))
    run([sys.executable,'-B',str(HERE/'checks.py'),str(base)],base/'checks.log')
    print(json.dumps({'passed':True,'evidence':str(base/'review-results.json'),'sources':str(base/'source-manifest.json')}))
