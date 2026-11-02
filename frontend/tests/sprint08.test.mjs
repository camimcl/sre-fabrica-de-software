import test from 'node:test'
import assert from 'node:assert/strict'
import { periodQuery, readableSummary } from '../src/query.ts'
import { download } from '../src/download.ts'

test('local date filters preserve the whole day and the other criteria', () => {
  const previous = process.env.TZ
  try {
    for (const zone of ['UTC', 'America/Sao_Paulo']) {
      process.env.TZ = zone
      const query = new URLSearchParams(periodQuery('2026-11-02', '2026-11-02', { strategy: 'FIXED', search: 'API & QA' }))
      const start = new Date(query.get('date_from')); const end = new Date(query.get('date_to'))
      assert.equal(start.getHours(), 0)
      assert.equal(end.getHours(), 23)
      assert.equal(end.getMilliseconds(), 999)
      assert.equal(start.getDate(), 2)
      assert.equal(end.getDate(), 2)
      assert.equal(query.get('search'), 'API & QA')
      assert.equal(query.get('strategy'), 'FIXED')
    }
    assert.equal(periodQuery('', ''), '')
  } finally {
    if (previous === undefined) delete process.env.TZ
    else process.env.TZ = previous
  }
})

test('legacy audit details do not crash the operations panel', () => {
  assert.equal(readableSummary(null), 'Sem detalhes adicionais.')
  assert.equal(readableSummary('legacy operation'), 'legacy operation')
  assert.equal(readableSummary('{"role":"VIEWER"}'), '{\n  "role": "VIEWER"\n}')
})

test('downloads expose the missing report action and API errors', async () => {
  const originalFetch = globalThis.fetch
  try {
    globalThis.fetch = async () => ({ ok: false, status: 404, json: async () => ({ detail: 'Execution report not found' }) })
    await assert.rejects(download('/report.pdf', 'test-token', 'report.pdf'), /QA proprietário/)
    globalThis.fetch = async () => ({ ok: false, status: 403, json: async () => ({ detail: 'QA role required' }) })
    await assert.rejects(download('/report.pdf', 'test-token', 'report.pdf'), /QA role required/)
  } finally { globalThis.fetch = originalFetch }
})

test('successful downloads use authentication and release temporary resources', async () => {
  const originalFetch = globalThis.fetch; const originalDocument = globalThis.document
  const originalCreate = URL.createObjectURL; const originalRevoke = URL.revokeObjectURL
  const events = []
  const anchor = { href: '', download: '', click() { events.push('click') }, remove() { events.push('remove') } }
  try {
    globalThis.fetch = async (path, options) => {
      assert.equal(path, '/api/report.pdf')
      assert.equal(options.headers.Authorization, 'Bearer test-token')
      return { ok: true, blob: async () => new Blob(['PDF']) }
    }
    globalThis.document = { createElement: () => anchor, body: { appendChild() { events.push('append') } } }
    URL.createObjectURL = () => 'blob:test'
    URL.revokeObjectURL = (url) => { assert.equal(url, 'blob:test'); events.push('revoke') }
    await download('/report.pdf', 'test-token', 'report.pdf')
    assert.equal(anchor.download, 'report.pdf')
    assert.deepEqual(events, ['append', 'click', 'remove', 'revoke'])
  } finally {
    globalThis.fetch = originalFetch; globalThis.document = originalDocument
    URL.createObjectURL = originalCreate; URL.revokeObjectURL = originalRevoke
  }
})
