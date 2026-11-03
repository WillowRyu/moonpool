"""Build only the admission research apps with existing tools and a scoped test CA."""
import argparse,base64,hashlib,json,os,plistlib,shutil,subprocess
from pathlib import Path
from fixture import create_certificates

ROOT=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('platform',choices=['android','ios']);args=p.parse_args()
    assets=ROOT/'build/assets';assets.mkdir(parents=True,exist_ok=True)
    cases=json.loads((ROOT/'presence_cases.json').read_text())
    ids={c['id']:'com.example.admission.'+c['id'] for c in cases}
    origins={key:'https://mp-'+base64.b32encode(hashlib.sha256(value.encode()).digest()).decode().lower().rstrip('=')+'.invalid' for key,value in ids.items()}
    (assets/'config.json').write_text(json.dumps({'cases':cases,'ids':ids,'origins':origins},indent=2)+'\n')
    shutil.copy2(ROOT/'storage.html',assets/'storage.html')
    tls=ROOT/'local-results/tls';create_certificates(tls)
    paths=[ROOT/'build.py',ROOT/'storage.html',ROOT/'presence_cases.json',ROOT/'gate_cases.json',*(ROOT/args.platform).rglob('*')]
    metadata={'sources':{str(path.relative_to(ROOT)):sha(path) for path in sorted(paths) if path.is_file() and not any(x in {'build','.gradle'} for x in path.relative_to(ROOT).parts)},
              'fixtureConfigSha256':sha(assets/'config.json'),'caSha256':sha(tls/'ca.pem')}
    if args.platform=='android':
        res=ROOT/'build/res/raw';res.mkdir(parents=True,exist_ok=True);shutil.copy2(tls/'ca.pem',res/'probe_ca.pem')
        env=os.environ.copy();env.setdefault('JAVA_HOME','/Applications/Android Studio.app/Contents/jbr/Contents/Home');env.setdefault('ANDROID_HOME',str(Path.home()/'Library/Android/sdk'))
        wrapper=ROOT.parent/'android-origin-probe/gradlew'
        subprocess.run([str(wrapper),'-p',str(ROOT/'android'),'--no-daemon',':app:assembleDebug',':app:lintDebug'],env=env,check=True)
        metadata['apkSha256']=sha(ROOT/'android/app/build/outputs/apk/debug/app-debug.apk');metadata['wrapperSha256']=sha(wrapper)
    else:
        app=ROOT/'build/CookieAdmissionProbe.app';app.mkdir(parents=True,exist_ok=True);shutil.copytree(assets,app/'Fixtures',dirs_exist_ok=True)
        info={'CFBundleExecutable':'CookieAdmissionProbe','CFBundleIdentifier':'org.moonpool.ioscookieadmissionprobe','CFBundleName':'Cookie Admission Probe','CFBundlePackageType':'APPL','CFBundleVersion':'1','CFBundleShortVersionString':'0.0.1','MinimumOSVersion':'17.0','UIDeviceFamily':[1,2],'UILaunchScreen':{},'LSRequiresIPhoneOS':True}
        (app/'Info.plist').write_bytes(plistlib.dumps(info))
        sdk=subprocess.check_output(['xcrun','--sdk','iphonesimulator','--show-sdk-path'],text=True).strip()
        subprocess.run(['xcrun','--sdk','iphonesimulator','swiftc','-swift-version','5','-parse-as-library','-sdk',sdk,'-target','arm64-apple-ios17.0-simulator','-framework','UIKit','-framework','WebKit',*[str(ROOT/'ios'/file) for file in ['AdmissionGate.swift','GateCases.swift','Probe.swift']],'-o',str(app/'CookieAdmissionProbe')],check=True)
        subprocess.run(['codesign','--force','--sign','-',str(app)],check=True);subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
        metadata['executableSha256']=sha(app/'CookieAdmissionProbe');metadata['signatureSha256']=sha(app/'_CodeSignature/CodeResources')
        metadata['xcode']=subprocess.check_output(['xcodebuild','-version'],text=True).strip();metadata['sdk']=subprocess.check_output(['xcrun','--sdk','iphonesimulator','--show-sdk-version'],text=True).strip()
    (ROOT/'local-results'/f'{args.platform}-build.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(args.platform+' admission artifact and source hashes recorded.')

if __name__=='__main__':main()
