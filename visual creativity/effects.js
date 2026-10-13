/* Pure visual frames: no authentication, actions, sensor access or network. */
(function(root){
'use strict';
const TAU=Math.PI*2;
const STABLE=new Set(['idle','standby','paused','voice_off','offline','cancelled','uncertain']);
const ATTENTION=new Set(['approval','high_risk','blocked','error']);
const ACTIVE_TASKS=new Set(['coding','helping','building','learning','research','files','success']);
function resolve(config,interaction,task){
 if(!Object.hasOwn(config.interaction,interaction)||!Object.hasOwn(config.tasks,task))throw new Error('Unknown visual state');
 const phase=config.interaction[interaction],work=config.tasks[task];
 // One main effect. Attention states override, pause/offline suppress task motion.
 const attention=ATTENTION.has(task);
 const suppress=['paused','voice_off','offline','cancelled','uncertain'].includes(interaction);
 const voice=['listening','hearing','thinking','speaking'].includes(interaction);
 const useTask=task!=='none'&&(attention||(!suppress&&!voice));
 return {interaction,task,phase,work,color:(useTask||(!suppress&&task!=='none'))?work.color:phase.color,effect:useTask?work.effect:phase.effect,
  moving:attention?false:suppress?false:useTask?ACTIVE_TASKS.has(task):phase.motion,
  label:attention?work.label:phase.label+(task!=='none'?' · '+work.label:''),authority:false};
}
function frame(config,interaction,task,time,energy=0.35,reduced=false){
 if(!Number.isFinite(time)||!Number.isFinite(energy))throw new Error('Invalid frame input');
 const state=resolve(config,interaction,task),t=reduced||!state.moving?0:Math.max(0,time),e=Math.max(0,Math.min(1,energy)),commands=[];
 function path(points,alpha=.6,width=1.2,glow=4,layer='back',dash=[]){commands.push({kind:'path',points,alpha,width,glow,layer,dash,color:state.color});}
 function point(x,y,r=.006,alpha=.9,layer='front'){commands.push({kind:'dot',x,y,r,alpha,layer,color:state.color});}
 function orbit(rx,ry,angle,start,end,alpha=.6,width=1.2,glow=4,dash=[]){
  let current=[],layer=null;
  for(let i=0;i<=80;i++){const a=start+(end-start)*i/80,c=Math.cos(angle),s=Math.sin(angle),x=rx*Math.cos(a),y=ry*Math.sin(a),next=Math.sin(a)>=0?'front':'back';
   const p=[x*c-y*s,x*s+y*c];if(layer&&next!==layer){path(current,alpha,width,glow,layer,dash);current=[current.at(-1)];}layer=next;current.push(p);}
  if(current.length>1)path(current,alpha,width,glow,layer,dash);
 }
 const lead=t*.8;
 switch(state.effect){
 case 'aura':orbit(.30,.35,-.25,0,TAU,.1,.8,8);break;
 case 'quiet':orbit(.35,.26,0,-1.0,-.35,.18,.8,0);break;
 case 'orbit':orbit(.43,.15,-.28,0,TAU,.32,1,3);orbit(.45,.16,-.28,lead,lead+1.05,.95,1.6,6);orbit(.47,.17,-.28,lead-.3,lead+.7,.15,.7,2);break;
 case 'ticks':orbit(.43,.17,.16,0,TAU,.4,1,3);for(let i=0;i<3;i++){const a=lead+i*.45;point(.43*Math.cos(a),.17*Math.sin(a),.0045,.9,Math.sin(a)>0?'front':'back');}break;
 case 'weave':for(let strand=0;strand<2;strand++){const p=[];for(let i=0;i<=100;i++){const a=i*TAU/100; p.push([.43*Math.sin(a),.18*Math.sin(2*a+strand*.45)]);}path(p,.34,1,3,strand?'front':'back');}point(.43*Math.sin(lead),.18*Math.sin(2*lead),.005,.95);break;
 case 'waves':for(const side of [-1,1])for(let k=0;k<3;k++){const p=[];for(let i=0;i<=50;i++){const u=i/50; p.push([side*(.25+.24*u),Math.sin(u*TAU*1.3-t*2.4+k*.4)*(.016+.045*e)*Math.sin(Math.PI*u)+(k-1)*.037]);}path(p,k===1?.85:.22,k===1?1.5:.8,4,'front');}break;
 case 'crescents':for(const side of [-1,1]){orbit(.36,.28,side*.18,side<0?1.8:-1.3,side<0?4.4:1.3,.65,1.25,4);orbit(.39,.30,side*.18,side<0?2.0:-1.1,side<0?4.2:1.1,.16,.7,2);} {const a=2.8+Math.sin(lead)*.65;point(.36*Math.cos(a),.28*Math.sin(a),.004,.65,'back');}break;
 case 'brackets':for(const side of [-1,1])orbit(.34,.25,0,side<0?2.3:-.85,side<0?4.0:.85,.42,1,0);break;
 case 'dashed':orbit(.35,.29,0,.2,TAU-.8,.25,.8,0,[5,10]);break;
 case 'broken':for(const start of [0.1,Math.PI+.1])orbit(.36,.28,.12,start,start+1.7,.58,1,2);break;
 case 'code':path([[-.43,-.22],[-.54,-.1],[.40,.10],[.48,.20],[.33,.25]],.45,1,3,'back');path([[-.43,-.22],[-.54,-.1],[-.24,-.04]],.85,1.4,4,'front');for(let i=0;i<3;i++){const x=.27+i*.028,y=.16;path([[x,y],[x+.017,y],[x+.017,y+.016],[x,y+.016],[x,y]],.7,.8,1,'front');} {const u=(t*.16)%1;point(-.54+u*.94,-.1+u*.2,.004,.7,'back');}break;
 case 'progress':for(let i=0;i<7;i++)orbit(.37,.29,-.25,i*TAU/7+.05,i*TAU/7+.56,i===Math.floor(t)%7?.9:.24,1.25,3);break;
 case 'rise':for(const side of [-1,1])for(let k=0;k<2;k++){const p=[];for(let i=0;i<=50;i++){const u=i/50;p.push([side*(.26+.12*Math.sin(u*Math.PI)),.32-u*.58]);}path(p,k?.16:.65,k?.7:1.25,3,'back');} {const u=(t*.20)%1;for(const side of [-1,1])point(side*(.26+.12*Math.sin(u*Math.PI)),.32-u*.58,.004,Math.sin(u*Math.PI)*.7,'back');}break;
 case 'frames':for(let k=0;k<2;k++){const x=.35+k*.045,y=.22+k*.025;path([[-x,-y],[-x,-y+.22]],k?.22:.65,1,2,'back');path([[-x,-y],[-x+.18,-y]],k?.22:.65,1,2,'back');path([[x,y],[x,y-.22],[x-.18,y]],k?.22:.65,1,2,'back');}point(.35,.22-((t*.18)%1)*.22,.004,.65,'back');break;
 case 'boundary':for(const radius of [.34,.38]){orbit(radius,.27,-.15,.25,2.6,.42,1,2);orbit(radius,.27,-.15,3.5,5.7,.42,1,2);}break;
 case 'approval':orbit(.41,.17,-.2,.35,TAU-.85,.7,1.25,3);point(.41*Math.cos(.35),.17*Math.sin(.35),.006,.85);break;
 case 'caution':for(let i=0;i<3;i++)orbit(.38,.28,-.12,i*TAU/3+.16,i*TAU/3+1.5,.76,1.5,3);break;
 case 'complete':orbit(.40,.16,-.23,0,TAU,.65,1.25,3);orbit(.42,.17,-.23,lead,lead+.8,.88,1.5,4);break;
 default:throw new Error('Unknown effect');
 }
 return {state,commands,body:{asset:config.body.asset,pose:config.body.pose,scale:1,rotation:0,tint:null},animate:!reduced&&state.moving};
}
const api={resolve,frame};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.LyaEffects=api;
})(typeof globalThis!=='undefined'?globalThis:this);
