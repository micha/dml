#!/usr/bin/env python3
"""Fresh targeted reproduction, no unchanged artifact-suite replay or tool install."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

HERE=Path(__file__).resolve().parent

def run(argv,logfile):
    with logfile.open('w') as log:
        p=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=p.wait(timeout=240)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5);raise
    assert code==0,f'failed ({code}); inspect {logfile}'

if __name__=='__main__':
    if len(sys.argv)>1:base=Path(sys.argv[1]).resolve()
    else:
        out=subprocess.check_output([sys.executable,'-B',str(HERE/'followup_prepare.py')],text=True,timeout=615)
        base=Path(out.strip())
    assert base.is_relative_to(HERE/'runtime/followup')
    run([sys.executable,'-B',str(base/'gate/run_tests.py')],base/'gate-regression.log')
    run([sys.executable,'-B',str(HERE/'followup_checks.py'),str(base)],base/'review-checks.log')
    print(json.dumps({'passed':True,'base':str(base),'results':str(base/'followup-review-results.json')}))
