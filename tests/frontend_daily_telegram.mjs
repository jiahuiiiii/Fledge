// Actual delivery history component; authored data and zero HTTP requests.
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const frontend=path.join(root,'frontend');
const require=createRequire(path.join(frontend,'package.json'));
const {build}=await import(pathToFileURL(require.resolve('vite')));
const {default:react}=await import(pathToFileURL(require.resolve('@vitejs/plugin-react')));
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE));
const out=await mkdtemp(path.join(tmpdir(),'fledge-daily-telegram-'));
const entry=path.join(out,'fixture.jsx');
await writeFile(entry,`
import React from 'react';
import {createRoot} from 'react-dom/client';
import Settings from ${JSON.stringify(path.join(frontend,'src/components/TelegramSettings.jsx'))};
import {api} from ${JSON.stringify(path.join(frontend,'src/api/client.js'))};
import ${JSON.stringify(path.join(frontend,'src/styles/tokens.css'))};
import ${JSON.stringify(path.join(frontend,'src/styles/app.css'))};
import ${JSON.stringify(path.join(frontend,'src/styles/mobile.css'))};
let types=true;window.actions=[];
api.telegram=async()=>({configured:true,linked:true,enabled:true,active:true,token_changed:false,
 chat_label:'Authored private chat',bot_username:'AuthoredTestBot',watches:5,daily_recaps_enabled:types,cost_notices_enabled:types,
 deliveries:[{id:'a',kind:'digest',status:'sent',created_at:'2026-10-17T06:00:00Z'},
 {id:'b',kind:'cost',status:'uncertain',created_at:'2026-10-17T06:01:00Z',error:'Authored <script> unconfirmed send.'},
 {id:'c',kind:'move',symbol:'EXMP',status:'skipped',created_at:'2026-10-17T06:02:00Z',error:'Preview stays in Fledge.'}]});
api.telegramDelivery=async()=>{window.actions.push('changed-delivery');throw new Error('Must not mutate');};
api.telegramTest=async()=>{window.actions.push('sent-test');throw new Error('Must not send');};
const root=createRoot(document.getElementById('root'));let serial=0;
window.show=(options={})=>{types=options.types!==false;root.render(<Settings key={++serial}/>);};
window.show();
`);
await build({configFile:false,root:frontend,plugins:[react()],logLevel:'error',define:{'process.env.NODE_ENV':JSON.stringify('production')},
 resolve:{alias:{react:path.join(frontend,'node_modules/react'),'react-dom':path.join(frontend,'node_modules/react-dom')}},
 build:{outDir:out,emptyOutDir:false,lib:{entry,name:'Fixture',formats:['iife'],fileName:()=>'fixture.js'},cssCodeSplit:false,minify:false}});
const js=await readFile(path.join(out,'fixture.js'),'utf8');const css=await readFile(path.join(out,'fledge.css'),'utf8');
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[],requests=[];
page.on('pageerror',e=>errors.push(e.message));
await page.route('**/*',route=>{requests.push(route.request().url());return route.abort();});
try{
 await page.setContent('<style>'+css+'</style><div id="root"></div>');await page.addScriptTag({content:js});
 const launcher=page.getByRole('button',{name:'Telegram alerts',exact:true});await launcher.click();
 const dialog=page.getByRole('dialog',{name:'Telegram alerts',exact:true});
 await dialog.getByText('Daily recap',{exact:true}).waitFor();await dialog.getByText('AI spending notice',{exact:true}).waitFor();
 await dialog.getByText('EXMP · Price move',{exact:true}).waitFor();
 await dialog.getByText('Delivered',{exact:true}).waitFor();await dialog.getByText('Delivery unconfirmed',{exact:true}).waitFor();
 await dialog.getByText('Not forwarded',{exact:true}).waitFor();
 assert.equal(await dialog.locator('script').count(),0);
 await dialog.getByText('Authored <script> unconfirmed send.',{exact:true}).waitFor();
 await dialog.getByText('What will arrive in Telegram?',{exact:true}).click();
 await dialog.getByText('Daily recaps of medium-priority updates, with evidence.',{exact:true}).waitFor();
 await dialog.getByText(/AI spending notices when confirmed charges/).waitFor();
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1000});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.ok(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth+1));
  await dialog.getByRole('heading',{name:'Recent deliveries',exact:true}).scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(out,'history-'+width+'.png'),animations:'disabled'});
 }
 await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});await launcher.waitFor({state:'visible'});
 assert.equal(await launcher.evaluate(el=>el===document.activeElement),true);
 await page.evaluate(()=>window.show({types:false}));await launcher.click();
 await dialog.getByText('Daily recap',{exact:true}).waitFor();
 await dialog.getByText('What will arrive in Telegram?',{exact:true}).click();
 assert.equal(await dialog.getByText('Daily recaps of medium-priority updates, with evidence.',{exact:true}).count(),0);
 assert.equal(await dialog.getByText(/AI spending notices when confirmed charges/).count(),0);
 assert.deepEqual(await page.evaluate(()=>window.actions),[]);assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
 console.log(JSON.stringify({passed:6,viewports:[1440,390,320],http_requests:0,output:out}));
}catch(error){console.error(JSON.stringify({output:out,errors,body:(await page.locator('body').innerText()).slice(0,2500)}));throw error;}
finally{await browser.close();}
