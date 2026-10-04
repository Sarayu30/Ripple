"""Scoped read-only tools: the assistant cannot access arbitrary runs or files."""
from .. import store
from ..simulation import cached
from ..experiments import compare

TOOL_DESCRIPTIONS={
    'simulation_results':'Main analysis and synthetic viewer reactions with evidence IDs.',
    'audience_analytics':'Actual stored aggregate metrics and assumptions.',
    'segment_comparison':'Reactions and objections grouped by audience segment.',
    'version_comparison':'Compare this run with its direct parent, when present.',
    'content_evidence':'Available transcript, frame provenance and inferred content analysis.',
    'recommendations':'Saved creative suggestions and their source IDs.'
}

def simulation_evidence(row):
    """Read-time source compatibility for runs predating provenance catalogs.

    Viewer IDs use retrieve()'s result ordering. No stored results are rewritten
    and no new observations are invented.
    """
    result=row['result']
    evidence={item['id']:item for item in result.get('provenance') or []}
    if result.get('analysis'):
        evidence.setdefault('analysis',{'id':'analysis','kind':'AI interpretation','description':'Saved content analysis'})
    if result.get('outcome'):
        evidence.setdefault('propagation',{'id':'propagation','kind':'mathematical assumptions','description':'Saved outcome and assumptions'})
    for index,viewer in enumerate(result.get('personas') or []):
        source=f'viewer:{index}'
        evidence.setdefault(source,{'id':source,'kind':'synthetic reaction','description':'Saved reaction from '+viewer['personaName']})
    return list(evidence.values())


def retrieve(name,row):
    if name not in TOOL_DESCRIPTIONS: raise ValueError('Tool is not permitted.')
    r=row['result'];directory=store.MEDIA/row['id']
    if name=='audience_analytics': return r['outcome']
    if name=='segment_comparison': return {'segments':r['outcome']['segments'],'insights':r.get('insights'),'feedback':[{'id':f'viewer:{i}','segment':p['personaType'],'action':p['likelyAction'],'objection':p['objection'][:350]} for i,p in enumerate(r['personas'])]}
    if name=='recommendations': return r.get('recommendations')
    if name=='content_evidence': return {'analysis':r['analysis'],'evidence':r.get('provenance',[]),'limitations':r['limitations']}
    if name=='version_comparison':
        version=cached(directory,'experiment.json') or {}
        parent=store.get(version.get('parentId',''))
        return compare(parent,row) if parent and parent.get('result') else {'unavailable':'No saved parent results.'}
    return {'analysis':r['analysis'],'insights':r.get('insights'),'viewers':[{'id':f'viewer:{i}','name':p['personaName'],'action':p['likelyAction'],'reaction':p['reaction'][:350],'objection':p['objection'][:350],'edit':p['recommendedEdit'][:350]} for i,p in enumerate(r['personas'])]}
