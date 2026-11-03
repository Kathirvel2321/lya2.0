'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const file=path.resolve(__dirname,'../../cloud/mobile.html'),html=fs.readFileSync(file,'utf8');
const source=html.match(/<script[^>]*>([\s\S]*?)<\/script>/)[1];
new vm.Script(source,{filename:'mobile.html'});
const start=source.indexOf('async function submitQuestion('),end=source.indexOf('\nfunction wav(',start);
assert.ok(start>=0&&end>start);
const functionSource=source.slice(start,end),elements=new Map(),sent=[];
let serial=0,mode='ok';
const element=id=>{if(!elements.has(id))elements.set(id,{textContent:'',scrollHeight:100,scrollTop:0,clientHeight:100});return elements.get(id)};
const ctx=vm.createContext({request:null,authenticating:false,conversation:false,sharedRetry:null,generation:0,
  requestId:null,lastAudio:null,playerSource:null,AbortController,crypto:{randomUUID:()=>String(++serial).padStart(32,'0')},
  $:element,ownerPhrase:()=>false,stopPhrase:()=>false,ownerRequest:()=>{},controls:()=>{},queueListen:()=>{},
  archiveExchange:()=>{},state:()=>{},playReply:async()=>{},
  pause:message=>{ctx.paused=message},locked:()=>{ctx.sharedRetry=null},
  cancelTurn:()=>{ctx.generation++;ctx.request=null;ctx.requestId=null},
  api:async(route,packet)=>{sent.push({...packet});if(mode==='uncertain')throw Object.assign(Error('Unconfirmed'),{status:503});
    if(mode==='bad')throw Object.assign(Error('Rejected'),{status:400});
    if(mode==='cancel'){ctx.generation++;ctx.request=null;throw Object.assign(Error('Cancelled'),{name:'AbortError'})}
    return {text:'Synthetic reply.'}}
});
vm.runInContext(functionSource,ctx);
async function main(){
  const text='shared memory demo: correct colour = green';
  mode='uncertain';await ctx.submitQuestion(text,false);const original=sent.at(-1).id;
  assert.equal(ctx.sharedRetry.id,original);
  const before=sent.length;await ctx.submitQuestion('shared memory demo: forget colour',false);
  assert.equal(sent.length,before);assert.match(ctx.paused,/unconfirmed/);
  mode='ok';await ctx.submitQuestion('shared memory demo: recall colour',false);
  assert.equal(ctx.sharedRetry.id,original);
  await ctx.submitQuestion(text,false);assert.equal(sent.at(-1).id,original);assert.equal(ctx.sharedRetry,null);
  mode='bad';await ctx.submitQuestion('shared memory demo: invalid = command',false);assert.equal(ctx.sharedRetry,null);
  mode='ok';await ctx.submitQuestion('Hello',false);const first=sent.at(-1).id;await ctx.submitQuestion('Hello again',false);
  assert.notEqual(sent.at(-1).id,first);assert.equal(ctx.sharedRetry,null);
  mode='cancel';await ctx.submitQuestion(text,false);assert.ok(ctx.sharedRetry);const cancelled=ctx.sharedRetry.id;
  mode='ok';await ctx.submitQuestion(text,false);assert.equal(sent.at(-1).id,cancelled);assert.equal(ctx.sharedRetry,null);
  const result={passed:true,checks:6,whole_script_syntax:true,shared_request_retry_and_admission:true,
    synthetic_function_harness:true,real_browser_or_phone:false,live_network:false,
    source_sha256:crypto.createHash('sha256').update(Buffer.from(html)).digest('hex')};
  if(!process.argv[2])throw Error('A new evidence path is required.');
  fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
}
main().catch(error=>{console.error(error);process.exitCode=1});
