(()=>{
'use strict';
const style=document.createElement('style');
style.textContent='.external-open{display:none}#externalLightbox{width:min(1000px,calc(100% - 20px));padding:0;background:#17131d}#externalLightbox iframe{display:block;width:100%;height:min(80dvh,56.25vw);min-height:240px;border:0}#externalLightbox.is-expanded{position:fixed;inset:0;width:100dvw;max-width:none;height:100dvh;max-height:none;margin:0;border:0;border-radius:0}#externalLightbox.is-expanded iframe{width:100%;height:100%;max-height:none}@media(max-width:640px),(max-height:640px) and (orientation:landscape){.external-item iframe{pointer-events:none}.external-open{display:block;position:absolute;inset:0;width:100%;height:240px;border-radius:0;background:transparent;color:transparent}.external-open:focus-visible{outline:3px solid #7162b8;outline-offset:-3px}}';
document.head.append(style);
const dialog=document.createElement('dialog');
dialog.id='externalLightbox';
dialog.innerHTML='<button class="close" type="button" aria-label="Cerrar">×</button><iframe title="Video externo" sandbox="allow-scripts allow-same-origin allow-presentation" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>';
document.body.append(dialog);
const fullscreenButton=document.createElement('button');
fullscreenButton.type='button';
fullscreenButton.className='fullscreen';
fullscreenButton.setAttribute('aria-label','Pantalla completa');
fullscreenButton.title='Pantalla completa';
fullscreenButton.textContent='⛶';
Object.assign(fullscreenButton.style,{position:'absolute',zIndex:'1',top:'10px',left:'50%',transform:'translateX(-50%)',minHeight:'36px',padding:'6px 10px',background:'rgba(23,19,29,.78)',color:'#fff'});
dialog.append(fullscreenButton);
const updateFullscreenButton=()=>{const active=dialog.classList.contains('is-expanded');fullscreenButton.textContent=active?'×':'⛶';fullscreenButton.setAttribute('aria-label',active?'Salir de pantalla completa':'Pantalla completa');fullscreenButton.title=fullscreenButton.getAttribute('aria-label')};
dialog.querySelector('.close').onclick=()=>{dialog.classList.remove('is-expanded');updateFullscreenButton();dialog.querySelector('iframe').src='';dialog.close()};
fullscreenButton.onclick=()=>{dialog.classList.toggle('is-expanded');updateFullscreenButton()};
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-external-embed]');
  if(!button)return;
  dialog.classList.remove('is-expanded');updateFullscreenButton();
  dialog.querySelector('iframe').src=button.dataset.externalEmbed;
  dialog.showModal();
});
})();
