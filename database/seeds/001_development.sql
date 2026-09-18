-- Dados exclusivamente demonstrativos. O hash abaixo não representa uma senha utilizável.
INSERT INTO users (id, full_name, email, password_hash, role)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Usuário QA de Demonstração',
    'qa.demo@loadforge.local',
    'NOT_A_LOGIN_HASH_SPRINT_02',
    'QA'
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO projects (id, owner_id, name, description)
VALUES (
    '00000000-0000-0000-0000-000000000101',
    '00000000-0000-0000-0000-000000000001',
    'API Catálogo',
    'Projeto fictício para demonstração do protótipo. Nenhum alvo está autorizado.'
)
ON CONFLICT (owner_id, name) DO NOTHING;
