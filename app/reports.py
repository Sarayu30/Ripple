"""Portable creator-ready Markdown report generated exclusively from saved state."""
from . import store
from .simulation import cached
from .experiments import compare

def creator_report(row):
    r=row['result'];o=r['outcome'];rec=r.get('recommendations') or {}
    lines=['# Ripple · '+row['title'],'','Created: '+row['created'],'',r['disclaimer'],'','## Main audience insight',r.get('insights',{}).get('summary',o['verdict']),'',f"Evaluated {o['completed']} of {o['requested']} synthetic viewers.",'','## Audience segments']
    for s in o['segments']:
        lines.append(f"- {s['name']}: {s['count']} viewers; relevance {s['relevance']}/100; share intent {s['share']}/100. {s.get('insight','')}")
    lines+=['','## Key objections']
    lines.extend('- '+p['personaName']+': '+p['objection'] for p in r['personas'])
    lines+=['','## Priority edits']+['- '+x for x in rec.get('topEdits',[])]
    for label,key in [('Alternative hook','alternativeHook'),('Caption','caption'),('CTA','cta')]: lines+=['','### '+label,rec.get(key,'Unavailable')]
    lines+=['','## Evidence sources']+['- '+x for x in rec.get('sources',[])]
    version=cached(store.MEDIA/row['id'],'experiment.json') or {}
    parent=store.get(version.get('parentId',''))
    lines+=['','## Original vs revised content']
    if parent and parent.get('result'):
        comparison=compare(parent,row)
        lines+=['Original: '+parent['title'],'Shared personas: '+str(comparison['sharedPersonas']),'Changed assumptions: '+(', '.join(comparison['assumptionDifferences']) or 'none')]
        lines+=['- '+key+f': {delta:+g} points' for key,delta in comparison['metricDeltas'].items()]
        lines+=['### Original recommendations']+['- '+x for x in (parent['result'].get('recommendations') or {}).get('topEdits',[])]
        lines+=['### Segment differences']+[f"- {s['name']}: share-intent change {s['shareDelta']} points" for s in comparison['segments']]
        lines+=comparison['limitations']
    else: lines+=['No parent comparison is available for this simulation.']
    lines+=['','## Simulation assumptions']+['- '+k+': '+str(v) for k,v in o['assumptions'].items()]
    lines+=['','## Limitations']+['- '+x for x in r['limitations']]
    lines+=['','## Evidence provenance']+['- '+e['id']+' ('+e['kind']+'): '+e['description'] for e in r.get('provenance',[])]
    return '\n'.join(lines)+'\n'
