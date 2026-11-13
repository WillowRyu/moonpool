"""Check the c04-1 vectors against the reference parser, its Swift port or the retained Android broker.

Several --subject options run each subject in turn. The Java reference and its Swift port must then also
produce identical observations, including on seeded generated cases that have no expected values.
"""

import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
import random
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
BROKER = ROOT.parent / (
    'native-http-broker-probe/android/app/src/main/java/org/moonpool/httpbroker/Broker.java'
)
REFERENCE = ROOT / 'reference'
JAVA = REFERENCE / 'java'
SWIFT = REFERENCE / 'swift'
SWIFTC = ['swiftc', '-swift-version', '6', '-warnings-as-errors', '-O']
PACKAGE = 'org.moonpool.cookieprofile'
REPEAT = re.compile(r'\{repeat:(.):([0-9]+)\}')
IDENTITY = ('name', 'domain', 'path', 'hostOnly')
RULES_DIGEST = re.compile(r'^self-test: PSL rules sha256 ([0-9a-f]{64})$', re.MULTILINE)
SOURCE_IMPORT = re.compile(r'^\s*(@[A-Za-z_]+\s+)*import\s', re.MULTILINE)


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


class BehaviorFailure(Exception):
    """The subject ran and reported wrong results, which is exit status 1 rather than a setup error."""


def classpath(okhttp=True):
    deps = ROOT.parent / 'native-cookie-parser-comparison/local-results/deps'
    jars = []
    libraries = [('org.json', 'json', '20250517')]
    if okhttp:
        jar = deps / 'okhttp-jvm-5.5.1.jar'
        published = (deps / 'okhttp-jvm-5.5.1.jar.sha1').read_text().split()
        if not published or hashlib.sha1(jar.read_bytes()).hexdigest() != published[0]:
            raise ValueError('OkHttp JVM jar SHA-1 differs from the published checksum')
        jars.append(jar)
        libraries[:0] = [
            ('com.squareup.okio', 'okio-jvm', '3.18.1'),
            ('org.jetbrains.kotlin', 'kotlin-stdlib', '2.2.21'),
        ]

    gradle = Path(os.environ.get('GRADLE_USER_HOME', Path.home() / '.gradle'))
    cache = gradle / 'caches/modules-2/files-2.1'
    for group, artifact, version in libraries:
        name = f'{artifact}-{version}.jar'
        if (deps / name).is_file():
            jars.append(deps / name)
            continue
        matches = sorted(cache.glob(f'{group}/{artifact}/{version}/*/{name}'))
        if not matches:
            raise FileNotFoundError(f'{group}:{artifact}:{version} is missing from {cache}')
        jars.append(matches[0])
    return os.pathsep.join(str(jar) for jar in jars)


def self_test(command, subject):
    """Run a port's self-test and return the digest of its canonical PSL rules."""
    run = subprocess.run(command, capture_output=True, encoding='utf-8')
    print(run.stdout, end='', flush=True)
    # Status 3 means failed checks. Any other failure, such as an uncaught exception, is a setup error.
    if run.returncode == 3:
        raise BehaviorFailure(f'the {subject} self-test failed')
    if run.returncode:
        raise subprocess.CalledProcessError(run.returncode, run.args, stderr=run.stderr)
    match = RULES_DIGEST.search(run.stdout)
    if not match:
        raise ValueError(f'the {subject} self-test reported no PSL rules digest')
    return match[1]


def adapter(command, inputs):
    result = subprocess.run(command, input=json.dumps(inputs), capture_output=True, encoding='utf-8', check=True)
    return json.loads(result.stdout)


def run_reference(inputs, psl, digest):
    """Compile the parser with no classpath, so it cannot depend on anything beyond the JDK."""
    deps = classpath(okhttp=False)
    with tempfile.TemporaryDirectory(prefix='moonpool-c04-reference-') as classes:
        javac = ['javac', '--release', '17', '-Xlint:all', '-Werror', '-d', classes]
        subprocess.run([*javac, *sorted(map(str, (JAVA / 'src').rglob('*.java')))], check=True)
        tests = sorted(map(str, (JAVA / 'test').rglob('*.java')))
        subprocess.run([*javac, '-cp', classes + os.pathsep + deps, *tests], check=True)
        java = ['java', '-cp', classes + os.pathsep + deps]
        rules = self_test([*java, f'{PACKAGE}.ReferenceSelfTest', str(psl), digest], 'reference')
        return adapter([*java, f'{PACKAGE}.ReferenceAdapter', str(psl), digest], inputs), rules


def swift_sources():
    """The port uses only the Swift standard library, so no Foundation text API can change a result on iOS."""
    sources = sorted((SWIFT / 'src').glob('*.swift'))
    if not sources:
        raise ValueError(f'no Swift sources in {SWIFT / "src"}')
    for source in sources:
        if SOURCE_IMPORT.search(source.read_text(encoding='utf-8')):
            raise ValueError(f'{source.name} imports a module; the port must use only the standard library')
    return sources


def run_swift(inputs, psl, digest):
    """Build the port as its own module, then link the Foundation harness against it."""
    sources = swift_sources()
    with tempfile.TemporaryDirectory(prefix='moonpool-c04-swift-') as build:
        subprocess.run([
            *SWIFTC, '-enable-testing', '-parse-as-library', '-module-name', 'CookieProfile',
            '-emit-library', '-static', '-emit-module', '-emit-module-path', f'{build}/CookieProfile.swiftmodule',
            '-o', f'{build}/libCookieProfile.a', *map(str, sources),
        ], check=True)
        harness = f'{build}/harness'
        tests = sorted(map(str, (SWIFT / 'test').glob('*.swift')))
        subprocess.run([*SWIFTC, '-I', build, '-L', build, '-lCookieProfile', '-o', harness, *tests], check=True)
        rules = self_test([harness, 'self-test', str(psl), digest], 'Swift')
        return adapter([harness, 'adapter', str(psl), digest], inputs), rules


def run_baseline(inputs, psl, digest):
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
    return json.loads(result.stdout), None


RUNNERS = {'reference': run_reference, 'swift': run_swift, 'baseline': run_baseline}

# Pieces for generated cases. Each case uses one family of related hosts, so cookies are often sent back.
# Weighted choices favor ordinary cookies, and rarer pieces reach the boundaries and D1 rejections.
GENERATED_FAMILIES = (
    ('api.example.com', 'shop.api.example.com', 'example.com', 'www.example.com'),
    ('co.uk', 'shop.co.uk'),
    ('www.ck', 'shop.www.ck', 'other.www.ck'),
    ('shop.github.io', 'other.github.io'),
    ('shop.xn--55qx5d.cn', 'a.shop.xn--55qx5d.cn'),
    ('127.0.0.1',),
    ('[::1]',),
    ('a.github.io.', 'b.github.io.', 'co.uk.', 'shop.co.uk.'),
)
GENERATED_FAMILY_WEIGHTS = (6, 1, 1, 1, 1, 1, 1, 1)
GENERATED_PATHS = ('/', '/x', '/x/y', '/x/y/z', '', '/x/', '/xq', '/a%2Fb/c', '/a/b/c')
GENERATED_PATH_WEIGHTS = (6, 6, 6, 2, 1, 1, 1, 1, 1)
GENERATED_NAMES = ('a', 'b', 'sid', 'A', ' a ', '__Secure-a', '__secure-a', '__Host-a', '__host-a', '__HOST-a', '')
GENERATED_NAME_WEIGHTS = (6, 6, 6, 1, 1, 1, 1, 1, 1, 1, 1)
GENERATED_VALUES = ('1', '2', '', '"q r"', 'x y', 'v=1', 'x' * 4095, '\u00e9', '\u0001')
GENERATED_VALUE_WEIGHTS = (8, 8, 1, 1, 1, 1, 1, 1, 1)
GENERATED_ATTRIBUTES = (
    'Path=/', 'Path=/x', 'Path=/x/y', 'Path=x', 'Path=', ' path = /x ', 'Domain=example.com',
    'Domain=.example.com', 'Domain=EXAMPLE.com', 'Domain=api.example.com', 'Domain=co.uk', 'Domain=www.ck',
    'Domain=127.0.0.1', 'Domain=[::1]', 'Domain=', 'Domain=.', 'Domain=github.io.', 'Domain=co.uk.',
    'Domain=' + 'x' * 1025, 'Secure', 'HttpOnly', 'SameSite=None',
    'SameSite=lax', 'SameSite=Strict', 'SameSite=bogus', 'Max-Age=0', 'Max-Age=60', 'Max-Age=-1',
    'Max-Age=abc', 'Max-Age=+5', 'Max-Age=999999999999999999999', 'Expires=Wed, 11 Nov 2026 00:01:00 GMT',
    'Expires=Tue, 10 Nov 2026 00:00:00 GMT', 'Expires=Fri, 10 Nov 2028 00:00:00 GMT', 'Expires=tomorrow',
    'Expires=Wed, 21 Oct 70 07:28:00 GMT', 'Expires=Sun Nov  6 08:49:37 1994', 'Partitioned', 'Priority=High',
    'Foo=bar', 'Foo=\u00e9',
)
GENERATED_DELAYS = (0, 0, 0, 1, 30, 59, 60, 61, 3600, 34_560_000, 34_560_001)


def generated_line(rng):
    name = rng.choices(GENERATED_NAMES, GENERATED_NAME_WEIGHTS)[0]
    value = rng.choices(GENERATED_VALUES, GENERATED_VALUE_WEIGHTS)[0]
    pair = f'{name}={value}' if rng.random() > 0.05 else 'a'
    attributes = rng.choices(GENERATED_ATTRIBUTES, k=rng.choice((0, 1, 1, 2, 2, 3, 4)))
    return (';' if rng.random() < 0.1 else '; ').join([pair, *attributes])


def generated_cases(count, seed):
    """Cases without expected values. Only the agreement between ports is checked."""
    rng = random.Random(seed)
    cases = []
    for number in range(count):
        hosts = rng.choices(GENERATED_FAMILIES, GENERATED_FAMILY_WEIGHTS)[0]
        at = 0
        steps = []
        for _ in range(rng.randint(2, 10)):
            at += rng.choice(GENERATED_DELAYS)
            op = rng.choices(('receive', 'header', 'read', 'jar', 'set'), weights=(10, 6, 3, 2, 1))[0]
            path = rng.choices(GENERATED_PATHS, GENERATED_PATH_WEIGHTS)[0]
            step = {'op': op, 'at': at, 'url': f'https://{rng.choice(hosts)}{path}'}
            if op == 'receive':
                step['fields'] = [
                    ', '.join(generated_line(rng) for _ in range(rng.choice((1, 1, 1, 2))))
                    for _ in range(rng.randint(1, 3))
                ]
            elif op == 'set':
                fields = {
                    'name': rng.choices(GENERATED_NAMES, GENERATED_NAME_WEIGHTS)[0],
                    'value': rng.choices(GENERATED_VALUES, GENERATED_VALUE_WEIGHTS)[0],
                }
                if rng.random() < 0.5:
                    fields['path'] = rng.choice(('/', '/x', 'x', '/a;b'))
                if rng.random() < 0.5:
                    fields['maxAge'] = rng.choice((-1, 0, 60, 999_999_999, '60', True))
                step['fields'] = fields
            steps.append(step)
        cases.append({'id': f'G{number:05d}', 'steps': steps})
    return cases


def comparable(observation):
    # Jar entry order is not observable through header or read, so snapshots compare as sets of entries.
    if isinstance(observation, list) and observation and isinstance(observation[0], dict) and 'hostOnly' in observation[0]:
        return sorted(observation, key=lambda cookie: [cookie[key] for key in IDENTITY])
    return observation


def compare(observed):
    """Every observation of every case must match between the subjects, not only the asserted ones."""
    (first, expected), *others = observed.items()
    differences = []
    for other, results in others:
        if [result['id'] for result in results] != [result['id'] for result in expected]:
            raise ValueError(f'{first} and {other} returned different cases')
        for left, right in zip(expected, results, strict=True):
            for index, (a, b) in enumerate(zip(left['observations'], right['observations'], strict=True), 1):
                if json.dumps(comparable(a), sort_keys=True) != json.dumps(comparable(b), sort_keys=True):
                    differences.append(f"  {left['id']} step {index}: {first} {show(a)}, {other} {show(b)}")
    return differences


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
    parser.add_argument(
        '--subject', action='append', choices=tuple(RUNNERS), required=True,
        help='reference (Java), swift (its port) or baseline (the retained Android broker); repeat to run several',
    )
    parser.add_argument('--psl', type=Path, required=True, help='pinned public_suffix_list.dat')
    parser.add_argument('--case', help='run one ID or all variants of a profile row')
    parser.add_argument(
        '--generated', type=int, default=0, metavar='N',
        help='also compare N seeded generated cases between reference and swift',
    )
    parser.add_argument('--seed', type=int, default=20261113, help='seed for --generated')
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
        subjects = list(dict.fromkeys(args.subject))
        ports = [subject for subject in subjects if subject != 'baseline']
        if args.generated < 0 or (args.generated and len(ports) < 2):
            raise ValueError('--generated needs a nonnegative count and both --subject reference and --subject swift')
        print(f"{profile['profile']} PSL {psl['commit']} verified, subjects {', '.join(subjects)}", flush=True)
        t0 = datetime.fromisoformat(profile['t0'])
        inputs = list(inputs_for(cases, t0, profile['url']))
        generated = list(inputs_for(generated_cases(args.generated, args.seed), t0, profile['url']))

        failed = 0
        observed = {}
        digests = {}
        for subject in subjects:
            print(f'== {subject}', flush=True)
            subject_inputs = inputs if subject == 'baseline' else inputs + generated
            results, rules = RUNNERS[subject](subject_inputs, args.psl, psl['sha256'])
            if len(results) != len(subject_inputs):
                raise ValueError(f'{subject} must return one result per case')
            failed += verify(cases, results[:len(inputs)])
            if subject != 'baseline':
                observed[subject] = results
                digests[subject] = rules
        if len(observed) > 1:
            print(f"== {' and '.join(observed)}")
            differences = compare(observed)
            if len(set(digests.values())) > 1:
                differences.insert(0, f'  PSL rules digests differ: {digests}')
            for difference in differences[:10]:
                print(difference)
            print(f'{len(inputs)} corpus and {len(generated)} generated cases compared, '
                  f'{len(differences)} differences')
            failed += len(differences)
        return 1 if failed else 0
    except BehaviorFailure as failure:
        print(f'FAIL {failure}')
        return 1
    except (OSError, ValueError, TypeError, KeyError, OverflowError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr, file=sys.stderr)
        print(f'Cannot run C04 tests: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
