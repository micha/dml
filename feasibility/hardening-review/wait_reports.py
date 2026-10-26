#!/usr/bin/env python3
"""Read-only bounded marker wait; never signals, delegates, or resumes workers."""
import argparse
import json
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--seconds',type=int,default=900)
    a=p.parse_args()
    assert 0<=a.seconds<=900
    start=time.monotonic()
    while True:
        status={name:(HERE.parent/name/'done.json').exists() and (HERE.parent/name/'report.md').exists()
                for name in ('journal','gate','artifact')}
        if all(status.values()) or time.monotonic()-start>=a.seconds:
            print(json.dumps({'reports_and_markers':status,'waited_seconds':round(time.monotonic()-start,2)}))
            break
        time.sleep(min(15,max(0,a.seconds-(time.monotonic()-start))))
