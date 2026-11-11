import { test, expect } from '@playwright/test';
import { openDemoPage, expectNoHorizontalPageOverflow } from './helpers.mjs';
const path='/settings/others/vip-rewards';
test('local rewards form saves and discards without live requests',async({page, baseURL})=>{
 const external=[];page.on('request',r=>{if(/^https?:/.test(r.url())&&new URL(r.url()).origin !== new URL(baseURL).origin)external.push(r.url());});
 await openDemoPage(page,path);
 await expect(page.getByRole('heading',{name:'VIP-Belohnungen',exact:true})).toBeVisible();
 await expect(page.getByText(/Lokaler Formulartest/)).toBeVisible();
 await expect(page.getByLabel('Vorschau: keine VIP-Vergabe und keine Spielernachrichten')).toBeChecked();
 const enabled=page.getByLabel('Neue VIP-Belohnungen aktivieren');await enabled.check();
 await page.getByRole('button',{name:'Einstellungen speichern',exact:true}).click();
 await expect(page.getByText(/Einstellungen gespeichert/)).toBeVisible();
 await enabled.uncheck();await page.getByRole('button',{name:'Änderungen verwerfen'}).click();await expect(enabled).toBeChecked();
 await page.screenshot({path:'../../outputs/next-release-local-20261111/form-desktop.png',fullPage:true});
 expect(external).toEqual([]);
});
test('local rewards form fits mobile',async({page})=>{
 await page.setViewportSize({width:390,height:844});await openDemoPage(page,path);
 await expectNoHorizontalPageOverflow(page);
 await page.screenshot({path:'../../outputs/next-release-local-20261111/form-mobile.png',fullPage:true});
});
