export function number(value, label, max=1e10) {
 if (value === '' || value === null || typeof value === 'boolean') throw Error('请填写'+label);
 const n=Number(value); if(!Number.isFinite(n)||n<0||n>max) throw Error(label+'超出有效范围'); return n;
}
export function loan(principal, rate, years, method='annuity') {
 principal=number(principal,'贷款');rate=number(rate,'利率',100)/100/12;
 const months=number(years,'年限',50)*12;
 if(!Number.isInteger(months)||months<1) throw Error('贷款期限须为1至600个整月');
 if(!['annuity','principal'].includes(method)) throw Error('还款方式无效');
 const payment=rate===0?principal/months:principal*rate/(-Math.expm1(-months*Math.log1p(rate)));
 let balance=principal, interest=0;
 const payments=Array.from({length:months},(_,i)=>{
  const fee=balance*rate;
  const capital=i===months-1?balance:Math.min(balance,method==='principal'?principal/months:payment-fee);
  balance=Math.max(0,balance-capital);interest+=fee;return {payment:capital+fee,interest:fee,principal:capital,balance};
 });
 return {payments,interest};
}
export function calculate(input) {
 const names={price:'房屋总价',cash:'已到账现金',down:'首付',fees:'交易税费',renovation:'装修家具家电',fund:'公积金贷款',bankRate:'商贷利率',fundRate:'公积金利率',years:'贷款年限',income:'税后月收入',expenses:'其他月支出',reserve:'现金底线',drop:'收入降幅'};
 const p={}; for(const k of Object.keys(names)) p[k]=number(input[k],names[k]);
 if(p.price<=0) throw Error('房屋总价须大于0');
 if(p.down>p.price) throw Error('首付不能超过房屋总价');
 if(p.drop>100) throw Error('收入降幅须在0%至100%之间');
 const total=p.price-p.down;
 if(p.fund>total) throw Error('公积金贷款不能超过贷款总额；请调整贷款金额或首付');
 const fund=loan(p.fund*10000,p.fundRate,p.years,input.method);
 const bank=loan((total-p.fund)*10000,p.bankRate,p.years,input.method);
 const payments=bank.payments.map((x,i)=>x.payment+fund.payments[i].payment);
 const remaining=(p.cash-p.down-p.fees-p.renovation)*10000;
 const horizon=36, paths=[0,p.drop,100].map(drop=>{
  let cash=remaining;const values=[cash];let breach=cash<p.reserve*10000?0:null;
  for(let i=0;i<horizon;i++){cash+=(p.income*(1-drop/100)-p.expenses)*10000-(payments[i]??0);values.push(cash);if(breach===null&&cash<p.reserve*10000)breach=i+1;}
  return {drop,values,breach,ending:cash};
 });
 return {remaining,total:total*10000,bank:(total-p.fund)*10000,first:payments[0],last:payments.at(-1),interest:fund.interest+bank.interest,monthlyNet:(p.income-p.expenses)*10000-payments[0],paths,payments};
}

