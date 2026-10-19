"""Immutable child versions and comparisons of actual saved results."""
import shutil
import uuid
from collections import Counter
from . import store
from .simulation import cached, checkpoint
from .schemas import TestInput

def create_version(parent, edit):
    id=str(uuid.uuid4());old=store.MEDIA/parent['id'];directory=store.MEDIA/id
    changes={k:v for k,v in edit.model_dump().items() if k not in ('title','approved') and v is not None}
    if not changes: raise ValueError('Change at least one content or audience field.')
    payload=dict(parent['payload'],title=edit.title)
    payload.setdefault('outsidePercent',0)
    payload.setdefault('outsideAudience','')
    for key in ('caption','cta','audience'):
        if key in changes: payload[key]=changes[key]
    payload=TestInput.model_validate(payload).model_dump()
    audience_changed=payload['audience']!=parent['payload']['audience']
    creative_changed=any(k in changes for k in ('hook','caption','cta','variation'))
    directory.mkdir(mode=0o700)
    try:
        from .budgets import admit
        admit(id,payload,preparing=True)
        context=cached(old,'context.json')
        if not context:
            raise ValueError('Saved content analysis is unavailable. Submit a new simulation with the content.')
        if context:
            for key in ('audience','caption','cta'): context[key]=payload[key]
            context['evidence']['caption']=bool(payload['caption'])
            # Preserve proposals inherited from the prior version.
            context['experiment']={**context.get('experiment',{}),**changes}
            checkpoint(directory,'context.json',context)
        analysis=cached(old,'analysis.json')
        if not creative_changed and analysis:
            checkpoint(directory,'analysis.json',analysis)
        if not audience_changed:
            profiles=cached(old,'profiles.json') or (parent.get('result') or {}).get('profiles')
            if profiles: checkpoint(directory,'profiles.json',profiles)
        version={'parentId':parent['id'],'rootId':(cached(old,'experiment.json') or {}).get('rootId',parent['id']),'changes':{**(context or {}).get('experiment',{}),**changes},'currentChanges':changes,'sharedAudience':not audience_changed,'approved':True,'rerunFrom':'content_analysis' if creative_changed else 'audience_research'}
        checkpoint(directory,'experiment.json',version)
        store.update(id,status='queued')
        return id
    except Exception:
        store.delete(id)
        shutil.rmtree(directory,ignore_errors=True)
        raise

def compare(a,b):
    if not a.get('result') or not b.get('result'): raise ValueError('Both versions need saved results.')
    ar,br=a['result'],b['result']
    defaults={'outsidePercent':0,'outsideAudience':''}
    mismatches=[k for k in ('audience','goal','platform','seedReach','contactsPerShare','size','outsidePercent','outsideAudience') if a['payload'].get(k,defaults.get(k))!=b['payload'].get(k,defaults.get(k))]
    shared=ar.get('profiles')==br.get('profiles') and bool(ar.get('profiles'))
    metrics={k:round(br['outcome']['metrics'][k]-v,2) for k,v in ar['outcome']['metrics'].items()}
    ag={s['name']:s for s in ar['outcome']['segments']};bg={s['name']:s for s in br['outcome']['segments']}
    segments=[{'name':name,'original':ag.get(name),'revised':bg.get(name),'shareDelta':round(bg[name]['share']-ag[name]['share'],2) if name in ag and name in bg else None} for name in sorted(ag.keys()|bg.keys())]
    def objections(r): return [{'text':k,'count':v} for k,v in Counter(p['objection'] for p in r['personas']).most_common(10)]
    return {'original':a['id'],'revised':b['id'],'metricDeltas':metrics,'sharedPersonas':shared,'assumptionDifferences':mismatches,'segments':segments,'objections':{'original':objections(ar),'revised':objections(br)},'recommendations':{'original':ar.get('recommendations'),'revised':br.get('recommendations')},'limitations':['Synthetic comparison, not a randomized human experiment. Differences may reflect model variability.','Text variations are hypothetical; original media remains unchanged.']}
