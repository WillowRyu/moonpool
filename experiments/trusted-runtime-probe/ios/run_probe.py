from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time

parser=argparse.ArgumentParser();parser.add_argument('--run',choices=['first','repeat'],required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
root=Path(__file__).resolve().parent;owner=json.loads((root.parent/'local-results/ios-ownership.json').read_text());owned=owner['owned']
assert owned not in [d['id'] for d in owner['others']]
def command(*args,check=True):return subprocess.run(['xcrun','simctl',*args],capture_output=True,text=True,check=check,timeout=25)
devices=json.loads(command('list','devices','available','--json').stdout)['devices'];device=next(d for ds in devices.values() for d in ds if d['udid']==owned)
assert device['state']=='Booted' and device['name']==owner['name']
package='org.moonpool.iosruntimeprobe';meta=json.loads((root/'build/build-metadata.json').read_text())
installed=Path(command('get_app_container',owned,package,'app').stdout.strip());assert hashlib.sha256((installed/'RuntimeProbe').read_bytes()).hexdigest()==meta['executableSha256']
for name,sha in meta['sources'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha
command('terminate',owned,package,check=False)
data=Path(command('get_app_container',owned,package,'data').stdout.strip());report=data/'Documents/report.json';report.unlink(missing_ok=True)
command('launch',owned,package,'--run',args.run)
deadline=time.monotonic()+90
while time.monotonic()<deadline:
 if report.exists():
  value=json.loads(report.read_text())
  if value.get('complete') and value['run']==args.run:
   value['buildMetadata']=meta;args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(value,indent=2)+'\n');print('iOS/'+args.run+': 3 runtime owners exported');break
 time.sleep(.4)
else:raise SystemExit('No runtime probe report')
