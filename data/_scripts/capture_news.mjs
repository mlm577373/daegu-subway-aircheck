import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
const req=createRequire('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright/package.json');
const {chromium}=req('playwright');
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const B='outputs/submission_draft/_build/news';await fs.mkdir(B,{recursive:true});
for(const [name,url] of [['sbs','https://news.sbs.co.kr/news/endPage.do?news_id=N1008448922'],['yeongnam','https://www.yeongnam.com/web/view.php?key=20240418010002733']]){
 const page=await browser.newPage({viewport:{width:1440,height:1200},deviceScaleFactor:1});
 await page.goto(url,{waitUntil:'domcontentloaded',timeout:60000});
 await page.waitForTimeout(3500);
 await page.screenshot({path:B+'/'+name+'_page.png',fullPage:false});
 const info=await page.locator('h1,h2,h3,img,video').evaluateAll(els=>els.map(e=>({tag:e.tagName,text:e.innerText||e.alt,src:e.currentSrc||e.src,box:{x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y,w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height}})).filter(e=>e.box.w>250));
 await fs.writeFile(B+'/'+name+'_elements.json',JSON.stringify(info,null,2));
 console.log(name,JSON.stringify(info).slice(0,6500));await page.close();
}await browser.close();
