"""Verify actual iOS metadata/reply controls; preserve global/frame eval gaps."""

import argparse
import hashlib
import json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('directory',type=Path)
parser.add_argument('--single',type=Path)
args=parser.parse_args()
checks=0
metadata=None
def require(value,label):
    global checks
    if not value:raise AssertionError(label)
    checks+=1

files=[args.single] if args.single else [args.directory/f'{p}-{r}.json' for p in ['all-frames','main-only'] for r in ['first','repeat']]
for path in files:
    report=json.loads(path.read_text());context=report['profile']+'/'+report['run'];events=report['events']
    require(report['complete'] and report['heldCompletionsCalled'],context+' native report/completion bookkeeping')
    require(metadata is None or metadata==report['buildMetadata'],'One final build/source set')
    metadata=report['buildMetadata'];samples={s['label']:s for s in report['samples']}
    require(len(samples)==20 and not any(s.get('unavailable') for s in samples.values()),context+' all observations available')
    messages=[e for e in events if e['type']=='message']
    require(all(e['webViewMatches'] and e['claimedOrigin']=='moonpool://forged.invalid' for e in messages),context+' native metadata independent of claims')
    require(all(e['mainFrame'] and e['world']==e['expectedWorld'] for e in messages if e['decision']=='accepted'),context+' admitted frame/world checks')
    for label in ['initial-a','initial-b','same-origin-other-view']:
        s=samples[label];d=s['observation'];app='b' if label=='initial-b' else 'a'
        require(d['origin']==f'moonpool://com.example.probe.{app}' and len(d['frames'])==2,context+'/'+label+' origin/loaded frames')
        require(d['pageHandlerVisible'] and not d['isolatedHandlerVisible'] and not d['isolatedGlobalVisible'],context+'/'+label+' isolated handler/globals hidden from page')
        require(d['sharedDOMMarker']=='shared-dom-marker',context+'/'+label+' DOM shared across worlds')
        require(all(frame['pageHandlerVisible'] for frame in d['frames']),context+'/'+label+' handler present in subframes')
        first=[e for e in messages if e['view']==s['view'] and e['mainFrame'] and e['kind']=='inline']
        require(first and first[0]['beforePageFinished'] and first[0]['readyState']=='loading',context+'/'+label+' first inline message')
        require(any(r['kind']=='normal' and r['value']['marker']=='immediate:normal' for r in d['replies']),context+'/'+label+' direct native reply positive')
    require(any(e['decision']=='subframe' for e in messages),context+' same-origin subframe rejected')
    require(any(e['decision']=='wrong-origin' for e in messages),context+' foreign-origin call rejected')
    require(any(e['type']=='host-route-replay' and e['decision']=='wrong-view' for e in events),context+' actual other-view host replay')
    world_events=[e for e in messages if e['kind']=='world-start']
    require(any(e['mainFrame'] and e['world']=='MoonpoolT26' for e in world_events),context+' named-world main positive')
    require(any(not e['mainFrame'] for e in world_events) if report['profile']=='all-frames' else all(e['mainFrame'] for e in world_events),context+' script main-frame-only option')
    world=next(e for e in events if e['type']=='world-eval')
    require(world['success'] and json.loads(world['value'])['value']=='isolated-public-marker',context+' native evaluation in named world')
    for suffix,positive in [('replacement','replacement-positive'),('reload','reload-positive')]:
        old=samples['old-reply-'+suffix]['observation'];current=samples[positive]['observation']
        require(old['heldResults']==[],context+'/'+suffix+' old direct reply excluded from new Promise')
        require(len(current['heldResults'])==1 and current['heldResults'][0]['marker']=='current:'+positive,context+'/'+suffix+' current reply succeeds with same payload id')
        global_result=samples['legacy-global-'+suffix]['observation']
        require(global_result['legacyResult']=='old:legacy-global-'+suffix,context+'/'+suffix+' global receiver stale id collision control')
        frame=next(e for e in events if e['type']=='frame-eval-result' and e['label']=='stale-frame-'+suffix)
        require(isinstance(frame['success'],bool),context+'/'+suffix+' old frame execution outcome retained')
        if frame['success']:
            require(frame['result']['instance']==global_result['instance'],context+'/'+suffix+' old frame targets current document')
    before=samples['same-origin-replacement']['observation'];after=samples['same-url-reload']['observation']
    require(before['href']==after['href'] and before['instance']!=after['instance'],context+' actual same-URL fresh document')
    foreign=samples['foreign-navigation']['observation']
    require(any(r['kind']=='normal' and r['message']=='denied:wrong-origin' for r in foreign['rejected']),context+' foreign navigation denied')
    returned=samples['return-navigation']['observation']
    require(any(r['kind']=='normal' for r in returned['replies']),context+' fresh return positive')
    retired=samples['retired-binding']['observation']
    require(any(r['kind']=='after-retire' and r['message']=='denied:retired' for r in retired['rejected']),context+' real call after retirement denied')
    removed=samples['removed-reference']['observation']
    require(removed['removalAttempted'] and not removed['pageHandlerVisible'],context+' removed handler retained-reference attempt observed')
    removed_sequence=next(e['sequence'] for e in events if e['type']=='handlers-removed')
    require(not any(e['sequence']>removed_sequence and e['type']=='message' and e['decision']=='accepted' for e in events),context+' no admitted message after removal')
if not args.single:
    root=Path(__file__).resolve().parent
    for name,sha in metadata['sources'].items():require(hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,'Source fingerprint '+name)
print(f'{checks} native controls passed; reply closure binding and global/frame-eval limitations retained separately.')
