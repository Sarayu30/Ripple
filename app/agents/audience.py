from ..simulation import *
from .skills import instruction

async def run(state, runtime):
    row=state["row"]; payload=row["payload"]; directory=runtime.directory
    provider=runtime.provider; semaphore=runtime.semaphore; event=runtime.event; live=runtime.live
    store.update(row["id"],stage='Creating audience personas',progress=15)
    profiles = cached(directory,'profiles.json') or []
    outside_count=round(payload['size']*payload.get('outsidePercent',0)/100)
    target_count=payload['size']-outside_count
    while len(profiles)<payload['size']:
        group='target' if len(profiles)<target_count else 'outside'
        boundary=target_count if group=='target' else payload['size']
        count=min(5,boundary-len(profiles))
        audience=payload['audience'] if group=='target' else payload.get('outsideAudience') or ('Adjacent viewers outside this intended audience, with other priorities and low or uncertain product relevance: '+payload['audience'])
        async with semaphore:
            batch = await provider.json(Profiles,instruction('audience-segmentation') + f'Create exactly {count} distinct audience personas in cohort {group}. Tailor profiles to the supplied audience. Use the requested archetypes in order. Describe specific motivations, expertise, objections and viewing contexts. Do not stereotype protected traits or assume unsupported demographics.', {'audience':audience,'archetypes':[ARCHETYPES[(len(profiles)+i)%len(ARCHETYPES)] for i in range(count)],'alreadyUsed':[p['personaName'] for p in profiles]})
        if len(batch.personas)!=count: raise ProviderError('Persona generation returned the wrong count. Retry uses saved profiles.',code='persona_count')
        for p in batch.personas:
            value=p.model_dump()
            value['personaName']=f'{len(profiles)+1:03d} · {value["personaName"]}'
            value['personaType']=ARCHETYPES[len(profiles)%len(ARCHETYPES)]
            value['audienceGroup']=group
            profiles.append(value)
        checkpoint(directory,'profiles.json',profiles)
        # Show real generated profiles as they arrive; don't fabricate waiting identities.
        previous_events=live['events'];live=initial_network(profiles);live['events']=previous_events
        runtime.live=live
        event({'kind':'profiles','message':f'{len(profiles)} / {payload["size"]} distinct profiles created.'})
        store.update(row["id"],progress=15+round(10*len(profiles)/payload['size']))
    runtime.live=live
    return {"profiles":profiles}
