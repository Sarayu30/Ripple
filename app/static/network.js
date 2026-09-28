/* Pure SVG network renderer. Positions are layout only; all reactions come from the server. */
class RippleNetwork {
  constructor(host,onSelect){
    this.host=host;this.onSelect=onSelect;this.zoom=1;this.pan={x:0,y:0};this.mode='2d';this.rotation=.3;this.filter='all';this.selected=null;this.cutoff=Infinity;this.data={nodes:[],events:[]};this.drag=null;
    host.innerHTML='<svg class="audience-svg" viewBox="0 0 1000 570" aria-label="Interactive AI audience network"><defs><pattern id="netDots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".8" fill="currentColor" opacity=".18"/></pattern></defs><rect width="1000" height="570" fill="url(#netDots)"/><g class="network-viewport"></g></svg><div class="graph-tooltip" role="tooltip" hidden></div>';
    this.svg=host.querySelector('svg');this.layer=host.querySelector('.network-viewport');this.tip=host.querySelector('.graph-tooltip');
    this.svg.addEventListener('wheel',e=>{e.preventDefault();this.zoom=Math.max(.6,Math.min(3,this.zoom*(e.deltaY<0?1.12:.89)));this.draw()},{passive:false});
    this.svg.addEventListener('pointerdown',e=>{if(e.target.closest('[data-node]'))return;this.drag={x:e.clientX,y:e.clientY,px:this.pan.x,py:this.pan.y,r:this.rotation};this.svg.setPointerCapture(e.pointerId)});
    this.svg.addEventListener('pointermove',e=>{if(!this.drag)return;const scale=1000/Math.max(1,this.svg.clientWidth);if(this.mode==='3d')this.rotation=this.drag.r+(e.clientX-this.drag.x)*.008;else this.pan={x:this.drag.px+(e.clientX-this.drag.x)*scale,y:this.drag.py+(e.clientY-this.drag.y)*scale};this.draw()});
    this.svg.addEventListener('pointerup',()=>this.drag=null);
    this.svg.addEventListener('pointercancel',()=>this.drag=null);
  }
  setData(data){this.data=data;this.draw()}
  setMode(mode){this.mode=mode;this.pan={x:0,y:0};this.draw()}
  reset(){this.zoom=1;this.pan={x:0,y:0};this.rotation=.3;this.draw()}
  visibleReaction(node){if(this.cutoff===Infinity||this.data.legacy)return node.reaction;return this.data.events.some(e=>e.seq<=this.cutoff&&e.nodeId===node.id&&['reaction','reused'].includes(e.kind))?node.reaction:null}
  position(n){let x=n.x-.5,y=n.y-.5,z=n.z||0;if(this.mode==='3d'){const xx=x*Math.cos(this.rotation)+z*Math.sin(this.rotation);z=-x*Math.sin(this.rotation)+z*Math.cos(this.rotation);x=xx;y=y*.88-z*.3}return{x:500+x*920,y:282+y*530,z}}
  color(n,r){if(!r)return n.status==='failed'&&this.cutoff===Infinity?'var(--net-fail)':'var(--net-pending)';if(r.likelyAction==='scroll'||!r.wouldStop)return'var(--net-scroll)';if(r.likelyAction==='share')return'var(--net-share)';return'var(--net-engaged)'}
  draw(){
    if(!this.layer)return;const nodes=this.data.nodes||[],points=new Map(nodes.map(n=>[n.id,this.position(n)]));
    const allows=n=>this.filter==='all'||this.filter===n.cohort||this.filter==='share'&&this.visibleReaction(n)?.likelyAction==='share'||this.filter==='scroll'&&this.visibleReaction(n)?.likelyAction==='scroll';
    let lines='';
    for(const n of nodes){if(!n.parent||!this.visibleReaction(n))continue;const from=points.get(n.parent),to=points.get(n.id);if(!from)continue;const active=this.selected===n.id||this.selected===n.parent;lines+=`<path d="M${from.x},${from.y} Q${(from.x+to.x)/2},${(from.y+to.y)/2-18} ${to.x},${to.y}" class="share-edge ${active?'selected-edge':''}" opacity="${active?1:.35}"/>`}
    this.layer.setAttribute('transform',`translate(${this.pan.x+500*(1-this.zoom)} ${this.pan.y+282*(1-this.zoom)}) scale(${this.zoom})`);
    this.layer.innerHTML=lines+nodes.slice().sort((a,b)=>points.get(a.id).z-points.get(b.id).z).map(n=>{const p=points.get(n.id),r=this.visibleReaction(n),selected=this.selected===n.id,size=(nodes.length>100?5.3:8)+(this.mode==='3d'?p.z*6:0);const hidden=!allows(n),label=`${n.profile.personaName}, ${n.cohort} audience, ${r?r.likelyAction:n.status}`;return `<g class="agent-node ${n.status==='evaluating'&&this.cutoff===Infinity?'evaluating':''}" data-node="${n.id}" transform="translate(${p.x} ${p.y})" role="button" tabindex="${hidden?-1:0}" aria-label="${esc(label)}" opacity="${hidden?.13:1}"><circle r="${Math.max(14,size)}" fill="transparent"/>${selected?`<circle r="${size+7}" class="selection-ring"/>`:''}${n.cohort==='outside'?`<rect x="${-size}" y="${-size}" width="${size*2}" height="${size*2}" rx="3" transform="rotate(45)" fill="${this.color(n,r)}"/>`:`<circle r="${size}" fill="${this.color(n,r)}"/>`}${r&&r.likelyAction==='share'?`<circle r="${size/3}" fill="var(--panel)"/>`:''}${n.exposure==='seed'?`<circle r="${size+3}" class="seed-ring"/>`:''}</g>`}).join('');
    this.layer.querySelectorAll('[data-node]').forEach(g=>{const n=nodes.find(n=>n.id===g.dataset.node);g.addEventListener('click',()=>{this.selected=n.id;this.tip.hidden=true;this.draw();this.onSelect(n)});g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();this.selected=n.id;this.draw();this.onSelect(n)}});g.addEventListener('pointerenter',e=>{const r=this.visibleReaction(n);this.tip.innerHTML=`<b>${esc(n.profile.personaName)}</b><span>${esc(n.profile.personaType)}</span><small>${esc(n.cohort)} audience · ${r?esc(r.likelyAction):esc(n.status)}</small>`;this.tip.hidden=false;const box=this.host.getBoundingClientRect();this.tip.style.left=Math.min(e.clientX-box.left+12,Math.max(0,box.width-240))+'px';this.tip.style.top=Math.max(10,e.clientY-box.top-85)+'px'});g.addEventListener('pointerleave',()=>this.tip.hidden=true)})
  }
  destroy(){this.host.innerHTML=''}
}
window.RippleNetwork=RippleNetwork;
