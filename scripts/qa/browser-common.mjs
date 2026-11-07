import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
import assert from 'node:assert/strict'
export { assert }
const require = createRequire(import.meta.url)
export const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
export const local = path.join(root, '.qa-local')
export const credentials = JSON.parse(fs.readFileSync(path.join(local, 'credentials.json'), 'utf8'))
export const origin = 'http://127.0.0.1:5189'
export const stamp = new Date().toISOString().replace(/[:.]/g, '-')
export const evidence = path.join(local, 'browser-' + stamp)
fs.mkdirSync(evidence, { recursive: true })
export const records = []
export async function request(method, route, data, expected = 200, token) {
  const response = await fetch('http://127.0.0.1:58109' + route, {
    method, headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}),
      ...(data === undefined ? {} : { 'Content-Type': 'application/json' }) },
    body: data === undefined ? undefined : JSON.stringify(data),
  })
  assert.equal(response.status, expected, `${method} ${route}: status ${response.status}`)
  return response.status === 204 ? null : response.json()
}
export async function loginApi() {
  return (await request('POST', '/auth/login', { email: credentials.qa_email, password: credentials.qa_password })).access_token
}
export async function loginUi(page, email = credentials.qa_email, password = credentials.qa_password) {
  await page.goto(origin)
  await page.getByLabel('E-mail', { exact: true }).fill(email)
  await page.getByLabel('Senha', { exact: true }).fill(password)
  await page.locator('form').getByRole('button', { name: 'Entrar', exact: true }).click()
  await page.getByRole('button', { name: 'Sair', exact: true }).waitFor()
}
export async function selectProject(page, name) {
  await page.getByRole('button', { name: 'Projetos', exact: true }).click()
  await page.locator('.project-item').filter({ hasText: name }).click()
  await page.locator('.detail-card h2').filter({ hasText: name }).waitFor()
}
export async function shot(page, name) {
  await page.screenshot({ path: path.join(evidence, name + '.png'), fullPage: true })
}
export async function check(id, expected, action, page) {
  try {
    const obtained = await action()
    records.push({ id, expected, obtained: obtained || expected, status: 'PASS' })
    console.log(id + ': PASS')
  } catch (error) {
    records.push({ id, expected, obtained: String(error), status: 'FAIL' })
    if (page) await shot(page, id + '-failure')
    throw error
  } finally {
    fs.writeFileSync(path.join(evidence, 'results.json'), JSON.stringify({ captured_at: new Date().toISOString(), records }, null, 2))
    fs.writeFileSync(path.join(local, 'last-browser-path.txt'), evidence)
  }
}

export async function launch() {
  return chromium.launch({ channel: process.env.QA_BROWSER_CHANNEL || 'msedge', headless: true })
}
