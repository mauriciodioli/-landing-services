(()=>{
'use strict';
const style=document.createElement('style');
style.textContent='.external-open{display:none}#externalLightbox{width:min(1000px,calc(100% - 20px));padding:0;background:#17131d}#externalLightbox iframe{display:block;width:100%;height:min(80dvh,56.25vw);min-height:240px;border:0}#externalLightbox .close{position:absolute;z-index:1;top:10px;right:10px}@media(max-width:640px){.external-item iframe{pointer-events:none}.external-open{display:block;position:absolute;inset:0;width:100%;height:240px;border-radius:0;background:transparent;color:transparent}.external-open:focus-visible{outline:3px solid #7162b8;outline-offset:-3px}}';
document.head.append(style);
const dialog=document.createElement('dialog');
dialog.id='externalLightbox';
dialog.innerHTML='<button class="close" type="button" aria-label="Cerrar">×</button><iframe title="Video externo" sandbox="allow-scripts allow-same-origin allow-presentation" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>';
document.body.append(dialog);
dialog.querySelector('.close').onclick=()=>{dialog.querySelector('iframe').src='';dialog.close()};
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-external-embed]');
  if(!button)return;
  dialog.querySelector('iframe').src=button.dataset.externalEmbed;
  dialog.showModal();
});
})();
