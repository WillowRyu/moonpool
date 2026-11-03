"""Build research apps with installed toolchains; source and artifact fingerprints."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
from fixture import create_certificates
from verify import expected_cases

ROOT=Path(__file__).resolve().parent
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def sources(platform):
    paths=[ROOT/'page.html',ROOT/'build.py',*(ROOT/platform).rglob('*')]
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths) if p.is_file() and not any(x in {'build','.gradle'} for x in p.relative_to(ROOT).parts)}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('platform',choices=['android','ios']); args=parser.parse_args()
    assets=ROOT/'build/assets'; assets.mkdir(parents=True,exist_ok=True)
    ids={o:'com.example.cookieprobe.'+o for o in ['a','b','h','u']}
    origins={o:'https://mp-'+base64.b32encode(hashlib.sha256(i.encode()).digest()).decode().lower().rstrip('=')+'.invalid' for o,i in ids.items()}
    (assets/'config.json').write_text(json.dumps({'ids':ids,'androidOrigins':origins,'cases':expected_cases()},indent=2)+'\n')
    shutil.copy2(ROOT/'page.html',assets/'page.html')
    tls=ROOT/'local-results/tls'; create_certificates(tls)
    metadata={'sources':sources(args.platform),'fixtureConfigSha256':sha(assets/'config.json'),'caSha256':sha(tls/'ca.pem')}
    if args.platform=='android':
        res=ROOT/'build/res/raw'; res.mkdir(parents=True,exist_ok=True); shutil.copy2(tls/'ca.pem',res/'probe_ca.pem')
        env=os.environ.copy(); env.setdefault('JAVA_HOME','/Applications/Android Studio.app/Contents/jbr/Contents/Home'); env.setdefault('ANDROID_HOME',str(Path.home()/'Library/Android/sdk'))
        wrapper=ROOT.parent/'android-origin-probe/gradlew'
        subprocess.run([str(wrapper),'-p',str(ROOT/'android'),'--no-daemon',':app:assembleDebug',':app:lintDebug'],env=env,check=True)
        metadata['apkSha256']=sha(ROOT/'android/app/build/outputs/apk/debug/app-debug.apk')
        metadata['wrapperSha256']=sha(wrapper)
    else:
        app=ROOT/'build/CookieSuppressionProbe.app'; app.mkdir(parents=True,exist_ok=True)
        shutil.copytree(assets,app/'Fixtures',dirs_exist_ok=True)
        info={'CFBundleExecutable':'CookieSuppressionProbe','CFBundleIdentifier':'org.moonpool.ioscookiesuppressionprobe',
              'CFBundleName':'Cookie Suppression Probe','CFBundlePackageType':'APPL','CFBundleVersion':'1','CFBundleShortVersionString':'0.0.1',
              'MinimumOSVersion':'17.0','UIDeviceFamily':[1,2],'UILaunchScreen':{},'LSRequiresIPhoneOS':True}
        (app/'Info.plist').write_bytes(plistlib.dumps(info))
        sdk=subprocess.check_output(['xcrun','--sdk','iphonesimulator','--show-sdk-path'],text=True).strip()
        subprocess.run(['xcrun','--sdk','iphonesimulator','swiftc','-swift-version','5','-parse-as-library','-sdk',sdk,'-target','arm64-apple-ios17.0-simulator','-framework','UIKit','-framework','WebKit',str(ROOT/'ios/Probe.swift'),'-o',str(app/'CookieSuppressionProbe')],check=True)
        subprocess.run(['codesign','--force','--sign','-',str(app)],check=True)
        subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
        metadata['executableSha256']=sha(app/'CookieSuppressionProbe'); metadata['signatureSha256']=sha(app/'_CodeSignature/CodeResources')
        metadata['xcode']=subprocess.check_output(['xcodebuild','-version'],text=True).strip()
        metadata['sdk']=subprocess.check_output(['xcrun','--sdk','iphonesimulator','--show-sdk-version'],text=True).strip()
    (ROOT/'local-results'/f'{args.platform}-build.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(args.platform+' build and source fingerprints saved.')

if __name__=='__main__': main()
