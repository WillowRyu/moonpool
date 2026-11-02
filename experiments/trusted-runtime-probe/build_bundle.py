"""Compile unchanged kernel sources using the workspace's existing Vite."""
from pathlib import Path
import hashlib
import json
import subprocess

root=Path(__file__).resolve().parent
workspace=root.parents[1]
subprocess.run(['pnpm','--filter','moonpool-example-mock-host','exec','vite','build','--config',
    '../../experiments/trusted-runtime-probe/vite.config.mjs'],cwd=workspace,check=True)
files=[root/'kernel-probe.ts',root/'timer-adapter.js',root/'vite.config.mjs',workspace/'examples/mock-host/src/json-boundary.ts']
for package in ['protocol','client','host']:files+=sorted((workspace/'packages'/package/'src').glob('*.ts'))
meta={'bundleSha256':hashlib.sha256((root/'build/kernel-probe.js').read_bytes()).hexdigest(),
    'schedulerSha256':hashlib.sha256((root/'timer-adapter.js').read_bytes()).hexdigest(),
    'sources':{str(p.relative_to(workspace)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(root/'build/bundle-metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
print('Common kernel bundle and source fingerprints recorded.')
