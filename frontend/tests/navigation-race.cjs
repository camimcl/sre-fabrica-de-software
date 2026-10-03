// Run only against a disposable, seeded environment with an authorized local target.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('playwright');

async function main() {
  const fixture = JSON.parse(fs.readFileSync(process.env.LOADFORGE_E2E_FIXTURE, 'utf8'));
  const browser = await chromium.launch({headless: true, channel: process.env.LOADFORGE_BROWSER || 'msedge'});
  try {
    const page = await browser.newPage();
    await page.goto(process.env.LOADFORGE_E2E_URL || 'http://127.0.0.1:55173');
    await page.getByLabel('E-mail', {exact:true}).fill(process.env.LOADFORGE_E2E_EMAIL);
    await page.getByLabel('Senha', {exact:true}).fill(process.env.LOADFORGE_E2E_PASSWORD);
    await page.locator('form').getByRole('button', {name:'Entrar',exact:true}).click();
    const panel = page.locator('.sprint-five-card');
    const scenario = panel.locator('.adaptive-column').nth(0).locator(':scope > select');
    const execution = panel.locator('.adaptive-column').nth(1).locator(':scope > select');
    const a = fixture.hybrid.execution;
    const b = fixture.rules.execution;
    await scenario.locator(`option[value="${a.scenario_id}"]`).waitFor({state:'attached'});
    let release;
    let received;
    const held = new Promise(resolve => { release = resolve; });
    const intercepted = new Promise(resolve => { received = resolve; });
    let delivered;
    const finished = new Promise(resolve => { delivered = resolve; });
    await page.route(`**/scenarios/${a.scenario_id}/executions`, async route => {
      const response = await route.fetch();
      received();
      await held;
      await route.fulfill({response});
      delivered();
    });
    await scenario.selectOption(a.scenario_id);
    await intercepted;
    await scenario.selectOption(b.scenario_id);
    await execution.locator(`option[value="${b.id}"]`).waitFor({state:'attached'});
    await execution.selectOption(b.id);
    release();
    await finished;
    // Allow the delayed response to reach React before checking the visible selection.
    await page.waitForTimeout(500);
    assert.equal(await scenario.inputValue(), b.scenario_id);
    assert.equal(await execution.inputValue(), b.id, 'Resposta antiga não pode substituir as execuções do cenário atual');
    assert.match(await panel.locator('.monitor-block').innerText(), /DECREASE/);
    console.log('PASS: resposta atrasada não troca a execução nem o monitor do cenário selecionado.');
    await page.unrouteAll({behavior:'wait'});
    await page.route('**/metric-windows', async route => {
      const response = await route.fetch();
      await new Promise(resolve => setTimeout(resolve, 2500));
      await route.fulfill({response});
    });
    await panel.getByLabel('Confirmo que tenho autorização para testar este alvo.').check();
    await panel.getByRole('button', {name:'Criar e iniciar'}).click();
    await page.waitForFunction(() => document.querySelector('.execution-status strong')?.textContent === 'RUNNING');
    const deadline = Date.now() + 16000;
    while (Date.now() < deadline && await panel.locator('.execution-status strong').innerText() !== 'COMPLETED') {
      await page.waitForTimeout(200);
    }
    assert.equal(await panel.locator('.execution-status strong').innerText(), 'COMPLETED', 'Polling lento deve atualizar o estado terminal');
    assert.match(await panel.locator('.monitor-block').innerText(), /DECREASE/);
    console.log('PASS: respostas acima de 2 segundos atualizam métricas e estado terminal.');
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
