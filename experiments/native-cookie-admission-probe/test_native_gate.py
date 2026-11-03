"""Run the same published callback oracles through Java and Swift controllers."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parent
EXPECTED=json.loads((ROOT/'gate_cases.json').read_text())

class NativeGateTests(unittest.TestCase):
    def test_java_control_traces(self):
        out=ROOT/'build/java-tests'; out.mkdir(parents=True,exist_ok=True)
        java=Path('/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin')
        subprocess.run([str(java/'javac'),'-d',str(out),str(ROOT/'android/app/src/main/java/org/moonpool/cookieadmission/AdmissionGate.java'),str(ROOT/'android/app/src/main/java/org/moonpool/cookieadmission/GateCases.java')],check=True,capture_output=True,text=True)
        raw=subprocess.check_output([str(java/'java'),'-cp',str(out),'org.moonpool.cookieadmission.GateCases'],text=True)
        actual={line.split('\t')[0]:line.split('\t')[1].split('|') for line in raw.splitlines()}
        self.assertEqual(actual,EXPECTED)

    def test_swift_control_traces(self):
        out=ROOT/'build/swift-gate-tests'; out.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['xcrun','swiftc',str(ROOT/'ios/AdmissionGate.swift'),str(ROOT/'ios/GateCases.swift'),str(ROOT/'ios/test/Main.swift'),'-o',str(out)],check=True,capture_output=True,text=True)
        actual=json.loads(subprocess.check_output([str(out)],text=True))
        self.assertEqual(actual,EXPECTED)

if __name__=='__main__': unittest.main()
