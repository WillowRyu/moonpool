from pathlib import Path
import argparse
import hashlib
import json

parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args()
checks=0;common_meta=None
def require(value,label):
 global checks
 if not value:raise AssertionError(label)
 checks+=1
for platform in ['ios','android']:
 for run in ['first','repeat']:
  report=json.loads((args.directory/f'{platform}-{run}.json').read_text());context=platform+'/'+run
  require(report['complete'] and report['run']==run and report['platform']==platform,context+' report')
  if platform=='android':require(report['supported'] and 'errorClass' not in report,context+' sandbox availability')
  meta=report['buildMetadata']['common'];require(common_meta is None or common_meta==meta,'Same common kernel bundle/source set');common_meta=meta
  require(len(report['samples'])==3,context+' runtime owners')
  for sample,name,initial,stored in zip(report['samples'],['a-first','a-recreated','b-independent'],[None,'saved-A',None],['saved-A','saved-A','saved-B']):
   c=sample['common'];label=context+'/'+name
   require(sample['name']==name and sample['guestProbeGlobalAbsent'],label+' separate diagnostic realm')
   require(c['complete'] and 'error' not in c and len(c['checks'])==15 and all(v['passed'] for v in c['checks']),label+' real kernel vectors')
   require(not c['globals']['window'] and not c['globals']['document'] and c['globals']['timeout'] and c['globals']['microtask'],label+' DOM-free runtime/primitives')
   require(c['initialValue']==initial and c['storedValue']==stored,label+' native fixture snapshot seeding')
   state=json.loads(sample['schedulerAfterClose']);require(state['pendingTimers']==0 and state['hostDiagnosticCount']==1,label+' scheduler/host-only diagnostics')
  events=report['events']
  require(sum(e['type']=='owner-executor-confirmed' for e in events)==3,context+' observed native executor')
  require(sum(e['type']=='late-control-dropped' for e in events)==3,context+' captured old-owner controls dropped')
  require(not any(e['type'] in ['engine-exception','wrong-executor','late-control-unexpectedly-active'] for e in events),context+' no owner/engine error')
  root=Path(__file__).resolve().parent/platform
  for name,sha in report['buildMetadata']['sources'].items():require(hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,context+' native source '+name)
workspace=Path(__file__).resolve().parents[2]
for name,sha in common_meta['sources'].items():require(hashlib.sha256((workspace/name).read_bytes()).hexdigest()==sha,'common source '+name)
print(f'{checks} runtime evidence checks passed; 12 native owners / 180 common-kernel vectors. Provider/scheduler production integration remains unproven.')
