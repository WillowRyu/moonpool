from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time

parser=argparse.ArgumentParser();parser.add_argument('--run',choices=['first','repeat'],required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
root=Path(__file__).resolve().parent;own=json.loads((root.parent/'local-results/android-ownership.json').read_text());serial=own['owned']
assert serial.startswith('emulator-') and serial not in [d['serial'] for d in own['protected']]
def command(*parts,check=True):return subprocess.run(['adb','-s',serial,*parts],capture_output=True,text=True,timeout=20,check=check)
assert command('emu','avd','name').stdout.splitlines()[0]==own['avd']
package='org.moonpool.runtimeprobe';meta=json.loads((root/'local-results/build-metadata.json').read_text())
for name,sha in meta['sources'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
installed=command('shell','pm','path',package).stdout.strip().removeprefix('package:');assert installed.startswith('/data/app/')
assert command('shell','sha256sum',installed).stdout.split()[0]==meta['apkSha256']
command('shell','am','force-stop',package);command('shell','run-as',package,'rm','-f','files/report.json')
command('shell','am','start','-n',package+'/.RuntimeActivity','--es','run',args.run)
deadline=time.monotonic()+120
while time.monotonic()<deadline:
 r=command('exec-out','run-as',package,'cat','files/report.json',check=False)
 if r.returncode==0:
  try:
   report=json.loads(r.stdout)
   if report.get('complete') and report['run']==args.run:
    report['buildMetadata']=meta;args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print('Android/'+args.run+': '+str(len(report['samples']))+' runtime owners exported');break
  except json.JSONDecodeError:pass
 time.sleep(.4)
else:raise SystemExit('No T27 Android report')
