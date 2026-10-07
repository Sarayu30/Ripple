/* Controls reuse the existing renderer, saved events and result payloads. */
let replayTimer=null,previewUrl=null;
function stopReplay(){clearTimeout(replayTimer);replayTimer=null}
function releasePreview(){if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=null}}
function bindExperience(){
 for(const mode of ['2d','3d'])$('#view'+mode).onclick=()=>{
  networkView.setMode(mode);
  for(const m of ['2d','3d']){const b=$('#view'+m);b.classList.toggle('selected',m===mode);b.setAttribute('aria-pressed',String(m===mode))}
 };
 $('#replayRange').oninput=()=>{stopReplay();$('#replayButton').textContent='Play replay';showReplay(Number($('#replayRange').value))};
 $('#replayLive').onclick=()=>{stopReplay();networkView.cutoff=Infinity;networkView.draw();$('#replayRange').value=$('#replayRange').max;$('#replayLabel').textContent='Latest reactions';$('#replayButton').textContent='Replay analysis';if(selectedAgent)renderInspector(studioData.nodes.find(n=>n.id===selectedAgent))};
 $('#replayButton').onclick=()=>{
  if(replayTimer){stopReplay();$('#replayButton').textContent='Continue replay';return}
  const range=$('#replayRange');if(networkView.cutoff===Infinity||Number(range.value)>=Number(range.max))range.value='0';
  $('#replayButton').textContent='Pause replay';
  const step=()=>{if(!networkView||!$('#replayRange'))return;const value=Number(range.value);showReplay(value);if(value>=Number(range.max)){stopReplay();$('#replayButton').textContent='Replay analysis';return}range.value=String(value+1);replayTimer=setTimeout(step,Number($('#replaySpeed').value))};step();
 };
}
function showReplay(index){
 const event=studioData.events[index];networkView.cutoff=event?.seq??-1;networkView.draw();
 $('#replayLabel').textContent='Event '+(index+1)+' / '+studioData.events.length;
 if(selectedAgent){const node=studioData.nodes.find(n=>n.id===selectedAgent);if(node)renderInspector(node)}
}
function viewerDetails(r){
 return '<details class="section-gap"><summary>View reasoning & engagement scores</summary>'+diagnostic('Attention',`${r.wouldStop?'Would stop':'Would keep scrolling'} · ${r.wouldFinish?'Would finish':'Would not finish'}`)+diagnostic('Why they might share',r.shareReason||'No rationale returned')+diagnostic('Emotion',r.emotion||r.sentiment)+diagnostic('Confusion',r.confusion||'None returned')+'<p class="help">Scores are AI-stated intent out of 100, not probabilities of real behavior.</p><div class="viewer-metrics">'+Object.entries(labels).filter(([k])=>Number.isFinite(r[k])).map(([k])=>score(k,r[k])).join('')+'</div></details>';
}
function updateExperience(t,n){
 const events=n.events||[],range=$('#replayRange');range.max=String(Math.max(0,events.length-1));
 $('#replayButton').disabled=events.length===0||n.legacy;range.disabled=events.length===0||n.legacy;
 if(!events.length)$('#replayLabel').textContent='No saved events yet';
 const r=t.result;
 $('#insightStory').innerHTML=r?'<article><h3>WHAT HAPPENED</h3><p>'+esc(r.outcome?.verdict||r.insights?.summary||'Your viewers have responded. Select a viewer to explore their feedback.')+'</p></article><article><h3>WHY IT HAPPENED</h3><p>'+esc(r.insights?.summary||r.analysis?.summary||'Review individual feedback and content evidence below.')+'</p></article>':'';
 if(!$('#workflowSteps'))$('.run-status').insertAdjacentHTML('afterend','<div class="workflow-steps" id="workflowSteps" aria-label="Analysis stages"></div>');
 const stages=[['content_analysis','Understand content'],['audience_research','Build audience'],['viewer_simulation','Collect reactions'],['propagation_analyst','Explore sharing'],['insights_analyst','Find patterns'],['creative_strategist','Suggest edits']];
 $('#workflowSteps').innerHTML=stages.map(([id,label])=>{const done=events.some(e=>e.agent===id&&e.kind==='stage_complete'),active=!done&&events.some(e=>e.agent===id&&e.kind==='stage_start');return '<span class="'+(done?'complete':active?'current':'')+'" title="'+id.replaceAll('_',' ')+'">'+(done?'✓ ':active?'◌ ':'')+label+'</span>'}).join('');
}
function openFullAnalysis(){
 const r=current?.result;if(!r)return;const o=r.outcome||{},a=r.analysis||{};
 openDrawer('Full content & audience analysis',(r.source?sourceCard(r.source):'')+'<p class="help">All scores and scenarios below come from this saved simulation.</p>'+Object.entries(o.metrics||{}).map(([k,v])=>score(k,v)).join('')+'<h3 class="section-gap">Sharing scenario</h3>'+diagnostic('Modeled reach range',(o.reachRange||[]).join(' – ')+' exposure opportunities; not unique viewers')+diagnostic('Modeled engagement',o.engagementRate===undefined?'Unavailable':o.engagementRate+'% under the stated conversion prior')+(o.waves||[]).map(w=>diagnostic(w.label,w.reach+' modeled exposures')).join('')+'<h3 class="section-gap">Content diagnostics</h3>'+Object.entries({summary:'Summary',hook:'Opening hook',dropOff:'Possible attention drop-off',comprehension:'Message comprehension',ctaStrength:'Call to action',visualClarity:'Visual clarity',pacing:'Pacing',productVisibility:'Product visibility',shareableMoment:'Shareable moment'}).map(([k,label])=>diagnostic(label,a[k]||'Unavailable')).join('')+(a.scenes||[]).map(s=>diagnostic(s.timestamp,s.description)).join('')+diagnostic('On-screen text',(a.onScreenText||[]).join(' · '))+diagnostic('Captions',(a.captions||[]).join(' · '))+'<h3 class="section-gap">Sentiment & emotion</h3>'+Object.entries(o.sentiments||{}).map(([k,v])=>diagnostic(k,v+' viewers')).join('')+Object.entries(o.emotions||{}).map(([k,v])=>diagnostic(k,v+' viewers')).join('')+'<h3 class="section-gap">Unfinished evaluations</h3>'+Object.entries(r.failedAgents||{}).map(([k,v])=>diagnostic(k,typeof v==='string'?v:JSON.stringify(v))).join('')+diagnostic('Recommendation status',r.recommendationError||'No recommendation error recorded'));
}
