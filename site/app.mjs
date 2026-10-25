import {calculate} from './calculator.mjs';
const $=id=>document.getElementById(id),form=$('form');
const amount=n=>(n/10000).toLocaleString('zh-CN',{maximumFractionDigits:2})+' 万';
const yuan=n=>n.toLocaleString('zh-CN',{maximumFractionDigits:0});
let current,values;
function read(){const p={};for(const e of form.elements)if(e.id)p[e.id]=e.value;
 const total=Number(p.price)-Number(p.down);
 if(p.type==='bank'){p.fund=0;p.fundRate=0;}if(p.type==='fund'){p.fund=total;p.bankRate=0;}
 return p;
}
function update(){
 $('fund-label').hidden=$('type').value!=='mixed';
 $('bank-rate-label').hidden=$('type').value==='fund';
 $('fund-rate-label').hidden=$('type').value==='bank';
 try{
  const p=read(),r=calculate(p);current=r;values=p;
  $('error').hidden=true;$('output').hidden=false;
  $('payment-title').textContent=p.method==='principal'?'首月还款 · 此后逐月递减':'每月还款 · 等额本息';
  $('monthly').textContent=yuan(r.first);
  $('loan-detail').textContent='商业贷款 '+amount(r.bank)+' · 公积金 '+amount(Number(p.fund)*10000)+(p.method==='principal'?' · 末月 '+yuan(r.last)+' 元':'');
  $('remaining').textContent=amount(r.remaining);$('surplus').textContent=amount(r.monthlyNet);$('total').textContent=amount(r.total);$('interest').textContent=amount(r.interest);
  const gap=r.remaining-Number(p.reserve)*10000;
  $('cash-note').className='notice'+(gap<0?' warning':'');
  $('cash-note').textContent=r.remaining<0?'当前现金不足：支付首付和费用还差 '+amount(-r.remaining)+'。此方案尚未资金闭合，以下曲线仅展示缺口演变。':gap<0?'买后现金比你设定的底线少 '+amount(-gap)+'，可比较更低首付或更低总价。':'买后现金高于你设定的底线 '+amount(gap)+'。现金底线尚未从余额中扣除。';
  $('drop-label').textContent='收入下降 '+p.drop+'%';
  const labels=['正常收入','收入下降 '+p.drop+'%','零收入'];
  $('scenario-notes').replaceChildren(...r.paths.map((s,i)=>{const el=document.createElement('p');el.textContent=labels[i]+'：3年后 '+amount(s.ending)+'；'+(s.breach===null?'36个月内未低于所设底线':s.breach===0?'买后立即低于所设底线':'第 '+s.breach+' 个月低于所设底线');return el;}));
  chart(r,Number(p.reserve)*10000);
  $('compare').replaceChildren(...[-10,0,10].map(delta=>{
   const down=Number(p.down)+delta,card=document.createElement('article');card.className='compare-card'+(delta===0?' current':'');
   const title=document.createElement('p');title.className='eyebrow';title.textContent=delta===0?'当前方案':delta<0?'少付 10 万首付':'多付 10 万首付';
   const h=document.createElement('h3');h.textContent='首付 '+down+' 万';card.append(title,h);
   try{const total=Number(p.price)-down;const fund=p.type==='bank'?0:p.type==='fund'?total:Math.min(Number(p.fund),Math.max(0,total));const result=calculate({...p,down,fund});
    for(const [label,value]of [['首月还款',yuan(result.first)+' 元'],['买后现金',amount(result.remaining)],['全期利息',amount(result.interest)]]){const line=document.createElement('p'),b=document.createElement('b');line.textContent=label;b.textContent=value;line.append(b);card.append(line);}
    if(result.remaining<0){const warning=document.createElement('p');warning.textContent='现金不足，方案有资金缺口';card.append(warning);}
   }catch{const e=document.createElement('p');e.textContent='该首付超出房价或有效范围';card.append(e);}
   return card;
  }));
 }catch(e){current=null;$('output').hidden=true;$('error').hidden=false;$('error').textContent=e.message;$('compare').replaceChildren();}
}
function chart(r,reserve){
 const svg=$('chart'),ns='http://www.w3.org/2000/svg';svg.replaceChildren();
 const all=r.paths.flatMap(s=>s.values).concat([reserve,0]),lo=Math.min(...all),hi=Math.max(...all),span=hi-lo||1;
 const x=i=>48+i/36*515,y=v=>170-(v-lo)/span*145;
 function el(tag,attrs,text){const node=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))node.setAttribute(k,v);if(text!==undefined)node.textContent=text;svg.append(node);return node;}
 for(let j=0;j<4;j++){const v=lo+j*span/3;el('line',{x1:48,x2:563,y1:y(v),y2:y(v),stroke:'#e8e8ee'});el('text',{x:40,y:y(v)+4,'text-anchor':'end',fill:'#86868b','font-size':11},(v/10000).toFixed(0));}
 el('line',{x1:48,x2:563,y1:y(reserve),y2:y(reserve),stroke:'#777','stroke-dasharray':'4 4'});
 el('text',{x:50,y:12,fill:'#777','font-size':10},'虚线：你设定的现金底线');
 r.paths.forEach((s,i)=>el('polyline',{points:s.values.map((v,j)=>x(j)+','+y(v)).join(' '),fill:'none',stroke:['#0071e3','#bd7d25','#9b739b'][i],'stroke-width':2.5}));
 for(const n of [0,12,24,36])el('text',{x:x(n),y:198,'text-anchor':'middle',fill:'#86868b','font-size':11},n===0?'买后':n+'个月');
}
form.addEventListener('input',update);form.addEventListener('change',update);
form.addEventListener('submit',e=>e.preventDefault());
$('reset').addEventListener('click',()=>{form.reset();update();});
$('export').addEventListener('click',()=>{
 if(!current)return;
 const labels={price:'房屋总价（万元）',down:'首付（万元）',cash:'已到账现金（万元）',fees:'全部交易税费（万元）',renovation:'装修家具家电（万元）',fund:'公积金贷款（万元）',bankRate:'商贷年利率（%）',fundRate:'公积金年利率（%）',years:'贷款年限',income:'税后月收入（万元）',expenses:'买后其他月支出（万元）',reserve:'现金底线（万元）',drop:'收入降幅（%）'};
 const text=['买房小账本 · 条件测算',new Date().toLocaleString('zh-CN'),...Object.entries(labels).map(([k,v])=>v+'：'+values[k]),'还款方式：'+(values.method==='annuity'?'等额本息':'等额本金'),'首月月供：'+yuan(current.first)+'元','全期利息：'+amount(current.interest),'买后现金：'+amount(current.remaining),...current.paths.map(s=>'收入下降'+s.drop+'%：36个月后现金'+amount(s.ending)+'；低于底线月份：'+(s.breach??'期间未触及')),'按给定固定利率、固定其他收支、零投资收益测算。不含额外大额支出，银行实际按日计息及舍入可能不同。未核实审批额度和当地政策。网页测算不代表完整家庭规划或买卖建议。'].join('\n');
 const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='买房小账本-测算.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
$('copy').addEventListener('click',async()=>{
 const text='请安装或加载买房小账本配套的 family-freedom-planner Skill。仓库：https://github.com/bxfzzti/family-freedom-planner ，路径：skills/family-freedom-planner。请完整读取 SKILL.md，说明是否持久安装、是否能执行脚本；复用我提供的已知信息，每轮最多问三个关键项，帮我分析首付、买后现金和收入变化。';
 try{await navigator.clipboard.writeText(text);$('copy-status').textContent='已复制。粘贴给支持读取仓库和执行脚本的 Agent。';}catch{$('copy-status').textContent=text;}
});update();

