import test from 'node:test'
import assert from 'node:assert/strict'
import { label, messageForUser } from '../src/presentation.ts'

test('execution outcomes and strategies have user-facing Portuguese names', () => {
  assert.equal(label('RUNNING'), 'Em execução')
  assert.equal(label('FAILED'), 'Falhou')
  assert.equal(label('AI_HYBRID'), 'IA híbrida')
  assert.equal(label('EXECUTE'), 'Execução')
})

test('unknown historical labels and server details remain visible', () => {
  assert.equal(label('ARCHIVED_LEGACY'), 'ARCHIVED_LEGACY')
  assert.equal(messageForUser('Connection interrupted at window 4'), 'Connection interrupted at window 4')
})

test('known session and permission failures guide the user', () => {
  assert.match(messageForUser('Invalid or expired credentials'), /Entre novamente/)
  assert.match(messageForUser('Project owner required'), /QA proprietário/)
})
