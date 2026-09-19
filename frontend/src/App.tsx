import { useEffect, useState, type FormEvent } from 'react'

type Role = 'QA' | 'VIEWER'
type User = { id: string; full_name: string; email: string; role: Role }
type Project = {
  id: string
  owner_id: string
  name: string
  description: string | null
}
type Endpoint = {
  id: string
  project_id: string
  name: string
  base_url: string
  http_method: string
  authorization_confirmed: boolean
  authorization_evidence: string | null
}
type ProjectForm = { name: string; description: string }
type EndpointForm = {
  name: string
  base_url: string
  http_method: string
  authorization_confirmed: boolean
  authorization_evidence: string
}
type UserForm = { full_name: string; email: string; password: string; role: Role }

const blankProject: ProjectForm = { name: '', description: '' }
const blankEndpoint: EndpointForm = {
  name: '',
  base_url: '',
  http_method: 'GET',
  authorization_confirmed: false,
  authorization_evidence: '',
}
const blankUser: UserForm = { full_name: '', email: '', password: '', role: 'VIEWER' }

async function api<T>(path: string, method = 'GET', body?: unknown, token?: string): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: {
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    const detail = data.detail
    throw new Error(typeof detail === 'string' ? detail : `Falha na operação (${response.status})`)
  }
  return response.status === 204 ? (undefined as T) : (await response.json()) as T
}

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('loadforge-token') || '')
  const [user, setUser] = useState<User | null>(null)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [auth, setAuth] = useState({ full_name: '', email: '', password: '' })
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [projectForm, setProjectForm] = useState<ProjectForm>(blankProject)
  const [editingProject, setEditingProject] = useState<string | null>(null)
  const [endpoints, setEndpoints] = useState<Endpoint[]>([])
  const [endpointForm, setEndpointForm] = useState<EndpointForm>(blankEndpoint)
  const [editingEndpoint, setEditingEndpoint] = useState<string | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [userForm, setUserForm] = useState<UserForm>(blankUser)
  const [editingUser, setEditingUser] = useState<string | null>(null)
  const [notice, setNotice] = useState('')

  const selectedProject = projects.find((project) => project.id === selectedId)
  const canEdit = user?.role === 'QA' && selectedProject?.owner_id === user.id
  const qaCount = users.filter((entry) => entry.role === 'QA').length

  function report(error: unknown) {
    setNotice(error instanceof Error ? error.message : 'Ocorreu um erro inesperado.')
  }

  async function refreshProjects(accessToken: string) {
    const rows = await api<Project[]>('/projects', 'GET', undefined, accessToken)
    setProjects(rows)
    setSelectedId((current) => current && rows.some((row) => row.id === current) ? current : rows[0]?.id ?? null)
  }

  async function refreshEndpoints(projectId: string, accessToken: string) {
    setEndpoints(await api<Endpoint[]>(`/projects/${projectId}/endpoints`, 'GET', undefined, accessToken))
  }

  async function refreshUsers(accessToken: string, currentUser: User) {
    if (currentUser.role === 'QA') {
      setUsers(await api<User[]>('/users', 'GET', undefined, accessToken))
      return
    }
    setUsers([await api<User>('/auth/me', 'GET', undefined, accessToken)])
  }

  useEffect(() => {
    if (!token) return
    Promise.all([
      api<User>('/auth/me', 'GET', undefined, token),
      api<Project[]>('/projects', 'GET', undefined, token),
    ]).then(([currentUser, rows]) => {
      setUser(currentUser)
      setProjects(rows)
      setSelectedId(rows[0]?.id ?? null)
      if (currentUser.role === 'QA') {
        api<User[]>('/users', 'GET', undefined, token).then(setUsers).catch(report)
      } else {
        setUsers([currentUser])
      }
    }).catch((error) => {
      report(error)
      sessionStorage.removeItem('loadforge-token')
      setToken('')
    })
  }, [token])

  useEffect(() => {
    if (!token || !selectedId) {
      setEndpoints([])
      return
    }
    refreshEndpoints(selectedId, token).catch(report)
  }, [selectedId, token])

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice('')
    try {
      if (mode === 'register') {
        await api<User>('/auth/register', 'POST', auth)
        setMode('login')
        setNotice('Conta Visualizador criada. Entre com seu e-mail e senha.')
        return
      }
      const result = await api<{ access_token: string }>('/auth/login', 'POST', {
        email: auth.email, password: auth.password,
      })
      sessionStorage.setItem('loadforge-token', result.access_token)
      setToken(result.access_token)
      setAuth({ full_name: '', email: '', password: '' })
    } catch (error) {
      report(error)
    }
  }

  function logout() {
    sessionStorage.removeItem('loadforge-token')
    setToken('')
    setUser(null)
    setProjects([])
    setEndpoints([])
    setUsers([])
    setEditingUser(null)
    setUserForm(blankUser)
    setNotice('Sessão encerrada neste navegador.')
  }

  async function submitProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      const path = editingProject ? `/projects/${editingProject}` : '/projects'
      const saved = await api<Project>(path, editingProject ? 'PUT' : 'POST', {
        name: projectForm.name,
        description: projectForm.description || null,
      }, token)
      await refreshProjects(token)
      setSelectedId(saved.id)
      setProjectForm(blankProject)
      setEditingProject(null)
      setNotice('Projeto salvo no banco de dados.')
    } catch (error) { report(error) }
  }

  async function removeProject(project: Project) {
    if (!window.confirm(`Excluir o projeto “${project.name}”?`)) return
    try {
      await api<void>(`/projects/${project.id}`, 'DELETE', undefined, token)
      await refreshProjects(token)
      setNotice('Projeto excluído.')
    } catch (error) { report(error) }
  }

  async function submitEndpoint(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedId) return
    try {
      const path = editingEndpoint
        ? `/projects/${selectedId}/endpoints/${editingEndpoint}`
        : `/projects/${selectedId}/endpoints`
      await api<Endpoint>(path, editingEndpoint ? 'PUT' : 'POST', {
        ...endpointForm,
        authorization_evidence: endpointForm.authorization_evidence || null,
      }, token)
      await refreshEndpoints(selectedId, token)
      setEndpointForm(blankEndpoint)
      setEditingEndpoint(null)
      setNotice('Endpoint salvo no banco de dados.')
    } catch (error) { report(error) }
  }

  async function removeEndpoint(endpoint: Endpoint) {
    if (!selectedId || !window.confirm(`Excluir o endpoint “${endpoint.name}”?`)) return
    try {
      await api<void>(`/projects/${selectedId}/endpoints/${endpoint.id}`, 'DELETE', undefined, token)
      await refreshEndpoints(selectedId, token)
      setNotice('Endpoint excluído.')
    } catch (error) { report(error) }
  }

  async function submitUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      if (editingUser) {
        const saved = await api<User>(`/users/${editingUser}`, 'PUT', {
          ...userForm,
          password: userForm.password || null,
        }, token)
        const currentUser = saved.id === user?.id ? saved : user
        if (currentUser) {
          setUser(currentUser)
          await refreshUsers(token, currentUser)
        }
        setEditingUser(null)
        setUserForm(blankUser)
        setNotice('Usuário atualizado no banco de dados.')
        return
      }
      await api<User>('/users', 'POST', userForm, token)
      if (user) await refreshUsers(token, user)
      setUserForm(blankUser)
      setNotice('Usuário criado no banco de dados.')
    } catch (error) { report(error) }
  }

  function editUser(entry: User) {
    setEditingUser(entry.id)
    setUserForm({
      full_name: entry.full_name,
      email: entry.email,
      password: '',
      role: entry.role,
    })
  }

  function cancelUserEdit() {
    setEditingUser(null)
    setUserForm(blankUser)
  }

  async function removeUser(entry: User) {
    const ownAccount = entry.id === user?.id
    const message = ownAccount
      ? 'Excluir sua própria conta? Esta ação encerrará a sessão.'
      : `Excluir o usuário “${entry.full_name}”?`
    if (!window.confirm(message)) return
    try {
      await api<void>(`/users/${entry.id}`, 'DELETE', undefined, token)
      if (ownAccount) {
        sessionStorage.removeItem('loadforge-token')
        setToken('')
        setUser(null)
        setProjects([])
        setEndpoints([])
        setUsers([])
        setEditingUser(null)
        setUserForm(blankUser)
        setNotice('Conta excluída e sessão encerrada.')
        return
      }
      if (user) await refreshUsers(token, user)
      if (editingUser === entry.id) cancelUserEdit()
      setNotice('Usuário excluído.')
    } catch (error) { report(error) }
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">LF</span><div><strong>LoadForge</strong><small>Ambiente local · Sprint 03</small></div></div>
        {user && <div className="account"><span>{user.full_name} <em>{user.role === 'QA' ? 'QA' : 'Visualizador'}</em></span><button className="link-button" onClick={logout}>Sair</button></div>}
      </header>

      {!user ? (
        <main className="auth-layout">
          <div className="intro"><span className="eyebrow">Plataforma de confiabilidade</span><h1>Prepare testes de carga com controle.</h1><p>Cadastre projetos e alvos autorizados. O acesso de QA administra os registros; o Visualizador consulta os dados persistidos.</p><div className="intro-note">A conexão com o PostgreSQL e os perfis de acesso já fazem parte deste ambiente.</div></div>
          <section className="card auth-card">
            <div className="tabs"><button className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>Entrar</button><button className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>Criar conta</button></div>
            <h2>{mode === 'login' ? 'Acesse sua conta' : 'Criar acesso Visualizador'}</h2>
            <form onSubmit={submitAuth} className="stack">
              {mode === 'register' && <label>Nome completo<input required minLength={2} maxLength={160} value={auth.full_name} onChange={(event) => setAuth({ ...auth, full_name: event.target.value })} /></label>}
              <label>E-mail<input required type="email" value={auth.email} onChange={(event) => setAuth({ ...auth, email: event.target.value })} /></label>
              <label>Senha<input required type="password" minLength={mode === 'register' ? 12 : undefined} value={auth.password} onChange={(event) => setAuth({ ...auth, password: event.target.value })} /></label>
              <button className="primary" type="submit">{mode === 'login' ? 'Entrar' : 'Criar conta'}</button>
            </form>
            {mode === 'register' && <p className="helper">Contas de QA são criadas pelo responsável do ambiente ou por outro QA.</p>}
          </section>
        </main>
      ) : (
        <main className="workspace">
          <div className="page-heading"><div><span className="eyebrow">Área de trabalho</span><h1>Projetos e endpoints</h1><p>Dados salvos no PostgreSQL e disponíveis conforme o seu perfil.</p></div><span className="role-pill">{user.role === 'QA' ? 'Acesso QA' : 'Somente leitura'}</span></div>
          <div className="columns">
            <section className="card projects-card">
              <div className="section-heading"><h2>Projetos</h2><span>{projects.length}</span></div>
              {projects.length === 0 ? <p className="empty">Nenhum projeto cadastrado.</p> : <div className="project-list">{projects.map((project) => <button key={project.id} className={selectedId === project.id ? 'project-item selected' : 'project-item'} onClick={() => { setSelectedId(project.id); setEditingEndpoint(null); setEndpointForm(blankEndpoint) }}><strong>{project.name}</strong><small>{project.description || 'Sem descrição'}</small></button>)}</div>}
              {user.role === 'QA' && <form className="stack project-form" onSubmit={submitProject}><h3>{editingProject ? 'Editar projeto' : 'Novo projeto'}</h3><label>Nome<input required maxLength={120} value={projectForm.name} onChange={(event) => setProjectForm({ ...projectForm, name: event.target.value })} /></label><label>Descrição<textarea maxLength={5000} value={projectForm.description} onChange={(event) => setProjectForm({ ...projectForm, description: event.target.value })} /></label><div className="actions"><button className="primary" type="submit">Salvar projeto</button>{editingProject && <button type="button" onClick={() => { setEditingProject(null); setProjectForm(blankProject) }}>Cancelar</button>}</div></form>}
            </section>
            <section className="card detail-card">
              {selectedProject ? <>
                <div className="section-heading"><div><span className="eyebrow">Projeto selecionado</span><h2>{selectedProject.name}</h2></div>{canEdit && <div className="actions"><button onClick={() => { setEditingProject(selectedProject.id); setProjectForm({ name: selectedProject.name, description: selectedProject.description || '' }) }}>Editar</button><button className="danger" onClick={() => removeProject(selectedProject)}>Excluir</button></div>}</div>
                <p className="muted">{selectedProject.description || 'Sem descrição.'}</p>
                <div className="section-heading endpoint-heading"><h3>Endpoints</h3><span>{endpoints.length}</span></div>
                {endpoints.length === 0 ? <p className="empty">Nenhum endpoint cadastrado.</p> : <div className="endpoint-list">{endpoints.map((endpoint) => <article className="endpoint-item" key={endpoint.id}><div><strong>{endpoint.name}</strong><code>{endpoint.http_method} {endpoint.base_url}</code><small>{endpoint.authorization_confirmed ? 'Autorização registrada' : 'Autorização pendente'}</small></div>{canEdit && <div className="actions"><button onClick={() => { setEditingEndpoint(endpoint.id); setEndpointForm({ name: endpoint.name, base_url: endpoint.base_url, http_method: endpoint.http_method, authorization_confirmed: endpoint.authorization_confirmed, authorization_evidence: endpoint.authorization_evidence || '' }) }}>Editar</button><button className="danger" onClick={() => removeEndpoint(endpoint)}>Excluir</button></div>}</article>)}</div>}
                {canEdit && <form className="stack endpoint-form" onSubmit={submitEndpoint}><h3>{editingEndpoint ? 'Editar endpoint' : 'Novo endpoint'}</h3><div className="form-row"><label>Nome<input required maxLength={120} value={endpointForm.name} onChange={(event) => setEndpointForm({ ...endpointForm, name: event.target.value })} /></label><label>Método<select value={endpointForm.http_method} onChange={(event) => setEndpointForm({ ...endpointForm, http_method: event.target.value })}>{['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'].map((method) => <option key={method}>{method}</option>)}</select></label></div><label>URL do alvo<input required type="url" placeholder="https://exemplo.com/api" value={endpointForm.base_url} onChange={(event) => setEndpointForm({ ...endpointForm, base_url: event.target.value })} /></label><label className="checkbox"><input type="checkbox" checked={endpointForm.authorization_confirmed} onChange={(event) => setEndpointForm({ ...endpointForm, authorization_confirmed: event.target.checked })} /> Autorização do alvo confirmada</label><label>Evidência da autorização<textarea required={endpointForm.authorization_confirmed} maxLength={5000} value={endpointForm.authorization_evidence} onChange={(event) => setEndpointForm({ ...endpointForm, authorization_evidence: event.target.value })} /></label><div className="actions"><button className="primary" type="submit">Salvar endpoint</button>{editingEndpoint && <button type="button" onClick={() => { setEditingEndpoint(null); setEndpointForm(blankEndpoint) }}>Cancelar</button>}</div></form>}
              </> : <p className="empty">Selecione ou crie um projeto para visualizar os endpoints.</p>}
            </section>
          </div>
          <section className="card users-card">
            <div className="section-heading">
              <div>
                <span className="eyebrow">{user.role === 'QA' ? 'Controle de acesso' : 'Dados da conta'}</span>
                <h2>{user.role === 'QA' ? 'Usuários' : 'Meu perfil'}</h2>
              </div>
              <span>{users.length}</span>
            </div>
            <div className="users-layout">
              <div className="user-list">
                {users.map((entry) => {
                  const canManage = user.role === 'QA' || entry.id === user.id
                  const lastQa = entry.role === 'QA' && qaCount === 1
                  return <div className="user-item" key={entry.id}>
                    <div className="user-summary">
                      <div><strong>{entry.full_name}</strong><small>{entry.email}</small></div>
                      <span className="role-pill">{entry.role === 'QA' ? 'QA' : 'Visualizador'}</span>
                    </div>
                    {canManage && <div className="actions user-actions">
                      <button onClick={() => editUser(entry)}>Editar</button>
                      <button
                        className="danger"
                        disabled={lastQa}
                        title={lastQa ? 'O último QA não pode ser excluído' : undefined}
                        onClick={() => removeUser(entry)}
                      >Excluir</button>
                    </div>}
                  </div>
                })}
              </div>
              {(user.role === 'QA' || editingUser) ? <form className="stack" onSubmit={submitUser}>
                <h3>{editingUser ? 'Editar usuário' : 'Novo usuário'}</h3>
                <label>Nome completo<input required minLength={2} maxLength={160} value={userForm.full_name} onChange={(event) => setUserForm({ ...userForm, full_name: event.target.value })} /></label>
                <label>E-mail<input required type="email" value={userForm.email} onChange={(event) => setUserForm({ ...userForm, email: event.target.value })} /></label>
                <div className="form-row">
                  <label>{editingUser ? 'Nova senha (opcional)' : 'Senha inicial'}<input required={!editingUser} type="password" minLength={12} value={userForm.password} onChange={(event) => setUserForm({ ...userForm, password: event.target.value })} /></label>
                  <label>Perfil<select disabled={user.role !== 'QA'} value={userForm.role} onChange={(event) => setUserForm({ ...userForm, role: event.target.value as Role })}><option value="VIEWER">Visualizador</option><option value="QA">QA</option></select></label>
                </div>
                <div className="actions">
                  <button className="primary" type="submit">{editingUser ? 'Salvar alterações' : 'Criar usuário'}</button>
                  {editingUser && <button type="button" onClick={cancelUserEdit}>Cancelar</button>}
                </div>
              </form> : <p className="empty profile-help">Use o botão Editar para atualizar seu nome, e-mail ou senha.</p>}
            </div>
          </section>
        </main>
      )}
      {notice && <div className="notice" role="status"><span>{notice}</span><button aria-label="Fechar aviso" onClick={() => setNotice('')}>×</button></div>}
      <footer>LoadForge · Testes apenas em sistemas próprios ou autorizados.</footer>
    </div>
  )
}
