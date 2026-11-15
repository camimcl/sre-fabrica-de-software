const labels: Record<string, string> = {
  PENDING: 'Pendente', RUNNING: 'Em execução', COMPLETED: 'Concluída',
  CANCELLED: 'Cancelada', FAILED: 'Falhou', CANDIDATE: 'Candidato',
  APPROVED: 'Aprovado', RETIRED: 'Retirado', FIXED: 'Fixa', RULES: 'Regras',
  AI_HYBRID: 'IA híbrida', INCREASE: 'Aumentar', HOLD: 'Manter',
  DECREASE: 'Reduzir', STOP: 'Parar', CREATE: 'Criação', UPDATE: 'Alteração',
  DELETE: 'Exclusão', EXECUTE: 'Execução', project: 'projeto', scenario: 'cenário',
  endpoint: 'endpoint', execution: 'execução', user: 'usuário',
}

/** Preserve unknown historical values instead of inventing an interpretation. */
export function label(value: string) { return labels[value] ?? value }

const messages: Record<string, string> = {
  'Invalid or expired credentials': 'Sua sessão expirou ou não é válida. Entre novamente.',
  'Invalid email or password': 'E-mail ou senha incorretos.',
  'QA role required': 'Esta ação exige o perfil QA.',
  'Project owner required': 'Somente o QA proprietário pode alterar este projeto.',
  'Only QA can change user roles': 'Somente QA pode alterar perfis de usuário.',
  'The last QA account cannot be removed': 'O último QA do ambiente não pode ser removido.',
  'Email already registered': 'Este e-mail já está cadastrado.',
  'A project with this name already exists for this owner': 'Você já possui um projeto com esse nome.',
  'Remove dependent executions before deleting the scenario': 'Este cenário possui execuções. Preserve o histórico e utilize outro cenário.',
  'Remove dependent scenarios before deleting the endpoint': 'Remova primeiro os cenários vinculados a este endpoint.',
  'Remove dependent endpoints and scenarios before deleting the project': 'Remova primeiro os endpoints e cenários vinculados ao projeto.',
  'Invalid execution state transition': 'A situação da execução mudou. Atualize a consulta antes de tentar novamente.',
}
export function messageForUser(message: string) { return messages[message] ?? message }
