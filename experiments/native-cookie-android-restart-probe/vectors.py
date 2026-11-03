"""Expand store kinds into interleaved stores, so neither kind nor order tracks process time."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KINDS = json.loads((ROOT / 'store_kinds.json').read_text())
ORDERS = {'b': 'bare', 'v': 'view', 'p': 'policy'}
SAMPLES = 2
DEFAULTS = {'service': '127.0.0.1', 'seedTop': 'localhost', 'steps': [], 'cookies': {}, 'storage': False,
            'denyBefore': False, 'denyAfter': False, 'wait': 0, 'brandNew': False, 'late': False, 'thirdParty': False}


def expand():
    stores = []
    for sample in range(1, SAMPLES + 1):
        for short, order in ORDERS.items():
            for kind in KINDS:
                stores.append({**DEFAULTS, **kind, 'id': f"{kind['kind']}-{short}{sample}", 'order': order})
    return stores


def cookie_name(kind):
    return 't28r_' + kind
