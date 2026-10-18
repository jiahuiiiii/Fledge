// Standalone blind review, authored fixtures only; no Fledge server or HTTP.
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const out=await mkdtemp(path.join(tmpdir(),'fledge-blind-review-'));
const fixture=path.join(out,'authored-review.html');
execFileSync(path.join(root,'.venv/bin/python'),['-c',`
import sys
from experiments.soclaas_replay import owner_quality_set as Q
packets=[dict(company=dict(symbol=s,name='Example company'),sources=[dict(id=f'{s}-{channel}-{i}',label=f'item_{i}',channel=channel,title='Authored headline </script><img src=x>',published_at='2026-10-16T12:00:00Z',passages=[dict(id='p0',quote='Title'),dict(id='p1',quote='This is invented evidence for a browser check.')]) for channel in ('news','social') for i in range(20)]) for s in ('EXA','EXB')]
open(sys.argv[1],'w').write(Q.render(Q.build(packets)))
`,fixture],{cwd:root});
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE));
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
const errors=[],requests=[];
page.on('pageerror',e=>errors.push(e.message));
await page.route('**/*',route=>{
 const url=route.request().url();
 if(url===pathToFileURL(fixture).href)return route.continue();
 requests.push(url);return route.abort();
});
try{
 await page.goto(pathToFileURL(fixture).href);
 await page.getByText('0 of 50 sources labelled',{exact:true}).waitFor();
 assert.equal(await page.locator('img').count(),0);
 assert.equal(await page.locator('#sentiment').inputValue(),'');
 await page.getByText('How to label',{exact:true}).click();
 assert.ok(await page.locator('details').first().evaluate(e=>e.open));
 await page.getByText('How to label',{exact:true}).click();
 assert.ok(await page.getByRole('button',{name:'Download my 50 answers'}).isDisabled());
 await page.locator('#relevance').selectOption('relevant');
 await page.locator('#sentiment').selectOption('neutral');
 await page.reload();
 assert.equal(await page.locator('#sentiment').inputValue(),'neutral');
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1000});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(out,'review-'+width+'.png'),fullPage:true});
 }
 for(let i=1;i<50;i++){
  await page.getByRole('button',{name:'Next',exact:true}).click();
  assert.equal(await page.locator('#sentiment').inputValue(),'');
  await page.locator('#relevance').selectOption('relevant');
  await page.locator('#sentiment').selectOption('neutral');
 }
 await page.getByText('50 of 50 sources labelled',{exact:true}).waitFor();
 assert.ok(await page.getByRole('button',{name:'Download my 50 answers'}).isDisabled());
 await page.locator('#confirm').check();
 const downloadEvent=page.waitForEvent('download');
 await page.getByRole('button',{name:'Download my 50 answers'}).click();
 const download=await downloadEvent;
 const file=path.join(out,'authored-test-answers.json');await download.saveAs(file);
 const answers=JSON.parse(await readFile(file,'utf8'));
 assert.equal(Object.keys(answers.answers).length,50);
 assert.equal(answers.independently_labelled_by_owner,true);
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
 console.log(JSON.stringify({passed:7,viewports:[1440,390,320],http_requests:0,authored_fixtures_only:true,output:out}));
}finally{await browser.close();}
