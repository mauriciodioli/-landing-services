import * as THREE from './vendor/three.module.min.js';
import {SETTINGS,cityLabel} from './config.js';
import {bindInteraction} from './interaction.js';
const radians=degrees=>degrees*Math.PI/180;
export function coordinates(lat,lon,radius=1.018) {
  const phi=radians(lat),lambda=radians(lon);
  return new THREE.Vector3(radius*Math.cos(phi)*Math.cos(lambda),radius*Math.sin(phi),-radius*Math.cos(phi)*Math.sin(lambda));
}
function starTexture() {
  const canvas=document.createElement('canvas'); canvas.width=canvas.height=128;
  const ctx=canvas.getContext('2d');
  const glow=ctx.createRadialGradient(64,64,4,64,64,62);
  glow.addColorStop(0,'#fff4cdbb');glow.addColorStop(0.3,'#ffce6b70');glow.addColorStop(1,'#ffce6b00');
  ctx.fillStyle=glow;ctx.fillRect(0,0,128,128);
  ctx.beginPath();
  for(let i=0;i<10;i++) { const a=i*Math.PI/5-Math.PI/2,r=i%2?13:32; const x=64+Math.cos(a)*r,y=64+Math.sin(a)*r;i?ctx.lineTo(x,y):ctx.moveTo(x,y); }
  ctx.closePath();ctx.fillStyle=SETTINGS.starColor;ctx.fill();
  const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;return texture;
}
export async function createGlobe(stage,cities,lang,onSelect) {
  let disposed=false,frame=0,visible=true,lastTime=0,elapsed=0,paused=false,userEnabled=false;
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
  const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});
  renderer.setClearColor(0x000000,0);renderer.outputColorSpace=THREE.SRGBColorSpace;
  const canvas=renderer.domElement;canvas.setAttribute('aria-hidden','true');stage.append(canvas);
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(38,1,0.1,30);camera.position.set(0,0,3.8);
  const world=new THREE.Group();scene.add(world);
  const geometry=new THREE.SphereGeometry(1,64,48);
  const material=new THREE.MeshPhongMaterial({color:0xffffff,shininess:9,specular:0x10243a});
  const earth=new THREE.Mesh(geometry,material);world.add(earth);
  scene.add(new THREE.AmbientLight(0xb7d5ed,1.1));
  const sun=new THREE.DirectionalLight(0xffffff,2);sun.position.set(-3,4,5);scene.add(sun);
  const rim=new THREE.DirectionalLight(0x399cff,0.65);rim.position.set(3,-1,-2);scene.add(rim);
  const atmosphereMaterials=[1.035,1.075].map((radius,i)=> {
    const mat=new THREE.MeshBasicMaterial({color:SETTINGS.atmosphereColor,transparent:true,opacity:i?0.05:0.16,side:THREE.BackSide,depthWrite:false});
    const mesh=new THREE.Mesh(new THREE.SphereGeometry(radius,48,32),mat);scene.add(mesh);return mesh;
  });
  const spriteTexture=starTexture();
  const markers=cities.map(city=> {
    const marker=new THREE.Sprite(new THREE.SpriteMaterial({map:spriteTexture,transparent:true,depthTest:true,depthWrite:false}));
    marker.position.copy(coordinates(city.lat,city.lon));marker.scale.setScalar(0.16);marker.userData.city=city;world.add(marker);return marker;
  });
  const state={targetY:SETTINGS.initialRotation,targetX:SETTINGS.initialTilt,hoverY:0,hoverX:0,lastInput:0,interacting:false};
  world.rotation.set(state.targetX,state.targetY,0);
  const raycaster=new THREE.Raycaster(),mouse=new THREE.Vector2();
  const canRender=()=>visible&&!document.hidden&&!disposed;
  function requestFrame() {if(canRender()&&!frame)frame=requestAnimationFrame(draw);}
  function draw(time) {
    frame=0;if(!canRender())return;
    const delta=Math.min((time-(lastTime||time))/1000,0.05);lastTime=time;elapsed+=delta;
    const auto=(!motion.matches||userEnabled)&&!paused&&!state.interacting;
    if(auto)state.targetY+=delta*(SETTINGS.rotationSpeed+(time-state.lastInput<1200?state.hoverY*0.35:0));
    const blend=motion.matches?1:1-Math.exp(-delta*7);
    const tilt=state.targetX+(motion.matches?0:state.hoverX);
    world.rotation.y+=(state.targetY-world.rotation.y)*blend;
    world.rotation.x+=(tilt-world.rotation.x)*blend;
    markers.forEach((marker,i)=>marker.scale.setScalar(motion.matches||paused?0.16:0.16+Math.sin(elapsed*1.6+i)*0.014));
    renderer.render(scene,camera);
    const settling=Math.abs(world.rotation.y-state.targetY)+Math.abs(world.rotation.x-tilt)>0.0001;
    if(auto||settling||state.interacting)requestFrame();
  }
  const releaseInteraction=bindInteraction(canvas,state,{requestFrame,select(event){
    const rect=canvas.getBoundingClientRect();mouse.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);
    raycaster.setFromCamera(mouse,camera);const hit=raycaster.intersectObjects([earth,...markers],false)[0];
    if(hit?.object.userData.city)onSelect(hit.object.userData.city);
  }});
  let lastHover=0;
  function hover(event) {
    if(event.pointerType!=='mouse'||event.buttons||performance.now()-lastHover<80)return;
    lastHover=performance.now();const rect=canvas.getBoundingClientRect();
    mouse.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);
    raycaster.setFromCamera(mouse,camera);
    const hit=raycaster.intersectObjects([earth,...markers],false)[0];
    if(hit?.object.userData.city)onSelect(hit.object.userData.city);
  }
  canvas.addEventListener('pointermove',hover);
  function resize() {
    if(disposed)return;const {width,height}=stage.getBoundingClientRect();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,width<500?SETTINGS.mobilePixelRatio:SETTINGS.maxPixelRatio));
    renderer.setSize(Math.max(width,1),Math.max(height,1));camera.aspect=width/Math.max(height,1);camera.updateProjectionMatrix();requestFrame();
  }
  const observer=new ResizeObserver(resize);observer.observe(stage);
  const lost=event=>{event.preventDefault();stage.dispatchEvent(new Event('globe-failed'));};
  canvas.addEventListener('webglcontextlost',lost);
  const changed=()=>{lastTime=0;requestFrame();};document.addEventListener('visibilitychange',changed);motion.addEventListener('change',changed);
  try {
    const texture=await new THREE.TextureLoader().loadAsync(new URL('./earth.jpg',import.meta.url).href);
    if(disposed){texture.dispose();throw new Error('disposed');}
    texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=Math.min(renderer.capabilities.getMaxAnisotropy(),4);material.map=texture;material.needsUpdate=true;
    resize();requestFrame();
  } catch(error) {dispose();throw error;}
  function dispose() {
    if(disposed)return;disposed=true;cancelAnimationFrame(frame);observer.disconnect();releaseInteraction();canvas.removeEventListener('pointermove',hover);
    document.removeEventListener('visibilitychange',changed);motion.removeEventListener('change',changed);canvas.removeEventListener('webglcontextlost',lost);
    geometry.dispose();material.map?.dispose();material.dispose();spriteTexture.dispose();markers.forEach(m=>m.material.dispose());
    atmosphereMaterials.forEach(m=>{m.geometry.dispose();m.material.dispose();});renderer.dispose();renderer.forceContextLoss();canvas.remove();
  }
  return {
    focus(city){
      const desired=-Math.PI/2-radians(city.lon);
      state.targetY=world.rotation.y+Math.atan2(Math.sin(desired-world.rotation.y),Math.cos(desired-world.rotation.y));
      state.targetX=Math.max(-1,Math.min(1,radians(city.lat)));state.lastInput=performance.now();state.hoverX=state.hoverY=0;
      requestFrame();onSelect(city);
    },
    setVisible(value){visible=value;lastTime=0;if(value)requestFrame();else{cancelAnimationFrame(frame);frame=0;}},
    setPaused(value){paused=value;userEnabled=!value;requestFrame();},dispose,
  };
}
