/* Real Chromium checks and public documentation captures using isolated fixtures.
 * No Groq requests, private media, credentials, or production records are read.
 */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const {chromium}=require('../artifacts/ui-check/node_modules/playwright');
const metrics={hookScore:76,retentionScore:67,clarityScore:80,relevanceScore:78,trustScore:62,shareIntent:56,saveIntent:72,commentIntent:42,clickIntent:48,conversionIntent:35,likeIntent:70,followIntent:40};
const profiles=Array.from({length:25},(_,i)=>({personaName:String(i+1).padStart(3,'0')+' · '+['Independent designer','Studio founder','Creative freelancer','Brand strategist','Curious newcomer'][i%5],personaType:['Independent designers','Studio founders','Creative freelancers','Brand strategists','Outside audience'][i%5],background:'A sample creative professional exploring better project workflows.',motivation:'Turn a useful idea into a practical habit.',skepticism:'Needs a concrete example before trusting a new workflow.',viewingContext:'A quick scroll during a break.',audienceGroup:i%5===4?'outside':'target'}));
const reactions=profiles.map((p,i)=>({...metrics,personaName:p.personaName,personaType:p.personaType,clarityScore:i%5===4?55:85,likelyAction:i%5===0?'share':i%5===4?'scroll':'save',wouldStop:i%5!==4,wouldFinish:i%5!==4,sentiment:i%7===6?'negative':i%5===4?'neutral':'positive',reaction:'The three-step checklist feels useful. I would save it for my next client project, but I want to see the finished result first.',objection:'The promise is clear; the proof comes too late.',recommendedEdit:'Open with the finished mood board, then show the three steps.',understood:'A repeatable workflow for a stronger client mood board.',shareReason:'A practical checklist could help another designer.',emotion:'curiosity',confusion:'How long does each step take?'}));
const recommendations={topEdits:['Lead with the finished mood board, then reveal the process.','Put one short instruction on screen for each step.','End with a specific save-for-later prompt.'],alternativeHook:'A stronger mood board in three deliberate steps.',caption:'Start with a clear direction. Build a board your client can feel.',cta:'Save these three steps for your next client brief.',cover:'The finished mood board beside the initial brief.',abVariants:['Result-first opening','Question-first opening'],keep:['The practical three-step structure'],sources:['viewer:0','analysis']};
const result={analysis:{summary:'A short Reel introduces a three-step mood board workflow for freelance designers.',hook:'The benefit appears before an example of the finished result.',dropOff:'Viewers may scroll while waiting for visual proof.',comprehension:'The three steps are easy to identify.',ctaStrength:'The save prompt supports practical reuse.',visualClarity:'No source video is included in this documentation fixture.',pacing:'A proposed result-first opening could clarify the value sooner.',productVisibility:'Not applicable',shareableMoment:'The concise three-step checklist.',onScreenText:[],captions:[],scenes:[],limitations:['Documentation fixture, not a model-generated prediction.']},outcome:{metrics,verdict:'Clear idea. Earlier proof could help.',segments:profiles.slice(0,5).map(p=>({name:p.personaType,count:5,relevance:78,share:56,dominantReaction:'save',insight:'Show the result before explaining the process.'})),assumptions:{waveDecay:.65,shareRealizationPrior:.06},confidence:50,reachRange:[650,1400],engagementRate:8.4,waves:[{label:'Initial exposure',reach:1000},{label:'First sharing wave',reach:85}],sentiments:{positive:17,neutral:5,negative:3},emotions:{curiosity:25}},recommendations,insights:{summary:'The structure resonates with the intended audience. Viewers want a concrete example of the outcome earlier in the opening.',patterns:[{finding:'Visual proof makes the promise easier to assess.',sources:['viewer:0']}],disagreements:[{finding:'Outside viewers need more context.',sources:['viewer:4']}]},personas:reactions,profiles,evidence:{transcript:true,caption:true},limitations:['Example data for documentation only. Synthetic panels are exploratory.'],provenance:[{id:'analysis',kind:'AI interpretation',description:'The supplied transcript describes three workflow steps.'},{id:'viewer:0',kind:'synthetic reaction',description:'Sample feedback: show the finished result first.'}],failedAgents:{}};
const payload={title:'The mood board Reel',audience:'Freelance designers preparing their next client pitch',angle:'A practical three-step mood board workflow',goal:'engagement',platform:'Instagram',sourceType:'link',size:25,caption:'Three steps to a stronger client mood board.',cta:'Save the checklist',seedReach:1000,contactsPerShare:8};
const row={id:'example-original',created:'2026-10-07T09:00:00Z',title:'The mood board Reel',status:'completed',stage:'Complete',progress:100,payload,result};
const revised={...row,id:'example-revised',title:'The mood board Reel · Result-first opening'};
const stages=['content_analysis','audience_research','viewer_simulation','propagation_analyst','insights_analyst','creative_strategist'];
const live={nodes:profiles.map((profile,i)=>{const a=i*2.4,r=.12+Math.sqrt(i/25)*.32;return {id:String(i),profile,cohort:i%5===4?'outside':'target',status:'completed',reaction:reactions[i],x:.5+Math.cos(a)*r,y:.5+Math.sin(a)*r,z:Math.sin(i)*.22}}),links:profiles.flatMap((_,i)=>[{source:String(i),target:String((i+1)%25)},{source:String(i),target:String((i+5)%25)}]),events:[...stages.map((agent,i)=>({seq:i,kind:'stage_complete',agent,message:agent.replaceAll('_',' ')+' complete',at:row.created})),...reactions.map((_,i)=>({seq:i+6,kind:'reaction',nodeId:String(i),message:'A viewer returned their independent reaction.',at:row.created}))]};
const comparison={sharedPersonas:true,assumptionDifferences:[],metricDeltas:{hookScore:5,clarityScore:4,shareIntent:2,retentionScore:3,trustScore:6},segments:[{name:'Independent designers',shareDelta:2,original:{dominantReaction:'save'},revised:{dominantReaction:'share'}}],recommendations:{original:recommendations,revised:{...recommendations,topEdits:['Keep the result-first opening. Make the steps easier to scan.']}},objections:{original:[{count:7,text:'The proof comes too late.'}],revised:[{count:3,text:'The text moves quickly.'}]},limitations:['Documentation fixture; deltas do not establish a real improvement.']};
let submitted=0;
const server=http.createServer((req,res)=>{
 let body;if(req.url.startsWith('/api/')){
  if(req.url==='/api/config')body={providers:{groq:true},maxUploadMB:100,maxDuration:180};
  else if(req.url==='/api/tests')body=[row,revised];
  else if(req.url.endsWith('/live'))body=live;
  else if(req.url.includes('/compare/'))body=comparison;
  else if(req.url.endsWith('/versions')){if(req.method==='POST'){submitted++;body={id:revised.id}}else body=[row,revised]}
  else if(req.url.endsWith('/chat'))body=req.method==='POST'?{answer:'Start with the finished mood board. Viewers understand the promise, but want visual proof earlier. Test that opening with the same audience and compare the saved feedback.',sources:['viewer:0','analysis'],tools:['simulation_results']}:[];
  else body=req.url.includes(revised.id)?revised:row;
  res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify(body));return;
 }
 const name=req.url==='/'?'index.html':req.url.replace('/static/','');
 if(!/^[a-z.-]+$/.test(name)){res.writeHead(404);res.end();return}
 const file=path.join(__dirname,'../app/static',name);
 if(!fs.existsSync(file)){res.writeHead(404);res.end();return}
 res.setHeader('Content-Type',name.endsWith('.css')?'text/css':name.endsWith('.js')?'text/javascript':'text/html');res.end(fs.readFileSync(file));
});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
 const page=await browser.newPage({viewport:{width:1440,height:1050},deviceScaleFactor:1,reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base='http://127.0.0.1:'+server.address().port;
 const shot=async(name,fullPage=false)=>{await page.mouse.move(0,0);fs.mkdirSync('docs/screenshots',{recursive:true});await page.screenshot({path:'docs/screenshots/'+name+'.png',fullPage,animations:'disabled'})};
 await page.goto(base);await page.locator('#hero-title').waitFor();
 assert.equal(await page.locator('.art-node').count(),68);await shot('01-landing');
 await page.locator('[data-go=new]').first().click();await page.locator('#testForm').waitFor();await shot('02-new-simulation',true);
 await page.locator('[data-source=link]').click();assert(await page.locator('#linkArea').isVisible());assert(await page.locator('#testForm details').first().getAttribute('open')!==null);
 await page.locator('[data-page=studio]').click();await page.locator('.agent-node').first().waitFor();
 assert.equal(await page.locator('.agent-node').count(),25);
 // Label documentation examples in the page, without altering production templates.
 await page.evaluate(()=>{const badge=document.createElement('span');badge.id='documentationBadge';badge.textContent='DOCUMENTATION EXAMPLE · TEST FIXTURE DATA';badge.style.cssText='position:fixed;bottom:12px;left:250px;z-index:100;padding:8px 12px;background:#121917;color:#a0aea7;border:1px solid #2a3631;font:10px monospace;pointer-events:none';document.body.append(badge)});
 await page.locator('[data-node="0"]').click();assert((await page.locator('#agentInspector').innerText()).includes('Why they reacted'));
 await page.mouse.move(20,20);await shot('03-audience-map',true);
 await page.locator('#view3d').click();assert.equal(await page.locator('#view3d').getAttribute('aria-pressed'),'true');
 await page.locator('#view2d').click();
 await page.locator('#graphFilter').selectOption('outside');assert.equal(await page.locator('.agent-node[aria-hidden=false]').count(),5);await page.locator('#graphFilter').selectOption('negative');assert.equal(await page.locator('.agent-node[aria-hidden=false]').count(),3);await page.locator('#graphFilter').selectOption('all');
 await page.locator('#replayRange').fill('0');await page.locator('#replayRange').dispatchEvent('input');assert((await page.locator('#replayLabel').innerText()).includes('Event 1'));
 assert(!(await page.locator('#agentInspector').innerText()).includes('The three-step checklist'));
 await page.locator('#replayLive').click();assert((await page.locator('#agentInspector').innerText()).includes('The three-step checklist'));
 await page.locator('summary').filter({hasText:'Your content / full analysis'}).click();await page.locator('#fullAnalysis').click();assert((await page.locator('#workspaceDrawer').innerText()).includes('Sharing scenario'));await page.keyboard.press('Escape');
 await page.locator('#allSuggestions').click();assert((await page.locator('#workspaceDrawer').innerText()).includes('Cover / thumbnail'));await page.keyboard.press('Escape');
 await page.locator('#askNav').click();await page.locator('#chatQuestion').fill('What should I change in the opening?');await page.locator('#chatForm button[type=submit]').click();await page.locator('.chat-message:not(.user)').waitFor();await shot('04-ask-ripple');await page.keyboard.press('Escape');
 await page.locator('[data-page=compare]').click();await page.locator('#compareButton').click();await page.locator('#comparison table').waitFor();await shot('05-compare-versions',true);
 await page.locator('#createExperiment').click();await page.locator('[name=hook]').fill('Start with the finished mood board');await page.locator('[name=approved]').check();await page.locator('#experimentForm button[type=submit]').click();await page.locator('#networkCanvas').waitFor();assert.equal(submitted,1);
 await page.locator('#themeToggle').click();await shot('07-light-studio',true);assert.equal(await page.locator('html').getAttribute('data-theme'),'light');await page.locator('#themeToggle').click();
 await page.evaluate(()=>document.querySelector('#documentationBadge')?.remove());
 for(const width of [768,390]){
  await page.setViewportSize({width,height:900});
  for(const view of ['home','new','studio','history','compare','library','method','settings']){
   await page.evaluate(view=>navigate(view),view);if(view==='studio')await page.locator('#networkCanvas').waitFor();
   const sizes=await page.evaluate(()=>({full:document.documentElement.scrollWidth,viewport:innerWidth}));
   assert(sizes.full<=sizes.viewport+1,`${view} overflows at ${width}px: ${JSON.stringify(sizes)}`);
   if(width===390&&view==='home')await shot('06-mobile-landing',true);
  }
 }
 assert.deepEqual(errors,[]);console.log('PASS: Chromium navigation, 2D/3D, filters, replay, inspector, full analysis, suggestions, chat, approved versions, comparison, themes, and 16 responsive page checks. Seven screenshots captured.');
 }finally{await browser.close();server.close()}
})().catch(e=>{console.error(e);server.close();process.exitCode=1});
