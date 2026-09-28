"""Auditable synthetic topology; propagation depends on actual LLM decisions."""
import math
from collections import Counter

FACTORS={'positive':1,'neutral':.65,'mixed':.75,'negative':.35}

def initial_network(profiles):
    n=len(profiles)
    nodes=[]
    group_counts=Counter(p.get('audienceGroup','target') for p in profiles)
    group_index=Counter()
    for i,p in enumerate(profiles):
        group=p.get('audienceGroup','target');local=group_index[group];group_index[group]+=1
        angle=local*math.pi*(3-math.sqrt(5));radius=math.sqrt((local+.5)/max(group_counts[group],1))
        center=.79 if group=='outside' else .37 if group_counts['outside'] else .5
        width=.17 if group=='outside' else .32 if group_counts['outside'] else .43
        nodes.append({'id':str(i),'profile':p,'x':round(center+width*radius*math.cos(angle),5),'y':round(.5+.43*radius*math.sin(angle),5),'z':round(math.sin(i*1.7)*.18,4),'cohort':p.get('audienceGroup','target'),'status':'pending','reaction':None,'wave':None,'parent':None,'exposure':None})
    links=[]
    for i,p in enumerate(profiles):
        # A fixed, inspectable assumed contact graph, never an actual follower graph.
        neighbors=sorted((j for j in range(n) if j!=i),key=lambda j:(0 if profiles[j]['personaType']==p['personaType'] else 1, (j-i)%max(n,1)))[:3]
        opposite=[j for j in range(n) if profiles[j].get('audienceGroup','target')!=p.get('audienceGroup','target')]
        bridge=opposite[i%len(opposite)] if opposite else None
        if bridge is not None and bridge not in neighbors: neighbors=neighbors[:2]+[bridge]
        for j in neighbors: links.append({'source':str(i),'target':str(j),'kind':'assumed-contact'})
    target=[x['id'] for x in nodes if x['cohort']=='target'] or [x['id'] for x in nodes]
    count=max(1,math.ceil(n*.16))
    buckets={}
    for id in target: buckets.setdefault(profiles[int(id)]['personaType'],[]).append(id)
    seeds=[];level=0
    while len(seeds)<min(count,len(target)):
        for bucket in buckets.values():
            if level<len(bucket) and len(seeds)<count: seeds.append(bucket[level])
        level+=1
    return {'version':2,'nodes':nodes,'links':links,'seedIds':seeds,'events':[],'wave':0,'complete':False,'assumptions':{'topology':'Synthetic contacts based on archetype similarity plus cohort bridges. Not a real follower graph.','seedFraction':.16,'shareThreshold':.28,'maxContactsPerShare':3,'maxWaves':4,'holdouts':'Unreached people are evaluated separately as direct-test holdouts and never counted as cascade reach.'}}

def spread_targets(network,frontier,visited):
    selected=[];reserved=set(visited)
    for id in frontier:
        node=next(n for n in network['nodes'] if n['id']==id);r=node.get('reaction')
        if not r: continue
        strength=r['shareIntent']/100*r['relevanceScore']/100*FACTORS[r['sentiment']]
        # stated sharing action OR meaningful weighted sharing intent, with a minimum score
        if strength<.28 or (r['likelyAction']!='share' and r['shareIntent']<60): continue
        budget=min(3,max(1,math.ceil(strength*3)))
        neighbors=[e['target'] for e in network['links'] if e['source']==id and e['target'] not in reserved]
        for dest in neighbors[:budget]:
            reserved.add(dest);selected.append((dest,id,round(strength,3)))
    return selected

def network_summary(network):
    nodes=network['nodes'];done=[n for n in nodes if n.get('reaction')]
    reached=[n for n in done if n.get('exposure') in ('seed','share')]
    cohorts={}
    for group in ('target','outside'):
        rows=[n for n in done if n['cohort']==group]
        cohorts[group]={'completed':len(rows),'planned':sum(n['cohort']==group for n in nodes),'reached':sum(n['cohort']==group for n in reached),'relevance':round(sum(n['reaction']['relevanceScore'] for n in rows)/len(rows),1) if rows else None,'shareIntent':round(sum(n['reaction']['shareIntent'] for n in rows)/len(rows),1) if rows else None}
    waves=[sum(n.get('wave')==i and n.get('exposure') in ('seed','share') and n.get('reaction') is not None for n in nodes) for i in range(4)]
    outside=cohorts['outside'];target=cohorts['target']
    verdict='Panel still forming' if not done else 'Target-only panel' if outside['planned']==0 else 'Insufficient outside-audience evidence' if outside['completed']==0 else 'Cross-audience interest' if outside['relevance']>=65 and outside['shareIntent']>=55 else 'Strong in-audience, limited breakout' if (target['relevance'] or 0)>=65 else 'Message needs a clearer audience fit'
    return {'completed':len(done),'failed':sum(n['status']=='failed' for n in nodes),'reached':len(reached),'cascadeDepth':max((n['wave'] for n in reached),default=0),'waves':waves,'cohorts':cohorts,'actions':dict(Counter(n['reaction']['likelyAction'] for n in done)),'breakout':verdict}
