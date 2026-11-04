"""Collect from the explicit owned device. An unexpected process exit ends the run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from build import ios_artifact_digest, sha
from fixture import vectors_digest

ROOT = Path(__file__).resolve().parent
ADB = Path.home() / 'Library/Android/sdk/platform-tools/adb'
PACKAGES = {'android': 'org.moonpool.httpbroker', 'ios': 'org.moonpool.ioshttpbrokerprobe'}
DEADLINE_SECONDS = 300


def parse_report(raw, tag):
    if not raw:
        return None
    try:
        report = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return report if isinstance(report, dict) and report.get('run') == tag else None


def assert_fresh_run(rows_path, tag):
    """Receipts and the fixture's attempts and holds are kept by run tag, so a reused tag would mix two runs."""
    if rows_path.exists() and any(json.loads(line)['run'] == tag for line in rows_path.read_text().splitlines()):
        raise ValueError(f'Run tag {tag} already has receipts; use a new tag')


def collect(device, tag, expected_artifact, deadline_seconds=DEADLINE_SECONDS, startup_seconds=3, poll_seconds=0.5):
    """Nothing launches until the installed artifact matches the build, and the device is always stopped afterwards."""
    try:
        installed = device.prepare()
        assert installed == expected_artifact, 'Installed artifact differs from the build'
        device.launch()
        started = time.monotonic()
        while True:
            report = parse_report(device.read_report(), tag)
            if report is not None:
                return report, installed
            elapsed = time.monotonic() - started
            if elapsed >= deadline_seconds:
                raise TimeoutError('No final report; stopped without retry')
            if elapsed >= startup_seconds and not device.alive():
                raise RuntimeError('Probe process exited unexpectedly; stopped without retry')
            time.sleep(poll_seconds)
    finally:
        device.stop()


class AndroidDevice:
    package = PACKAGES['android']

    def __init__(self, owner, tag, ports, install):
        self.serial, self.avd, self.tag, self.ports, self.install = owner['serial'], owner['avd'], tag, ports, install

    def adb(self, *parts, check=True, binary=False):
        return subprocess.run([str(ADB), '-s', self.serial, *parts], capture_output=True, text=not binary, check=check, timeout=60)

    def check_owner(self):
        assert self.adb('emu', 'avd', 'name').stdout.splitlines()[0] == self.avd

    def prepare(self):
        for value in self.ports:
            self.adb('reverse', f'tcp:{value}', f'tcp:{value}')
        if self.install:
            self.adb('install', '-r', str(ROOT / 'android/app/build/outputs/apk/debug/app-debug.apk'))
        path = self.adb('shell', 'pm', 'path', self.package).stdout.strip().removeprefix('package:')
        return hashlib.sha256(self.adb('exec-out', 'cat', path, binary=True).stdout).hexdigest()

    def launch(self):
        port, second, control = self.ports
        self.adb('shell', 'am', 'force-stop', self.package)
        self.adb('shell', 'run-as', self.package, 'rm', '-f', 'files/report.json')
        launched = self.adb('shell', 'am', 'start', '-n', self.package + '/.ProbeActivity', '--es', 'run', self.tag,
                            '--ei', 'port', str(port), '--ei', 'second', str(second), '--ei', 'control', str(control))
        assert 'Error' not in launched.stdout, launched.stdout

    def read_report(self):
        result = self.adb('exec-out', 'run-as', self.package, 'cat', 'files/report.json', check=False)
        return result.stdout if result.returncode == 0 else None

    def alive(self):
        # A busy emulator can answer one pidof with nothing, so absence must be seen twice.
        for _ in range(2):
            if self.adb('shell', 'pidof', self.package, check=False).stdout.strip():
                return True
            time.sleep(2)
        return False

    def stop(self):
        self.adb('shell', 'am', 'force-stop', self.package, check=False)
        for value in self.ports:
            self.adb('reverse', '--remove', f'tcp:{value}', check=False)


class IosDevice:
    package = PACKAGES['ios']

    def __init__(self, owner, tag, ports, install):
        self.owner, self.device, self.tag, self.ports, self.install = owner, owner['owned'], tag, ports, install
        self.output, self.pid = None, None

    def sim(self, *parts, check=True):
        return subprocess.run(['xcrun', 'simctl', *parts], capture_output=True, text=True, check=check, timeout=60)

    def check_owner(self):
        assert self.device not in self.owner['protected']
        devices = json.loads(self.sim('list', 'devices', 'available', '-j').stdout)['devices']
        current = next(d for group in devices.values() for d in group if d['udid'] == self.device)
        assert current['name'] == self.owner['name'] and current['state'] == 'Booted'

    def prepare(self):
        if self.install:
            self.sim('install', self.device, str(ROOT / 'build/HttpBrokerProbe.app'))
        return ios_artifact_digest(Path(self.sim('get_app_container', self.device, self.package, 'app').stdout.strip()))

    def launch(self):
        port, second, control = self.ports
        self.sim('terminate', self.device, self.package, check=False)
        self.output = Path(self.sim('get_app_container', self.device, self.package, 'data').stdout.strip()) / 'Documents/report.json'
        self.output.unlink(missing_ok=True)
        launched = self.sim('launch', self.device, self.package, '--run', self.tag, '--port', str(port), '--second', str(second), '--control', str(control)).stdout.strip()
        self.pid = int(launched.rsplit(':', 1)[1].strip())

    def read_report(self):
        return self.output.read_text() if self.output.exists() else None

    def alive(self):
        try:
            os.kill(self.pid, 0)
            return True
        except ProcessLookupError:
            return False

    def stop(self):
        self.sim('terminate', self.device, self.package, check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('platform', choices=['android', 'ios'])
    parser.add_argument('--run', required=True)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    platform, tag = args.platform, f'{args.platform}-{args.run}'
    if not re.fullmatch(r'[a-z0-9-]+', tag):
        raise ValueError('Invalid public run tag')
    owner = json.loads((ROOT / 'local-results' / f'{platform}-owner.json').read_text())
    metadata = json.loads((ROOT / 'local-results' / f'{platform}-build.json').read_text())
    for path, digest in metadata['sources'].items():
        assert sha(ROOT / path) == digest, 'Changed built source: ' + path
    assert sha(ROOT / 'local-results/tls/ca.pem') == metadata['caSha256']
    server = json.loads((ROOT / 'local-results/server.json').read_text())
    assert server['vectorsSha256'] == vectors_digest(), 'Restart the fixture: running server differs from vectors'
    rows_path = ROOT / 'local-results/tls/requests.jsonl'
    assert_fresh_run(rows_path, tag)
    ports = (server['port'], server['secondPort'], server['controlPort'])
    device = (AndroidDevice if platform == 'android' else IosDevice)(owner, tag, ports, args.install)
    device.check_owner()
    report, installed = collect(device, tag, metadata['artifactSha256'])
    report['build'] = metadata
    report['installedArtifactSha256'] = installed
    rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
    report['requests'] = [row for row in rows if row['run'] == tag]
    report['capturedUtc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    results = ROOT / 'results'
    results.mkdir(exist_ok=True)
    (results / (tag + '.json')).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(f"{tag}: complete={report.get('complete')}, observations={len(report.get('observations', []))}, requests={len(report['requests'])}")
    if not report.get('complete'):
        print({key: report[key] for key in ['error', 'errors'] if key in report})


if __name__ == '__main__':
    main()
