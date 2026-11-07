/** Delay a REAL response to reproduce a project switch during a save. */
import { assert, request, loginApi, loginUi, selectProject, shot, check, launch, stamp } from './browser-common.mjs'
const token = await loginApi()
const a = await request('POST', '/projects', { name: 'S09 race A ' + stamp }, 201, token)
const b = await request('POST', '/projects', { name: 'S09 race B ' + stamp }, 201, token)
const browser = await launch()
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } })
  await loginUi(page)
  await selectProject(page, a.name)
  let release, fetched
  const gate = new Promise(resolve => { release = resolve })
  const intercepted = new Promise(resolve => { fetched = resolve })
  await page.route(`**/api/projects/${a.id}/endpoints`, async route => {
    if (route.request().method() !== 'POST') return route.continue()
    const response = await route.fetch()
    fetched()
    await gate
    await route.fulfill({ response })
  })
  const form = page.locator('.endpoint-form')
  await form.getByLabel('Nome', { exact: true }).fill('Endpoint exclusivo de A')
  await form.getByLabel('URL do alvo').fill('http://target:8080')
  await form.getByRole('button', { name: 'Salvar endpoint' }).click()
  await intercepted
  await selectProject(page, b.name)
  await page.locator('.endpoint-form').getByLabel('Nome', { exact: true }).fill('Rascunho de B')
  const lateRefresh = page.waitForResponse(r => r.url().endsWith(`/projects/${a.id}/endpoints`) && r.request().method() === 'GET').catch(() => null)
  release()
  // Fixed implementation may discard the response before requesting a refresh.
  await Promise.race([lateRefresh, new Promise(resolve => setTimeout(resolve, 1500))])
  await page.waitForTimeout(200)
  await shot(page, 'contexto-apos-resposta-atrasada')
  await check('NAV-RACE-01', 'Projeto B conserva seu rascunho e nao mostra endpoint de A', async () => {
    assert.equal(await page.locator('.endpoint-item').filter({ hasText: 'Endpoint exclusivo de A' }).count(), 0)
    assert.equal(await page.locator('.endpoint-form').getByLabel('Nome', { exact: true }).inputValue(), 'Rascunho de B')
    assert.equal((await request('GET', `/projects/${b.id}/endpoints`, undefined, 200, token)).length, 0)
    assert.equal((await request('GET', `/projects/${a.id}/endpoints`, undefined, 200, token)).length, 1)
  }, page)
} finally { await browser.close() }
