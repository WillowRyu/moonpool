"""Launch/export only the separate T26 app on the retained owned simulator."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

parser=argparse.ArgumentParser()
parser.add_argument('--profile',choices=['all-frames','main-only'],required=True)
parser.add_argument('--run',choices=['first','repeat'],required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parent
ownership=json.loads((root/'local-results/ownership.json').read_text())
owned=ownership['owned'];assert owned not in [d['id'] for d in ownership['others']]
devices=json.loads(subprocess.check_output(['xcrun','simctl','list','devices','available','--json']))['devices']
device=next(d for ds in devices.values() for d in ds if d['udid']==owned)
assert device['name']==ownership['name'] and device['state']=='Booted'
package='org.moonpool.iosmessageprobe'
def command(*parts,check=True):
    return subprocess.run(['xcrun','simctl',*parts],capture_output=True,text=True,timeout=25,check=check)
metadata=json.loads((root/'build/build-metadata.json').read_text())
for name,sha in metadata['sources'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
installed=Path(command('get_app_container',owned,package,'app').stdout.strip())
assert hashlib.sha256((installed/'MessageProbe').read_bytes()).hexdigest()==metadata['executableSha256']
command('terminate',owned,package,check=False)
data=Path(command('get_app_container',owned,package,'data').stdout.strip())
report_file=data/'Documents/report.json';report_file.unlink(missing_ok=True)
command('launch',owned,package,'--profile',args.profile,'--run',args.run)
deadline=time.monotonic()+210
while time.monotonic()<deadline:
    if report_file.exists():
        try:
            report=json.loads(report_file.read_text())
            if report.get('complete') and report['profile']==args.profile and report['run']==args.run:
                report['buildMetadata']=metadata;args.output.parent.mkdir(parents=True,exist_ok=True)
                args.output.write_text(json.dumps(report,indent=2)+'\n')
                print(f"{args.profile}/{args.run}: {len(report['samples'])} snapshots exported",flush=True)
                break
        except json.JSONDecodeError:pass
    time.sleep(0.4)
else:raise SystemExit('No completed T26 report before deadline; inspect only owned probe state.')
