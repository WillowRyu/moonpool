"""Compare what a platform cookie parser does with what the C04 profile draft expects.

Usage: python3 -B compare.py results/<platform>.json [...]
Prints one row per vector that differs on any platform, then a count by source and grammar.
"""
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKEW_MS = 120_000
FIELDS = ('name', 'value', 'domain', 'path', 'hostOnly', 'httpOnly', 'secure')
DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
TOKEN = re.compile(r'\{(\w+):([^}]*)\}')
UNITS = {'d': 86400, 'h': 3600, 'm': 60}


def http_date(seconds):
    """IMF-fixdate, written out by hand so the result never depends on the locale."""
    import time
    t = time.gmtime(seconds)
    return f'{DAYS[t.tm_wday]}, {t.tm_mday:02d} {MONTHS[t.tm_mon - 1]} {t.tm_year} {t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d} GMT'


def expand(text, now_seconds):
    def replace(match):
        kind, argument = match.groups()
        if kind == 'date':
            found = re.fullmatch(r'([+-])(\d+)([dhm])', argument)
            if not found:
                raise ValueError(f'bad date token {match.group(0)}')
            sign, amount, unit = found.groups()
            offset = int(amount) * UNITS[unit]
            return http_date(now_seconds + (offset if sign == '+' else -offset))
        if kind == 'repeat':
            character, _, count = argument.partition(':')
            if len(character) != 1 or not count.isdigit():
                raise ValueError(f'bad repeat token {match.group(0)}')
            return character * int(count)
        raise ValueError(f'unknown token {match.group(0)}')
    return TOKEN.sub(replace, text)


def read_document():
    return json.loads((ROOT / 'vectors.json').read_text())


def load_vectors(now_ms, document=None):
    vectors = copy.deepcopy((document or read_document())['vectors'])
    now_seconds = now_ms // 1000
    for vector in vectors:
        vector['line'] = expand(vector['line'], now_seconds)
        for key in ('name', 'value'):
            if key in vector['draft']:
                vector['draft'][key] = expand(vector['draft'][key], now_seconds)
    return vectors


def valid_expiry(expiry):
    if expiry in ('session', 'expired'):
        return True
    return isinstance(expiry, dict) and len(expiry) == 1 and next(iter(expiry)) in ('seconds', 'days') and isinstance(next(iter(expiry.values())), int)


def validate(document):
    problems, seen = [], set()
    for vector in document.get('vectors', []):
        name = vector.get('id', '?')
        if name in seen:
            problems.append(f'duplicate id {name}')
        seen.add(name)
        for key in ('source', 'url', 'line', 'checks', 'draft'):
            if key not in vector:
                problems.append(f'{name}: missing {key}')
        if not isinstance(vector.get('wellFormed'), bool):
            problems.append(f'{name}: wellFormed must be true or false')
        draft = vector.get('draft', {})
        if not isinstance(draft.get('accept'), bool):
            problems.append(f'{name}: draft.accept must be true or false')
            continue
        try:
            expand(vector.get('line', ''), 0)
        except ValueError as error:
            problems.append(f'{name}: {error}')
        if not draft['accept'] or draft.get('split'):
            continue
        for key in FIELDS:
            if key not in draft:
                problems.append(f'{name}: draft missing {key}')
        if not valid_expiry(draft.get('expiry')):
            problems.append(f'{name}: bad draft expiry')
        if len(draft.get('sends', [])) != len(vector.get('checks', [])):
            problems.append(f'{name}: draft.sends must have one entry per check')
    return problems


def expiry_matches(expected, cookie, now_ms):
    persistent, expires = cookie.get('persistent'), cookie.get('expiresAt')
    if expected == 'session':
        return persistent is False
    if expected == 'expired':
        return persistent is True and expires <= now_ms
    seconds = expected.get('seconds', 0) + expected.get('days', 0) * 86400
    return persistent is True and abs(expires - (now_ms + seconds * 1000)) <= SKEW_MS


def differences(vector, observed, now_ms):
    """Field names in which the observation differs from the draft. Acceptance first, since fields of a missing cookie mean nothing."""
    draft = vector['draft']
    if draft.get('split'):
        return []
    if observed.get('accepted') != draft['accept']:
        return ['accept']
    if not draft['accept']:
        return []
    cookie, found = observed['cookie'], []
    for key in FIELDS:
        expected, actual = draft[key], cookie.get(key)
        if key == 'domain' and isinstance(actual, str):
            actual = actual.lower()
        if actual != expected:
            found.append(key)
    if 'sameSite' in draft and cookie.get('sameSite') is not None and cookie['sameSite'].lower() != draft['sameSite']:
        found.append('sameSite')
    if not expiry_matches(draft['expiry'], cookie, now_ms):
        found.append('expiry')
    if 'sends' in draft and observed.get('sends') != draft['sends']:
        found.append('sends')
    return found


def main(paths):
    reports = [json.loads(Path(path).read_text()) for path in paths]
    names = [report['platform'] for report in reports]
    rows, counts = [], {}
    for vector in load_vectors(reports[0]['nowMs']):
        cells = []
        for report in reports:
            vectors = {v['id']: v for v in load_vectors(report['nowMs'])}
            observed = next(o for o in report['observations'] if o['id'] == vector['id'])
            cells.append(', '.join(differences(vectors[vector['id']], observed, report['nowMs'])) or '-')
        key = (vector['source'], vector['wellFormed'])
        total, differing = counts.get(key, (0, 0))
        counts[key] = (total + 1, differing + (any(cell != '-' for cell in cells)))
        if any(cell != '-' for cell in cells):
            rows.append(f"| {vector['id']} | {vector['source']} | {'yes' if vector['wellFormed'] else 'no'} | " + ' | '.join(cells) + ' |')
    print('| Id | Source | Well-formed | ' + ' | '.join(names) + ' |')
    print('| --- | --- | --- | ' + ' | '.join('---' for _ in names) + ' |')
    print('\n'.join(rows))
    print()
    for (source, well_formed), (total, differing) in sorted(counts.items()):
        print(f"{source}, well-formed={well_formed}: {differing} of {total} differ from the draft")


if __name__ == '__main__':
    main(sys.argv[1:])
