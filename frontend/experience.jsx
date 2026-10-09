import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import { AnimatePresence, MotionConfig, motion, useReducedMotion, useScroll, useTransform } from 'motion/react';
import { ArrowUpRight, Play, Plus, Upload, Link2, Film, UsersRound, Fingerprint, ScanEye, Sparkles, SlidersHorizontal, Check, ChevronRight, CircleHelp, History, GitCompareArrows, Library, Settings2, MessageCircle, CircleDot, Pause } from 'lucide-react';
import './experience.css';

const roots = new Map();
let pendingDraft = null;
const go = page => window.navigate(page);
const ease = [0.22, 1, 0.36, 1];

function mount(host, component) {
  if (!host) return;
  unmount(host);
  const root = createRoot(host);
  roots.set(host, root);
  flushSync(() => root.render(<MotionConfig reducedMotion="user">{component}</MotionConfig>));
}
function unmount(host) {
  const root = roots.get(host);
  if (root) { root.unmount(); roots.delete(host); }
}
function dispose() {
  for (const [host, root] of roots) {
    if (host.closest('#main')) { root.unmount(); roots.delete(host); }
  }
}
function Mark({ small = false }) {
  return <svg className={small ? 'ripple-mark small' : 'ripple-mark'} viewBox="0 0 40 40" aria-hidden="true"><path d="M8 20c0-8 5-14 12-14s12 6 12 14-5 14-12 14S8 28 8 20Z"/><path d="M14 20c0-5 2.5-9 6-9s6 4 6 9-2.5 9-6 9-6-4-6-9Z"/><path d="M20 3v34"/></svg>;
}
function Brand() { return <button className="r-brand" aria-label="Ripple home" onClick={() => go('home')}><Mark/>ripple</button>; }
function Pill({ children, onClick, secondary = false, ...props }) {
  return <motion.button whileHover={{ y: -2 }} whileTap={{ scale: .98 }} className={`r-pill ${secondary ? 'secondary' : ''}`} onClick={onClick} {...props}>{children}</motion.button>;
}
function Reveal({ children, className = '', delay = 0 }) {
  const reduced = useReducedMotion();
  return <motion.div className={className} initial={reduced ? false : { opacity: 0, y: 25 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .12 }} transition={{ duration: .7, delay, ease }}>{children}</motion.div>;
}

function Constellation({ active = 0 }) {
  const points = Array.from({ length: 68 }, (_, i) => {
    const angle = i * 2.39996, radius = 26 + Math.sqrt(i / 68) * 205;
    return { x: 280 + Math.cos(angle) * radius, y: 220 + Math.sin(angle) * radius * .8, i };
  });
  return <svg className="r-constellation" viewBox="0 0 560 440" role="img" aria-label="Illustrative audience connections, not live results">
    {[75,130,185].map(r => <ellipse key={r} cx="280" cy="220" rx={r * 1.1} ry={r * .8} className="constellation-orbit"/>)}
    {points.flatMap((p,i) => points.slice(i+1).filter(q => Math.hypot(p.x-q.x,p.y-q.y)<70).map(q=><path key={`${i}-${q.i}`} className="constellation-edge" d={`M${p.x} ${p.y}L${q.x} ${q.y}`}/>))}
    {points.map(p => <circle key={p.i} className={`art-node constellation-dot ${p.i % 3 === active ? 'lit' : ''}`} cx={p.x} cy={p.y} r={p.i%9===0?5:3} style={{ animationDelay: `${-p.i/6}s` }}/>) }
    <circle cx="280" cy="220" r="28" className="constellation-center"/><path d="M265 220q15-28 30 0-15 28-30 0Z" className="constellation-glyph"/>
  </svg>;
}

function Rehearsal({ paused }) {
  const [idea, setIdea] = useState('');
  const [file, setFile] = useState(null);
  const [source, setSource] = useState('upload');
  const fileInput = useRef(null);
  const ref = useRef(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] });
  const y = useTransform(scrollYProgress, [0,1], [26,-26]);
  const start = event => {
    event.preventDefault();
    pendingDraft = { angle: idea, file, sourceType: source };
    go('new');
  };
  return <section className={`r-rehearsal ${paused ? 'motion-paused' : ''}`} ref={ref} aria-label="Start a content rehearsal">
    <div className="r-atmosphere" aria-hidden="true"><i/><i/><i/><i/></div>
    <div className="r-ruler left" aria-hidden="true"/><div className="r-ruler right" aria-hidden="true"/>
    <span className="r-scene-label">THE SPACE BETWEEN AN IDEA AND PUBLISH.</span>
    <motion.div className="rehearsal-float float-a" style={{ y: reduced || paused ? 0 : y }} aria-hidden="true"><div className="portrait-dot peach"><UsersRound size={19}/></div><span>Your intended audience<small>Start with the people who matter.</small></span></motion.div>
    <motion.div className="rehearsal-float float-b" style={{ y: reduced || paused ? 0 : y }} aria-hidden="true"><div className="portrait-dot plum"><ScanEye size={18}/></div><span>A fresh perspective<small>See beyond your usual audience.</small></span></motion.div>
    <div className="rehearsal-float float-c" aria-hidden="true"><Fingerprint size={20}/><span>Independent points of view</span></div>
    <motion.form className="rehearsal-composer" onSubmit={start} initial={reduced ? false : { y: 35, rotateX: 5, opacity: 0 }} whileInView={{ y: 0, rotateX: 0, opacity: 1 }} viewport={{ once: true }} transition={{ duration: .9, ease }}>
      <div className="composer-top"><div className="composer-dots"><i/><i/><i/></div><span>ripple / your next post</span><Film size={16}/></div>
      <div className="composer-paper"><label htmlFor="contentIdea">What are you putting into the world?</label><textarea id="contentIdea" value={idea} maxLength={3000} onChange={e=>setIdea(e.target.value)} placeholder="A product reveal? Your next Reel? An idea you can’t stop thinking about…"/><div className="composer-file"><button type="button" onClick={()=>fileInput.current.click()}><Plus size={16}/>{file ? file.name : 'Attach a video'}</button><span>or start with an idea</span></div><input ref={fileInput} type="file" accept=".mp4,.mov,.webm" aria-label="Attach a video for your simulation" hidden onChange={e=>{setFile(e.target.files[0]||null);setSource('upload')}}/></div>
      <div className="composer-bottom"><div className="composer-source" aria-label="Content source"><button type="button" aria-pressed={source==='upload'} className={source==='upload'?'selected':''} onClick={()=>setSource('upload')}><Upload size={14}/>Video</button><button type="button" aria-pressed={source==='link'} className={source==='link'?'selected':''} onClick={()=>setSource('link')}><Link2 size={14}/>Link</button></div><Pill type="submit" data-go="new">Find my audience’s perspective <ArrowUpRight size={16}/></Pill></div>
    </motion.form>
    <div className="r-rehearsal-note"><span className="r-live-dot"/>Your idea stays in this browser until you review and run a simulation.</div>
  </section>;
}

const perspectives = [
  { name: 'The people you’re creating for', kicker: '01 / TARGET AUDIENCE', text: 'Give your idea the right context. Describe who they are, what they care about, and what you hope they take away.', icon: UsersRound },
  { name: 'The people you didn’t expect', kicker: '02 / OUTSIDE PERSPECTIVES', text: 'Explore how your message might land outside its intended audience. Find the context newcomers could be missing.', icon: ScanEye },
  { name: 'The reason behind the reaction', kicker: '03 / INDIVIDUAL REASONING', text: 'Select a simulated viewer to read what connected, what confused them, and what they would need to see next.', icon: Fingerprint },
];
function PerspectiveSection() {
  const [active, setActive] = useState(0);
  return <section className="r-perspectives" id="how-it-works"><Reveal className="r-section-heading"><span className="r-kicker">DIFFERENT PEOPLE. DIFFERENT REASONS.</span><h2>There’s an audience.<br/>And then there’s <em>your audience.</em></h2><p>Explore the perspectives behind the metrics.<br/>Because “they liked it” only tells half the story.</p></Reveal><div className="perspectives-stage"><div className="perspective-visual"><span className="visual-corner">THE AUDIENCE LENS</span><Constellation active={active}/><span className="visual-foot">Illustration · Your real map comes from saved reactions</span></div><div className="perspective-tabs" role="group" aria-label="Explore audience perspectives">{perspectives.map((p,i)=>{const Icon=p.icon;return <button key={p.name} aria-pressed={active===i} id={`perspective-tab-${i}`} onKeyDown={e=>{if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();const next=(active+(e.key==='ArrowDown'?1:2))%3;setActive(next);document.getElementById(`perspective-tab-${next}`).focus()}}} className={`perspective-tab ${active===i?'active':''}`} onClick={()=>setActive(i)}><span className="perspective-icon"><Icon size={21}/></span><span><small>{p.kicker}</small><strong>{p.name}</strong>{active===i&&<motion.span className="perspective-description"  initial={{opacity:0}} animate={{opacity:1}}>{p.text}</motion.span>}</span><ArrowUpRight size={18}/></button>})}</div></div></section>;
}

function Landing() {
  const [paused, setPaused] = useState(false);
  const reduced = useReducedMotion();
  return <div className={`r-experience ${paused || reduced ? 'motion-paused' : ''}`}>
    <nav className="r-nav" aria-label="Introduction"><Brand/><div className="r-nav-links"><a href="#how-it-works">The audience lens</a><a href="#the-process">How it works</a><a href="#built-for">Made for you</a></div><Pill secondary onClick={()=>go('studio')} data-go="studio">Open Studio <ArrowUpRight size={16}/></Pill></nav>
    <section className="r-hero"><Reveal><span className="r-kicker pill-kicker"><span className="r-live-dot"/>YOUR CONTENT. A LITTLE MORE PERSPECTIVE.</span><h1 id="hero-title">Every post starts<br/>a ripple.<span className="hero-gradient"> Make yours land.</span></h1></Reveal><Reveal className="r-hero-aside" delay={.15}><p>Meet the reactions before the real world does. An AI audience rehearsal for your next Reel, launch, or big idea.</p><Pill onClick={()=>go('new')} data-go="new">Simulate your audience <ArrowUpRight size={18}/></Pill><span className="hero-aside-note">Your creative instinct. A broader point of view.</span></Reveal><button className="r-motion-toggle" onClick={()=>setPaused(!paused)} aria-pressed={paused} aria-label={paused?'Play ambient animation':'Pause ambient animation'}>{paused?<Play size={13}/>:<Pause size={13}/>}<span>{paused?'Play motion':'Pause motion'}</span></button></section>
    <Rehearsal paused={paused}/>
    <div className="r-process-strip"><span>THINK BEFORE YOU PUBLISH.</span><span><Film size={15}/>Your content <ChevronRight size={14}/><UsersRound size={15}/>AI audience <ChevronRight size={14}/><MessageCircle size={15}/>Honest perspectives <ChevronRight size={14}/><Sparkles size={15}/>Your next edit</span></div>
    <PerspectiveSection/>
    <section className="r-process-section" id="the-process"><Reveal className="process-intro"><span className="r-kicker">A REHEARSAL, NOT A CRYSTAL BALL.</span><h2>From “will this work?”<br/>to “here’s what <em>I’ll try.”</em></h2><p>Keep your idea. Question the opening. Make one considered change at a time.</p><button className="r-text-button" onClick={()=>go('new')}>Start your first rehearsal <ArrowUpRight size={18}/></button></Reveal><div className="r-process-list">{[
      ['01','Bring the rough cut.','Upload your video or supply a link and transcript. Tell Ripple who should care and what you want them to remember.',Film],
      ['02','Listen to the differences.','Explore an interactive 2D or 3D audience map. Read individual reactions, replay the analysis, and question the evidence.',UsersRound],
      ['03','Give the next version a reason.','Get specific edits to try. Change a hook, caption, or audience and compare both versions without losing the original.',GitCompareArrows],
    ].map(([n,title,copy,Icon],i)=><Reveal className="r-process-item" delay={i*.05} key={n}><span>{n}</span><div><Icon size={24}/><h3>{title}</h3><p>{copy}</p></div><ArrowUpRight size={18}/></Reveal>)}</div></section>
    <section className="r-question-section"><span className="r-kicker">THE QUESTION BEHIND EVERY POST</span><h2>“Would they <em>stop scrolling?</em>”</h2><div className="r-question-tags"><span>Is the opening clear?</span><span>Who might share it?</span><span>What needs more proof?</span></div><p>Ask Ripple about your saved simulation.<br/>Get answers grounded in the reactions and evidence behind it.</p><Pill secondary onClick={()=>{go('studio').then(()=>window.openChat()).catch(error=>window.toast(error.message))}}>Explore with Ask Ripple <ArrowUpRight size={17}/></Pill></section>
    <section className="r-built-for" id="built-for"><Reveal><span className="r-kicker">FOR THE PEOPLE BEHIND THE POST</span><h2>You make the content.<br/>We bring <em>the perspectives.</em></h2></Reveal><div className="r-personas">{[['Creators','Find an opening that earns attention. A story that gets to the point. A reason to keep watching.','01'],['Social & creative teams','Pressure-test a campaign concept and bring the reasoning into your next creative conversation.','02'],['Founders & marketers','Find where your message needs clearer benefits, more context, or a little more proof.','03']].map(([title,copy,num])=><article key={num}><span>{num} /</span><h3>{title}</h3><p>{copy}</p></article>)}</div></section>
    <section className="r-closing"><Mark/><span className="r-kicker">THE NEXT POST IS YOURS.</span><h2>Make a little<br/><span>room for perspective.</span></h2><Pill onClick={()=>go('new')} data-go="new">Create your first ripple <ArrowUpRight size={18}/></Pill><p>Simulated perspectives. Real creative decisions.<br/>Exploration, not a promise of performance.</p></section><footer className="r-footer"><Brand/><span>INDEPENDENT PERSPECTIVES / INTENTIONAL CONTENT</span><button onClick={()=>go('method')}>Method & assumptions <ArrowUpRight size={14}/></button></footer>
  </div>;
}

function IntakeCompanion({ form }) {
  const [state, setState] = useState({});
  const [section, setSection] = useState(0);
  useEffect(()=>{
    const sync=()=>setState(Object.fromEntries(new FormData(form)));
    sync();form.addEventListener('input',sync);form.addEventListener('change',sync);
    const observer=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting)setSection(Number(e.target.dataset.stepIndex))},{rootMargin:'-15% 0px -60% 0px'});
    form.querySelectorAll(':scope > .card').forEach((el,i)=>{el.dataset.stepIndex=i;observer.observe(el)});
    return()=>{form.removeEventListener('input',sync);form.removeEventListener('change',sync);observer.disconnect()};
  },[form]);
  const jump=i=>form.querySelectorAll(':scope > .card')[i]?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
  return <div className="intake-companion"><div className="intake-chapter"><Mark small/><span>YOUR CONTENT REHEARSAL</span></div><h2>A post with<br/><em>a point of view.</em></h2><p>Build a little context.<br/>Get a lot more perspective.</p><nav className="intake-stages" aria-label="Simulation setup sections">{[['The content','Give us something to react to.',Film],['The audience','Tell us who should care.',UsersRound],['The rehearsal','Set the size. Review. Begin.',SlidersHorizontal]].map(([title,copy,Icon],i)=><button key={title} className={section===i?'active':''} aria-current={section===i?'step':undefined} onClick={()=>jump(i)}><span><Icon size={18}/></span><div><b>{title}</b><small>{copy}</small></div>{i<section?<Check size={14}/>:<ChevronRight size={14}/>}</button>)}</nav><div className="brief-receipt"><span>YOUR CREATIVE BRIEF</span><h3>{state.title||'An idea, taking shape.'}</h3><dl><dt>FOR</dt><dd>{state.audience||'Your audience goes here.'}</dd><dt>ON</dt><dd>{state.platform||'Instagram'}</dd><dt>WITH</dt><dd>{state.size||25} simulated points of view</dd></dl><div className="receipt-bottom"><span className="r-live-dot"/>Saved when you run the simulation</div></div><p className="intake-note"><CircleHelp size={15}/>Synthetic viewers help explore creative decisions. They don’t predict real performance.</p></div>;
}

function ContentRibbon({ row }) {
  const [expanded,setExpanded]=useState(false);
  const reduced=useReducedMotion();
  return <div className="content-ribbon"><button className="content-ribbon-toggle" onClick={()=>setExpanded(!expanded)} aria-expanded={expanded} aria-controls="contentBriefDetail"><div className="content-thumbnail"><Film size={20}/></div><div><small>THE CONTENT BEHIND THESE REACTIONS</small><strong>{row.payload.platform} <span>/</span> {row.payload.goal}</strong></div><span className="ribbon-audience"><UsersRound size={15}/>{row.payload.size} perspectives</span><Plus size={16} className={expanded?'rotated':''}/></button><AnimatePresence initial={false}>{expanded&&<motion.div id="contentBriefDetail" className="content-ribbon-detail" initial={reduced?false:{height:0,opacity:0}} animate={{height:'auto',opacity:1}} exit={{height:0,opacity:0}} transition={{duration:reduced?0:.25}}><div><small>THE IDEA</small><p>{row.payload.angle}</p></div><div><small>THE INTENDED AUDIENCE</small><p>{row.payload.audience}</p></div><div><small>CALL TO ACTION</small><p>{row.payload.cta||'No call to action supplied.'}</p></div></motion.div>}</AnimatePresence></div>;
}

const navIcons={studio:CircleDot,history:History,compare:GitCompareArrows,library:Library,new:Plus,method:CircleHelp,settings:Settings2};
function installIcons(){
  document.querySelectorAll('.sidebar .nav').forEach(button=>{const Icon=navIcons[button.dataset.page]||MessageCircle;mount(button.querySelector('span'),<Icon size={19} strokeWidth={1.65}/>)});
  document.querySelectorAll('.sidebar .brand .logo').forEach(host=>mount(host,<Mark small/>));
}

window.RippleExperience={
  dispose,
  landing(host){mount(host,<Landing/>);},
  intake(){
    const form=document.querySelector('#testForm');if(!form)return;
    if(pendingDraft){
      const draft=pendingDraft;pendingDraft=null;
      form.elements.angle.value=draft.angle||'';
      if(draft.sourceType==='link')form.querySelector('[data-source="link"]').click();
      if(draft.file){const transfer=new DataTransfer();transfer.items.add(draft.file);const input=form.querySelector('#video');input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));}
    }
    const host=document.querySelector('.aside-info');host.replaceChildren();mount(host,<IntakeCompanion form={form}/>);
  },
  studio(row){const host=document.createElement('div');host.id='contentRibbon';document.querySelector('#studioKpis')?.before(host);mount(host,<ContentRibbon row={row}/>);},
  icons:installIcons,
};
