"""Expand store kinds; each store is checked in its own new process, in vector order."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KINDS = json.loads((ROOT / 'store_kinds.json').read_text())
ORDERS = {'r': 'records-first', 'n': 'names-first'}
SAMPLES = 2
DEFAULTS = {'service': '127.0.0.1', 'seedTop': 'localhost', 'steps': [], 'cookies': {}, 'storage': False,
            'allowBefore': False, 'denyAfter': False, 'hazard': False}


def expand():
    stores = []
    for sample in range(1, SAMPLES + 1):
        for short, order in ORDERS.items():
            for kind in KINDS:
                stores.append({**DEFAULTS, **kind, 'id': f"{kind['kind']}-{short}{sample}", 'order': order})
    return stores


def cookie_name(kind):
    return 't28f_' + kind
