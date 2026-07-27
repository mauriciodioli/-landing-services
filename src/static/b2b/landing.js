(()=>{'use strict';const menu=document.querySelector('#sideMenu'),scrim=document.querySelector('#scrim'),trigger=document.querySelector('#menuTrigger'),close=document.querySelector('#menuClose');const setMenu=open=>{menu.classList.toggle('open',open);scrim.classList.toggle('open',open);menu.setAttribute('aria-hidden',String(!open));trigger.setAttribute('aria-expanded',String(open));document.body.style.overflow=open?'hidden':''};trigger?.addEventListener('click',()=>setMenu(true));close?.addEventListener('click',()=>setMenu(false));scrim?.addEventListener('click',()=>setMenu(false));menu?.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>setMenu(false)));document.addEventListener('keydown',e=>{if(e.key==='Escape')setMenu(false)});document.querySelectorAll('.drawer-toggle').forEach(button=>button.addEventListener('click',()=>{const item=button.closest('.drawer-item'),open=item.classList.toggle('open');button.setAttribute('aria-expanded',String(open))}));document.querySelector('#year').textContent=new Date().getFullYear()})();

(function(){
	'use strict';
	const menus = [document.querySelector('#navMenu'), document.querySelector('#sideMenu')].filter(Boolean);
	if (!menus.length) return;

	function renderAdminLinks(){
		const token = sessionStorage.getItem('participants-admin-token');
		const creds = sessionStorage.getItem('participants-admin-credentials');
		menus.forEach(menu => {
			menu.querySelectorAll('.nav-admin-item').forEach(n=>n.remove());
			const li = document.createElement('li');
			li.className = 'nav-admin-item';
			if (token || creds){
				li.innerHTML = '<a href="/admin/participantes" class="navbar__link">Panel admin</a> <a href="#" id="logoutBtn" class="navbar__link">Cerrar sesión</a>';
			} else {
				li.innerHTML = '<a href="/login" class="navbar__link">Acceso admin</a>';
			}
			// Insert after Contact link if available to preserve requested position
			let contactLi = null;
			const contactAnchor = menu.querySelector('a[href*="#contacto"]') || menu.querySelector('a[href$="/contacto"]') || menu.querySelector('a.navbar__link[href="index.html#contacto"]');
			if (contactAnchor) contactLi = contactAnchor.closest('li');
			if (contactLi && contactLi.parentNode) {
				contactLi.parentNode.insertBefore(li, contactLi.nextSibling);
			} else {
				menu.appendChild(li);
			}
		});

		const btn = document.getElementById('logoutBtn');
		if (btn){
			btn.addEventListener('click', async (e)=>{
				e.preventDefault();
				const t = sessionStorage.getItem('participants-admin-token');
				if (t){
					try{ await fetch('/auth/logout', { method: 'POST', headers: { 'Authorization': 'Bearer '+t } }); }catch(err){}
				}
				sessionStorage.removeItem('participants-admin-token');
				sessionStorage.removeItem('participants-admin-credentials');
				location.href = '/';
			});
		}
	}

	renderAdminLinks();
	window.addEventListener('storage', renderAdminLinks);
})();