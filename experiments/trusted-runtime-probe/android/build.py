from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess

parser=argparse.ArgumentParser();parser.add_argument('--online',action='store_true');args=parser.parse_args()
root=Path(__file__).resolve().parent;common=root.parent
subprocess.run(['python3',str(common/'build_bundle.py')],check=True)
assets=root/'app/src/main/assets';assets.mkdir(parents=True,exist_ok=True)
shutil.copyfile(common/'build/kernel-probe.js',assets/'kernel-probe.js');shutil.copyfile(common/'timer-adapter.js',assets/'timer-adapter.js')
env=os.environ.copy();env['JAVA_HOME']='/Applications/Android Studio.app/Contents/jbr/Contents/Home'
wrapper=common.parent/'android-origin-probe/gradlew';command=[str(wrapper),'-p',str(root),'--no-daemon',':app:assembleDebug',':app:lintDebug']
if not args.online:command.append('--offline')
subprocess.run(command,env=env,check=True)
apk=root/'app/build/outputs/apk/debug/app-debug.apk'
paths=[root/'settings.gradle',root/'build.gradle',root/'app/build.gradle',root/'gradle.properties',root/'app/src/main/AndroidManifest.xml',
       *root.glob('app/src/main/java/**/*.java'),root/'build.py',root/'run_probe.py']
meta={'common':json.loads((common/'build/bundle-metadata.json').read_text()),'apkSha256':hashlib.sha256(apk.read_bytes()).hexdigest(),
      'sources':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
out=root/'local-results';out.mkdir(exist_ok=True);(out/'build-metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
