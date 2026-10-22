// Pointer interaction does not cancel vertical page scrolling on touch screens.
export function bindInteraction(element,state,{select,requestFrame}) {
  let pointer=null, moved=false, startX=0, startY=0, previousX=0, previousY=0;
  const handlers = [];
  function listen(name,fn) { element.addEventListener(name,fn); handlers.push([name,fn]); }
  listen('pointerdown',event => {
    if (event.button !== 0) return;
    pointer=event.pointerId; moved=false; startX=previousX=event.clientX; startY=previousY=event.clientY;
    element.setPointerCapture(pointer); state.interacting=true;
  });
  listen('pointermove',event => {
    if (pointer===event.pointerId) {
      const dx=event.clientX-previousX,dy=event.clientY-previousY;
      if (Math.hypot(event.clientX-startX,event.clientY-startY)>5) moved=true;
      state.targetY+=dx*0.008;
      state.targetX=Math.max(-1,Math.min(1,state.targetX+dy*0.005));
      previousX=event.clientX;previousY=event.clientY;
      state.lastInput=performance.now();requestFrame();
    } else if (event.pointerType==='mouse') {
      const rect=element.getBoundingClientRect();
      state.hoverY=(event.clientX-rect.left)/rect.width-0.5;
      state.hoverX=((event.clientY-rect.top)/rect.height-0.5)*0.12;
      state.lastInput=performance.now();requestFrame();
    }
  });
  const release=event => {
    if (pointer!==event.pointerId) return;
    if (!moved && event.type==='pointerup') select(event);
    pointer=null; state.interacting=false; state.lastInput=performance.now();requestFrame();
  };
  listen('pointerup',release);listen('pointercancel',release);listen('lostpointercapture',release);
  listen('pointerleave',() => {state.hoverX=state.hoverY=0;requestFrame();});
  return () => { for (const [name,fn] of handlers) element.removeEventListener(name,fn); };
}
