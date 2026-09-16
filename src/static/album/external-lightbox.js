(()=>{
'use strict';
const style=document.createElement('style');
style.textContent='.external-open{display:none}#externalLightbox{width:min(1000px,calc(100% - 20px));padding:0;background:#17131d}#externalLightbox iframe{display:block;width:100%;height:min(80dvh,56.25vw);min-height:240px;border:0}#externalLightbox .close{position:absolute;z-index:1;top:10px;right:10px}@media(max-width:640px){.external-item iframe{pointer-events:none}.external-open{display:block;position:absolute;inset:0;width:100%;height:240px;border-radius:0;background:transparent;color:transparent}.external-open:focus-visible{outline:3px solid #7162b8;outline-offset:-3px}}';
document.head.append(style);
const dialog=document.createElement('dialog');
dialog.id='externalLightbox';
dialog.innerHTML='<button class="close" type="button" aria-label="Cerrar">×</button><iframe title="Video externo" sandbox="allow-scripts allow-same-origin allow-presentation" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>';
document.body.append(dialog);
let sourceUrl='';
const fullscreenButton=document.createElement('button');
fullscreenButton.type='button';
fullscreenButton.className='fullscreen';
fullscreenButton.setAttribute('aria-label','Pantalla completa');
fullscreenButton.title='Pantalla completa';
fullscreenButton.textContent='⛶';
Object.assign(fullscreenButton.style,{position:'absolute',zIndex:'1',top:'10px',left:'10px',minHeight:'36px',padding:'6px 10px',background:'rgba(23,19,29,.78)',color:'#fff'});
dialog.append(fullscreenButton);
dialog.querySelector('.close').onclick=()=>{dialog.querySelector('iframe').src='';dialog.close()};
fullscreenButton.onclick=()=>{const frame=dialog.querySelector('iframe'),request=frame.requestFullscreen||frame.webkitRequestFullscreen;if(request)request.call(frame).catch(()=>{if(sourceUrl)window.open(sourceUrl,'_blank','noopener')});else if(sourceUrl)window.open(sourceUrl,'_blank','noopener')};
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-external-embed]');
  if(!button)return;
  sourceUrl=button.dataset.externalUrl||'';
  dialog.querySelector('iframe').src=button.dataset.externalEmbed;
  dialog.showModal();
});
})();
