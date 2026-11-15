// Explicit, locally configured lighting allowlist. No arbitrary entity/service input.
export function validateRooms(raw){
 if(!Array.isArray(raw)||raw.length>12)throw Error('Invalid lighting configuration');
 const ids=new Set(),entities=new Set(),rooms=new Set();
 const idOK=s=>typeof s==='string'&&/^[a-z0-9-]{1,50}$/.test(s);
 const labelOK=s=>typeof s==='string'&&s.length>0&&s.length<=64;
 return raw.map(r=>{
  if(!r||!idOK(r.id)||rooms.has(r.id)||!labelOK(r.label)||!Array.isArray(r.lights)||r.lights.length>20)throw Error('Invalid room');
  rooms.add(r.id);
  return {id:r.id,label:r.label,lights:r.lights.map(l=>{
   if(!l||!idOK(l.id)||ids.has(l.id)||!labelOK(l.label)||typeof l.entity!=='string'||!/^light\.[a-z0-9_]+$/.test(l.entity)||entities.has(l.entity))throw Error('Invalid light');
   ids.add(l.id);entities.add(l.entity);return {id:l.id,label:l.label,entity:l.entity};
  })};
 });
}
export function projectRooms(rooms,states){
 return rooms.map(r=>({id:r.id,label:r.label,lights:r.lights.map(l=>{
  let state=states?.[l.entity]?.state;
  if(state!=='on'&&state!=='off')state='unavailable';
  return {id:l.id,label:l.label,state};
 })}));
}
export function targetFor(rooms,id,state){
 if(typeof id!=='string'||!['on','off'].includes(state))return null;
 for(const r of rooms)for(const l of r.lights)if(l.id===id)return {entity:l.entity,service:state==='on'?'turn_on':'turn_off'};
 return null;
}
