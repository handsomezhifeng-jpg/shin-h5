const clamp=v=>Math.max(0,Math.min(1,v));
const smooth=v=>{v=clamp(v);return v*v*(3-2*v);};
const mix=(a,b,t)=>a+(b-a)*t;
export const MARKET_VISITS=[
 {id:'produce-customer',vendor:'produce-seller',path:[[-70,820],[-12,744],[46,665],[88,615],[123,582]],arrive:7,buy:9,leave:7,gap:7,offset:9,variant:0,faceRight:false},
 {id:'tea-blue-customer',vendor:'tea-seller',path:[[1090,645],[1000,620],[930,585],[835,548],[785,519]],arrive:8,buy:10,leave:8,gap:8,offset:13,variant:1,faceRight:true},
 {id:'tea-red-customer',vendor:'tea-seller',path:[[1100,720],[1010,675],[950,630],[900,590],[854,556]],arrive:7,buy:8,leave:7,gap:11,offset:3,variant:2,faceRight:false},
 {id:'cloth-customer',vendor:'cloth-seller',path:[[-70,1440],[25,1393],[135,1342],[252,1302],[329,1268]],arrive:8,buy:11,leave:8,gap:9,offset:11,variant:2,faceRight:false}
];
export const MARKET_VENDORS=[
 {id:'produce-seller',row:0,position:[75,526],counter:[[-20,548],[151,474],[157,538],[-20,622]]},
 {id:'tea-seller',row:1,position:[854,450],counter:[[760,424],[788,420],[820,420],[840,429],[855,443],[880,440],[903,454],[940,452],[966,449],[987,465],[990,560],[760,480]]},
 {id:'cloth-seller',row:2,position:[230,1196],counter:[[178,1206],[279,1159],[305,1167],[342,1176],[343,1220],[176,1305]]},
 {id:'grain-seller',row:3,position:[861,1075],counter:[[790,1045],[825,1020],[850,1038],[850,1056],[868,1063],[880,1059],[902,1054],[921,1075],[942,1077],[968,1096],[970,1160],[778,1110]]}
];
export function sampleResidentPath(points,fraction){
 const lengths=points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1])),total=lengths.reduce((a,b)=>a+b,0);let distance=clamp(fraction)*total;
 for(let i=0;i<lengths.length;i++){if(distance<=lengths[i]||i===lengths.length-1){const t=lengths[i]?clamp(distance/lengths[i]):1,a=points[i],b=points[i+1];return{x:mix(a[0],b[0],t),y:mix(a[1],b[1],t),dx:b[0]-a[0],dy:b[1]-a[1],distance:clamp(fraction)*total};}distance-=lengths[i];}
 return{x:points[0][0],y:points[0][1],dx:0,dy:0,distance:0};
}
export function sampleMarketVisit(definition,time){
 const d=definition,total=d.arrive+d.buy+d.leave+d.gap,absolute=Math.max(0,time)+d.offset,cycle=Math.floor(absolute/total),t=absolute%total,variant=(cycle+d.variant)%3;
 let state,local,duration,fraction;
 if(t<d.arrive){state='arriving';local=t;duration=d.arrive;fraction=t/duration;}
 else if(t<d.arrive+d.buy){state='buying';local=t-d.arrive;duration=d.buy;fraction=1;}
 else if(t<d.arrive+d.buy+d.leave){state='leaving';local=t-d.arrive-d.buy;duration=d.leave;fraction=1-local/duration;}
 else return{id:d.id,vendor:d.vendor,state:'away',visible:false,cycle,variant,local:t-d.arrive-d.buy-d.leave,duration:d.gap};
 const p=sampleResidentPath(d.path,fraction),walking=state!=='buying',faceRight=walking?(state==='leaving'?-p.dx:p.dx)>0:d.faceRight,frame=state==='buying'?(Math.floor(local*1.5)%4===1?3:0):(state==='leaving'?4:1)+(Math.floor(p.distance/18)%2);
 return{id:d.id,vendor:d.vendor,state,visible:true,cycle,variant,local,duration,x:p.x,y:p.y,frame,faceRight,walking,alpha:smooth(Math.min(fraction*14,1)),scale:1};
}
const HOME_ROUTE=[[329,320],[302,304],[274,282],[247,258],[236,229]],SWEEP_POINTS=[[329,320],[359,337],[305,332],[329,320]];
export function sampleSweeperAnimation(pose,atlases){
 const atlas=pose.walking?'sweeperWalk':'sweeperSweep',clip=atlases[atlas],seconds=Math.max(0,(pose.local??0)-(pose.state==='change-patch'?4.2:0));
 return{atlas,frame:Math.floor(seconds*clip.fps)%clip.frames.length,flip:pose.walking&&clip.faceRight!==pose.faceRight};
}
export function sampleSweeper(time){
 const cycle=Math.floor(Math.max(0,time)/42),t=Math.max(0,time)%42;
 if(t<18){const segment=Math.min(2,Math.floor(t/6)),local=t%6,moving=local>=4.2,p=sampleResidentPath([SWEEP_POINTS[segment],SWEEP_POINTS[segment+1]],moving?smooth((local-4.2)/1.8):0);return{id:'sweeper',state:moving?'change-patch':'sweeping',visible:true,cycle,x:p.x,y:p.y,scale:1,alpha:1,walking:moving,frame:moving?6+Math.floor(t*5)%2:Math.floor(t*4)%4,faceRight:p.dx>0,doorOpen:0,local};}
 if(t<23){const local=t-18,u=local/5,p=sampleResidentPath(HOME_ROUTE,u);return{id:'sweeper',state:'going-home',visible:u<.99,cycle,x:p.x,y:p.y,walking:true,frame:4+Math.floor(p.distance/15)%2,faceRight:p.dx>0,scale:mix(1,.67,smooth((u-.58)/.32)),alpha:1-smooth((u-.87)/.12),doorOpen:smooth((local-2)/.45),atDoor:u>.75,local};}
 if(t<37){const local=t-23;return{id:'sweeper',state:'indoors',visible:false,cycle,local,doorOpen:Math.max(1-smooth(local/.6),smooth((local-13.4)/.6))};}
 const local=t-37,u=local/5,p=sampleResidentPath(HOME_ROUTE,1-u);return{id:'sweeper',state:'coming-out',visible:u>.015,cycle,x:p.x,y:p.y,walking:true,frame:6+Math.floor(p.distance/15)%2,faceRight:-p.dx>0,scale:mix(.67,1,smooth((u-.1)/.32)),alpha:smooth(u/.12),doorOpen:1-smooth((local-2.4)/.6),atDoor:u<.25,local};
}
export function sampleMarketResidents(time){
 const visitors=MARKET_VISITS.map(d=>sampleMarketVisit(d,time));
 const vendors=MARKET_VENDORS.map((v,i)=>{const serving=visitors.some(p=>p.vendor===v.id&&p.state==='buying'),phase=(time+i*1.7)%6;return{...v,state:serving?'serving':'arranging',frame:serving?(Math.floor(phase*1.2)%3===0?0:2):(phase<3?1:0),visible:true};});
 return{time,sweeper:sampleSweeper(time),visitors,vendors};
}
