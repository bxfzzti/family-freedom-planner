import test from 'node:test';import assert from 'node:assert/strict';import {loan,calculate} from '../calculator.mjs';
const p={price:300,cash:150,down:100,fees:6,renovation:20,fund:80,bankRate:3.1,fundRate:2.6,years:30,income:2.5,expenses:1,reserve:20,drop:50,method:'annuity'};
test('zero interest pays exactly principal',()=>{const r=loan(120000,0,1);assert.equal(r.payments[0].payment,10000);assert.equal(r.interest,0);});
test('known annuity and principal conservation',()=>{const r=loan(1000000,3,30);assert.ok(Math.abs(r.payments[0].payment-4216.04)<.01);assert.ok(Math.abs(r.payments.reduce((a,x)=>a+x.principal,0)-1000000)<.001);assert.equal(r.payments.at(-1).balance,0);});
test('equal principal decreases and pays full principal',()=>{const r=loan(120000,12,1,'principal');assert.equal(r.payments[0].payment,11200);assert.equal(r.payments.at(-1).payment,10100);assert.equal(r.interest,7800);});
test('combined loans and initial cash close',()=>{const r=calculate(p);assert.equal(r.remaining,240000);assert.equal(r.total,2000000);assert.equal(r.bank,1200000);assert.ok(Math.abs(r.first-loan(1200000,3.1,30).payments[0].payment-loan(800000,2.6,30).payments[0].payment)<.001);});
test('zero income path, reserve and cash gaps remain visible',()=>{const r=calculate(p);assert.ok(r.paths[2].ending<0);assert.ok(r.paths[2].breach>0);const short=calculate({...p,cash:90});assert.equal(short.remaining,-360000);assert.equal(short.paths[0].breach,0);});
test('mortgage ends during 36 month horizon',()=>{const r=calculate({...p,years:1});assert.equal(r.payments.length,12);assert.equal(Math.round(r.paths[0].values[13]-r.paths[0].values[12]),15000);});
test('reject blank, negative, nonfinite, invalid funding and fractional months',()=>{for(const bad of [{price:''},{cash:-1},{income:Infinity},{down:301},{fund:201},{drop:101},{years:0},{years:1.01}])assert.throws(()=>calculate({...p,...bad}));});
test('all cash purchase has no interest or mortgage',()=>{const r=calculate({...p,down:300,cash:400,fund:0});assert.equal(r.first,0);assert.equal(r.interest,0);assert.equal(r.remaining,740000);});

