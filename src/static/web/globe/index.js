import {activeCities,cityLabel} from './config.js';
const section=document.getElementById('global-presence');
if(section) {
  const lang=document.documentElement.lang.slice(0,2),cities=activeCities();
  const stage=section.querySelector('.globe-stage'),fallback=section.querySelector('.globe-fallback');
  const list=section.querySelector('.globe-cities'),label=section.querySelector('.globe-selection');
  const toggle=section.querySelector('.globe-toggle');
  let globe=null,loading=false,disposed=false,paused=window.matchMedia('(prefers-reduced-motion: reduce)').matches,pending=null;
  function select(city) {
    label.textContent=cityLabel(city,lang);
    list.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.city===city.id)));
  }
  cities.forEach(city=> {
    const button=document.createElement('button');button.type='button';button.dataset.city=city.id;button.setAttribute('aria-pressed','false');
    const star=document.createElement('span');star.setAttribute('aria-hidden','true');star.textContent='★';button.append(star,document.createTextNode(cityLabel(city,lang)));
    button.addEventListener('click',()=> {pending=city;select(city);if(globe)globe.focus(city);else load();});list.append(button);
  });
  const fail=()=>{globe?.dispose();globe=null;fallback.hidden=false;toggle.hidden=true;stage.dataset.state='fallback';};
  async function load() {
    if(loading||globe||disposed||stage.dataset.state==='fallback')return;loading=true;stage.dataset.loading='true';
    try {
      const {createGlobe}=await import('./renderer.js');
      if(disposed)return;
      globe=await createGlobe(stage,cities,lang,select);
      if(disposed){globe.dispose();return;}
      fallback.hidden=true;stage.dataset.state='ready';toggle.hidden=false;
      globe.setPaused(paused);toggle.textContent=paused?toggle.dataset.play:toggle.dataset.pause;toggle.setAttribute('aria-pressed',String(paused));
      if(pending)globe.focus(pending);
      globe.setVisible(section.getBoundingClientRect().bottom>0&&section.getBoundingClientRect().top<innerHeight);
    } catch(_) {fail();} finally {loading=false;}
  }
  toggle.addEventListener('click',()=>{paused=!paused;globe?.setPaused(paused);toggle.textContent=paused?toggle.dataset.play:toggle.dataset.pause;toggle.setAttribute('aria-pressed',String(paused));});
  stage.addEventListener('globe-failed',fail);
  const viewportObserver=new IntersectionObserver(entries=> {
    for(const entry of entries) {if(entry.isIntersecting)load();globe?.setVisible(entry.isIntersecting);}
  },{threshold:0.05});viewportObserver.observe(section);
  function dispose(){disposed=true;viewportObserver.disconnect();stage.removeEventListener('globe-failed',fail);globe?.dispose();}
  window.addEventListener('pagehide',dispose,{once:true});
  // BFCache restoration needs a fresh WebGL context and lifecycle observers.
  window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
}
