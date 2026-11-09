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
# The largest legitimate skew in the retained runs is under 2 s: iOS truncates its parse time to whole seconds,
# and dates are written to the second. A 60 s Max-Age must not match a cookie that expired at once (review, 2026-11-09).
SKEW_MS = 5_000
FIELDS = ('name', 'value', 'domain', 'path', 'hostOnly', 'httpOnly', 'secure')
DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
# Any {word:...} is a token, so a misspelt one fails instead of becoming a literal cookie byte. No vector needs braces.
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
        templated = [vector.get('line', ''), vector.get('url', ''), *vector.get('checks', []),
                     *(draft[key] for key in ('name', 'value') if isinstance(draft.get(key), str))]
        for text in templated:
            try:
                expand(text, 0)
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
    if 'error' in observed:
        return ['error']
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
    if 'sameSite' in draft:
        found.extend(same_site_difference(draft['sameSite'], cookie.get('sameSite')))
    if not expiry_matches(draft['expiry'], cookie, now_ms):
        found.append('expiry')
    if 'sends' in draft and observed.get('sends') != draft['sends']:
        found.append('sends')
    return found


SESSION_SENTINEL = 253402300799999  # OkHttp's expiresAt for a session cookie, so both platforms read alike


def ios_fields(cookie):
    domain = cookie['domain']
    persistent = not cookie['sessionOnly']
    out = {'name': cookie['name'], 'value': cookie['value'], 'domain': domain.lstrip('.'), 'path': cookie['path'],
           'hostOnly': not domain.startswith('.'), 'httpOnly': cookie['httpOnly'], 'secure': cookie['secure'],
           'persistent': persistent, 'expiresAt': cookie['expiresMs'] if persistent else SESSION_SENTINEL}
    if cookie.get('sameSite') is not None:
        out['sameSite'] = cookie['sameSite'].lower()
    return out


def ios_view(raw, clock_ms):
    """What iOS did with one vector: the stored cookie when storage kept it, the parsed one when it only deletes.

    A parsed expiry at or before the moment iOS parsed is a deletion, which storage never keeps. iOS dates Max-Age to the
    whole second it parses in, so the probe records parsedAtMs just after parsing; older results fall back to clock_ms,
    when the app started, which a deletion can exceed only if parsing crossed a second boundary.
    """
    if 'error' in raw:
        return {'id': raw['id'], 'error': raw['error']}
    parsed = raw['parsed']
    view = {'id': raw['id'], 'count': len(parsed)}
    if not parsed:
        return view | {'accepted': False}
    first = parsed[0]
    parsed_at = raw.get('parsedAtMs', clock_ms)
    expired = not first['sessionOnly'] and first['expiresMs'] is not None and first['expiresMs'] <= parsed_at
    stored = next((cookie for cookie in raw['stored'] if cookie['name'] == first['name']), None)
    if not expired and stored is None:
        return view | {'accepted': False, 'refusedBy': 'storage'}
    view.update(accepted=True, cookie=ios_fields(first if expired else stored), sends=list(raw['sends']))
    view['parsedExpiresAt'] = ios_fields(first)['expiresAt']
    return view


def observations_of(report):
    """Observations judged against the report's clock. iOS results keep only raw data, so the view is derived here."""
    if 'raw' in report:
        return [ios_view(raw, report['clockMs']) for raw in report['raw']]
    return report['observations']


def platform_differences(a, now_a, b, now_b):
    """Field names in which two platforms' observations of the same vector disagree, each read against its own run clock."""
    if 'error' in a or 'error' in b:
        return ['error']
    if a.get('accepted') != b.get('accepted'):
        return ['accept']
    if not a.get('accepted'):
        return []
    left, right, found = a['cookie'], b['cookie'], []
    for key in FIELDS:
        x, y = left.get(key), right.get(key)
        if key == 'domain':
            x, y = x.lower(), y.lower()
        if x != y:
            found.append(key)
    if left.get('sameSite') is not None or right.get('sameSite') is not None:
        found.extend(same_site_difference(left.get('sameSite'), right.get('sameSite')))
    if not same_expiry(left, now_a, right, now_b):
        found.append('expiry')
    if a.get('sends') != b.get('sends'):
        found.append('sends')
    if a.get('count', 1) != b.get('count', 1):
        found.append('count')
    return found


def same_site_difference(expected, actual):
    """SameSite reported on one side only is not agreement: iOS's API has no value for None or an unknown token."""
    if expected is None or actual is None:
        return ['sameSite(unobserved)']
    return [] if expected.lower() == actual.lower() else ['sameSite']


def same_expiry(left, now_a, right, now_b):
    if left['persistent'] != right['persistent']:
        return False
    if not left['persistent']:
        return True
    expired = left['expiresAt'] <= now_a, right['expiresAt'] <= now_b
    if any(expired):
        return all(expired)
    return abs((left['expiresAt'] - now_a) - (right['expiresAt'] - now_b)) <= SKEW_MS


def classify(cell):
    """'' for agreement, 'unobserved' when every difference is an attribute one side cannot report, else 'differ'."""
    if cell == '-':
        return ''
    return 'unobserved' if all(name.endswith('(unobserved)') for name in cell.split(', ')) else 'differ'


def main(paths):
    reports = [json.loads(Path(path).read_text()) for path in paths]
    names = [report['platform'] for report in reports]
    between = len(reports) == 2
    views = [({v['id']: v for v in load_vectors(r['nowMs'])}, {o['id']: o for o in observations_of(r)}) for r in reports]
    clocks = [r.get('clockMs', r['nowMs']) for r in reports]
    rows, counts = [], {}
    for vector in load_vectors(reports[0]['nowMs']):
        cells = [', '.join(differences(vectors[vector['id']], observed[vector['id']], clock)) or '-'
                 for (vectors, observed), clock in zip(views, clocks)]
        if between:
            cells.append(', '.join(platform_differences(views[0][1][vector['id']], clocks[0],
                                                        views[1][1][vector['id']], clocks[1])) or '-')
        key = (vector['source'], vector['wellFormed'])
        tally = counts.setdefault(key, [0] + [[0, 0] for _ in cells])
        tally[0] += 1
        for index, cell in enumerate(cells):
            kind = classify(cell)
            if kind:
                tally[index + 1][kind == 'unobserved'] += 1
        if any(cell != '-' for cell in cells):
            rows.append(f"| {vector['id']} | {vector['source']} | {'yes' if vector['wellFormed'] else 'no'} | " + ' | '.join(cells) + ' |')
    columns = [f'{name} vs draft' for name in names] + (['between platforms'] if between else [])
    print('| Id | Source | Well-formed | ' + ' | '.join(columns) + ' |')
    print('| --- | --- | --- | ' + ' | '.join('---' for _ in columns) + ' |')
    print('\n'.join(rows))
    print()
    for (source, well_formed), tally in sorted(counts.items()):
        parts = ', '.join(f'{column}: {differ} (+{unobserved} unobserved only)' for column, (differ, unobserved) in zip(columns, tally[1:]))
        print(f"{source}, well-formed={well_formed}, {tally[0]} vectors -> {parts}")


if __name__ == '__main__':
    main(sys.argv[1:])
