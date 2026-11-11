"""Check the c04-1 vectors against the retained native broker on the desktop JVM."""

import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
BROKER = ROOT.parent / (
    'native-http-broker-probe/android/app/src/main/java/org/moonpool/httpbroker/Broker.java'
)
REPEAT = re.compile(r'\{repeat:(.):([0-9]+)\}')
IDENTITY = ('name', 'domain', 'path', 'hostOnly')


def expand_repetitions(value):
    """Expand the same repeated-byte notation as the OS parser comparison vectors."""
    if isinstance(value, str):
        return REPEAT.sub(lambda match: match[1] * int(match[2]), value)
    if isinstance(value, list):
        return [expand_repetitions(item) for item in value]
    if isinstance(value, dict):
        return {key: expand_repetitions(item) for key, item in value.items()}
    return value


def inputs_for(cases, t0, default_url):
    """Give the subject timestamped inputs. The expected outputs stay with the verifier."""
    for case in cases:
        at = 0
        steps = []
        for step in case['steps']:
            next_at = step.get('at', at)
            if type(next_at) is not int or next_at < at:
                raise ValueError(f"{case['id']} must use nondecreasing integer clock offsets")
            at = next_at
            steps.append({
                **{key: value for key, value in step.items() if key not in ('expect', 'at')},
                'url': step.get('url', default_url),
                'now': (t0 + timedelta(seconds=at)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            })
        yield {'id': case['id'], 'steps': steps}


def classpath():
    deps = ROOT.parent / 'native-cookie-parser-comparison/local-results/deps'
    okhttp = deps / 'okhttp-jvm-5.5.1.jar'
    published = (deps / 'okhttp-jvm-5.5.1.jar.sha1').read_text().split()
    if not published or hashlib.sha1(okhttp.read_bytes()).hexdigest() != published[0]:
        raise ValueError('OkHttp JVM jar SHA-1 differs from the published checksum')

    gradle = Path(os.environ.get('GRADLE_USER_HOME', Path.home() / '.gradle'))
    cache = gradle / 'caches/modules-2/files-2.1'
    jars = [okhttp]
    for group, artifact, version in (
        ('com.squareup.okio', 'okio-jvm', '3.18.1'),
        ('org.jetbrains.kotlin', 'kotlin-stdlib', '2.2.21'),
        ('org.json', 'json', '20250517'),
    ):
        name = f'{artifact}-{version}.jar'
        if (deps / name).is_file():
            jars.append(deps / name)
            continue
        matches = sorted(cache.glob(f'{group}/{artifact}/{version}/*/{name}'))
        if not matches:
            raise FileNotFoundError(f'{group}:{artifact}:{version} is missing from {cache}')
        jars.append(matches[0])
    return os.pathsep.join(str(jar) for jar in jars)


def run_baseline(inputs):
    deps = classpath()
    with tempfile.TemporaryDirectory(prefix='moonpool-c04-jvm-') as classes:
        subprocess.run(
            ['javac', '--release', '17', '-cp', deps, '-d', classes, str(BROKER),
             str(ROOT / 'BrokerBaseline.java')],
            check=True,
        )
        result = subprocess.run(
            ['java', '-cp', classes + os.pathsep + deps, 'org.moonpool.httpbroker.BrokerBaseline'],
            input=json.dumps(inputs), capture_output=True, encoding='utf-8', check=True,
        )
    return json.loads(result.stdout)


def jar_views(expected, observed):
    # Jar snapshots compare identities and named metadata. Header/read steps compare selection order.
    def identity(cookie):
        return tuple(cookie[key] for key in IDENTITY)

    expected = sorted(expected, key=identity)
    observed = sorted(observed, key=identity)
    if len(expected) == len(observed):
        observed = [
            {key: cookie[key] for key in target if key in cookie}
            for target, cookie in zip(expected, observed, strict=True)
        ]
    return expected, observed


def show(value):
    result = json.dumps(value, sort_keys=True)
    if len(result) <= 160:
        return result
    return f'{result[:157]}... ({len(result)} characters)'


def verify(cases, results):
    if [result['id'] for result in results] != [case['id'] for case in cases]:
        raise ValueError('the baseline must return one result per case in order')

    failed_cases = 0
    checked_steps = 0
    failed_steps = 0
    for case, result in zip(cases, results, strict=True):
        steps = case['steps']
        if all(step['op'] == 'receive' for step in steps):
            raise ValueError(f"{case['id']} has no assertions")
        observations = result['observations']
        if len(observations) != len(steps):
            raise ValueError(f"{case['id']} must return one observation per step")
        mismatches = []
        for index, (step, observed) in enumerate(zip(steps, observations, strict=True), 1):
            if step['op'] == 'receive':
                continue
            checked_steps += 1
            expected = step['expect']
            if step['op'] == 'jar':
                expected, observed = jar_views(expected, observed)
            if json.dumps(expected, sort_keys=True) != json.dumps(observed, sort_keys=True):
                mismatches.append(
                    f"  step {index} {step['op']}: expected {show(expected)}, observed {show(observed)}"
                )
        if mismatches:
            print(f"FAIL {case['id']} {case['title']}")
            print('\n'.join(mismatches))
            failed_cases += 1
            failed_steps += len(mismatches)

    print(f'{len(cases) - failed_cases}/{len(cases)} cases passed, {failed_cases} failed')
    print(f'{checked_steps - failed_steps}/{checked_steps} assertions passed, {failed_steps} failed')
    return failed_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--psl', type=Path, required=True, help='pinned public_suffix_list.dat')
    parser.add_argument('--case', help='run one ID or all variants of a profile row')
    args = parser.parse_args()
    try:
        profile = json.loads((ROOT / 'vectors.json').read_text(encoding='utf-8'))
        if profile['profile'] != 'c04-1':
            raise ValueError('the baseline verifier expects profile c04-1')
        psl = profile['psl']
        if hashlib.sha256(args.psl.read_bytes()).hexdigest() != psl['sha256']:
            raise ValueError('PSL SHA-256 differs from the c04-1 snapshot')
        cases = expand_repetitions(profile['cases'])
        ids = [case['id'] for case in cases]
        if len(ids) != len(set(ids)):
            raise ValueError('case IDs must be unique')
        if args.case:
            cases = [case for case in cases if args.case in (case['id'], case['id'][:3])]
        if not cases:
            raise ValueError(f'no cases selected by {args.case!r}')
        print(f"{profile['profile']} PSL {psl['commit']} verified", flush=True)
        inputs = list(inputs_for(cases, datetime.fromisoformat(profile['t0']), profile['url']))
        return 1 if verify(cases, run_baseline(inputs)) else 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr, file=sys.stderr)
        print(f'Cannot run C04 tests: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
