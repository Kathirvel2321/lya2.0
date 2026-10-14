'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),config=JSON.parse(fs.readFileSync(path.join(root,'states.json'))),effects=require('../effects.js');let frames=0;
const body=JSON.stringify(effects.frame(config,'idle','none',0).body);
for(const interaction of Object.keys(config.interaction))for(const task of Object.keys(config.tasks))for(const time of [0,1.25,10])for(const reduced of [false,true]){
 const f=effects.frame(config,interaction,task,time,.6,reduced);frames++;assert.equal(JSON.stringify(f.body),body);assert.equal(f.state.authority,false);assert.ok(f.commands.length<=16);assert.ok(f.commands.length>0);if(reduced)assert.equal(f.animate,false);
 for(const c of f.commands){assert.match(c.color,/^#[0-9a-f]{6}$/i);assert.ok(c.alpha>=0&&c.alpha<=1);if(c.points){assert.ok(c.points.length<=102);for(const p of c.points)assert.ok(p.every(Number.isFinite))}else assert.ok([c.x,c.y,c.r].every(Number.isFinite))}
 if(['approval','high_risk','blocked','error'].includes(task))assert.equal(f.animate,false);
}
assert.throws(()=>effects.frame(config,'fake','none',0));assert.throws(()=>effects.frame(config,'idle','fake',0));assert.throws(()=>effects.frame(config,'idle','none',NaN));
assert.equal(effects.resolve(config,'speaking','coding').color,'#79b8ff');assert.equal(effects.resolve(config,'speaking','coding').effect,'waves');
assert.equal(effects.resolve(config,'paused','coding').color,'#9aaeba');assert.equal(effects.resolve(config,'thinking','blocked').color,'#ffc26b');
assert.equal(effects.resolve(config,'speaking','approval').effect,'approval');
assert.deepEqual(effects.frame(config,'thinking','none',0,.5,true).commands,effects.frame(config,'thinking','none',10,.5,true).commands);
assert.notDeepEqual(effects.frame(config,'listening','none',0).commands,effects.frame(config,'listening','none',2).commands);
const result={success:true,frames_checked:frames,fixed_body:true,authority_granted:false,real_browser:false};fs.writeFileSync(path.join(root,'tests/effects-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
