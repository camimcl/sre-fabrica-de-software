import { assert, request, loginApi, loginUi, selectProject, shot, check, launch, stamp } from './browser-common.mjs'
const token = await loginApi()
const project = await request('POST', '/projects', { name: 'S09 periodo ' + stamp }, 201, token)
const browser = await launch()
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 960 } })
  await loginUi(page)
  await selectProject(page, project.name)
  let release, captured
  const gate = new Promise(resolve => { release = resolve })
  const pending = new Promise(resolve => { captured = resolve })
  await page.route(`**/api/projects/${project.id}/dashboard*`, async route => {
    const response = await route.fetch()
    captured()
    await gate
    await route.fulfill({ response })
  })
  await page.getByRole('navigation').getByRole('button', { name: 'Dashboard', exact: true }).click()
  await pending
  await page.getByLabel('De', { exact: true }).fill('2026-11-07')
  await page.getByLabel('Até', { exact: true }).fill('2026-11-06')
  await page.getByRole('alert').waitFor()
  release()
  await page.waitForTimeout(250)
  await shot(page, 'periodo-invalido-durante-consulta')
  await check('NAV-RACE-02', 'Periodo invalido mostra validacao sem carregamento eterno nem dados antigos', async () => {
    assert.equal(await page.getByText('Carregando indicadores…', { exact: true }).count(), 0)
    assert.equal(await page.locator('.s7-kpis').count(), 0)
    await page.getByRole('button', { name: 'Limpar filtros' }).click()
    await page.locator('.s7-kpis').waitFor()
  }, page)
} finally { await browser.close() }
