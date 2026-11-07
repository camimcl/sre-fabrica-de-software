import test from 'node:test'
import assert from 'node:assert/strict'
import { api } from '../src/api.ts'
import { download } from '../src/download.ts'

for (const payload of [null, [], {}, 42, 'upstream unavailable']) {
  test(`HTTP errors retain a readable fallback for ${JSON.stringify(payload)}`, async () => {
    const original = globalThis.fetch
    try {
      globalThis.fetch = async () => ({ ok: false, status: 502, json: async () => payload })
      await assert.rejects(api('/projects'), /Falha na operação \(502\)/)
      await assert.rejects(download('/report.pdf', 'test-only', 'report.pdf'), /Falha na exportação \(502\)/)
    } finally { globalThis.fetch = original }
  })
}

test('validation errors name the field and preserve the API explanation', async () => {
  const original = globalThis.fetch
  try {
    globalThis.fetch = async () => ({ ok: false, status: 422, json: async () => ({ detail: [null, { loc: ['body', 'name'], msg: 'Field required' }] }) })
    await assert.rejects(api('/projects'), /name: Field required/)
  } finally { globalThis.fetch = original }
})

test('HTML or empty error responses keep status-specific fallbacks', async () => {
  const original = globalThis.fetch
  try {
    globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => { throw new SyntaxError('not JSON') } })
    await assert.rejects(api('/projects'), /Falha na operação \(503\)/)
    await assert.rejects(download('/report.pdf', 'test-only', 'report.pdf'), /Falha na exportação \(503\)/)
  } finally { globalThis.fetch = original }
})
