// Front artwork looks left; back artwork looks right. Derive the mirror from travel,
// rather than borrowing the original character's atlas convention.
export function lordDirection(from,to,fallback={back:false,flip:false}){
 const dx=to.x-from.x,dz=to.z-from.z;if(Math.hypot(dx,dz)<1e-6)return{...fallback,dx,dz};
 const back=Math.abs(dz)>1e-6?dz>0:fallback.back,flip=Math.abs(dx)>1e-6?(back?dx<0:dx>0):fallback.flip;
 return{back,flip,dx,dz,heading:(back?'back-':'front-')+(dx<0?'left':'right')};
}
export function npcPose(n,time){
 const local=((time+(n.phase||0))%18+18)%18;let progress=0,walking=false,sign=1;
 if(local>=4&&local<7){progress=(local-4)/3;walking=true;}
 else if(local>=7&&local<12)progress=1;
 else if(local>=12&&local<15){progress=1-(local-12)/3;walking=true;sign=-1;}
 const dx=(n.pace||.22)*(n.paceSign||1),flip=walking?dx*sign>0:(local>=7&&local<12?dx>0:!!n.flip);
 return{x:n.x+dx*progress,z:n.z,walking,flip,frame:(walking?4:0)+Math.floor((time+(n.phase||0))*(walking?6:2.4))%4,progress,mode:walking?'walk':'gesture'};
}
