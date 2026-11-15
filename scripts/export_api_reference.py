"""Generate a human-readable operation index from the committed OpenAPI file."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT/'docs/api/openapi.json'
target = ROOT/'docs/api/referencia.md'


def render():
    contract = json.loads(source.read_text(encoding='utf-8'))
    lines = ['# Referência completa das APIs', '',
             f"Contrato: {contract['info']['version']}. Gerado de [openapi.json](openapi.json).", '',
             'Schemas completos, exemplos, tipos e limites estão no OpenAPI e em `/docs` ou `/redoc`.',
             'UUIDs de exemplos são fictícios. Use IDs retornados pelos cadastros do seu ambiente.', '']
    count = 0
    for path, item in sorted(contract['paths'].items()):
        for method, operation in sorted(item.items()):
            count += 1
            lines += [f'## {method.upper()} `{path}`', '', operation['summary'], '', operation['description'], '',
                      'Autenticação: ' + ('Bearer obrigatório.' if operation.get('security') else 'Pública.'), '']
            parameters = operation.get('parameters', [])
            if parameters:
                lines += ['| Parâmetro | Local | Obrigatório | Tipo / contrato |', '|---|---|---|---|']
                for parameter in parameters:
                    schema = json.dumps(parameter.get('schema', {}), ensure_ascii=False).replace('|', '\\|')
                    lines.append(f"| `{parameter['name']}` | {parameter['in']} | {'Sim' if parameter.get('required') else 'Não'} | `{schema}` |")
                lines.append('')
            body = operation.get('requestBody')
            if body:
                lines += ['Corpo: ' + json.dumps(body['content'], ensure_ascii=False), '']
            lines += ['| Resposta | Significado |', '|---|---|']
            for status, response in operation['responses'].items():
                media = ', '.join(response.get('content', {}))
                lines.append(f"| {status} | {response.get('description', '')} {media} |")
            lines.append('')
    lines.insert(6, f'Total de operações: **{count}**.')
    return '\n'.join(lines)+'\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    content = render()
    if args.check:
        if not target.exists() or target.read_text(encoding='utf-8') != content:
            raise SystemExit('API reference is stale; regenerate scripts/export_api_reference.py')
        print('API reference matches OpenAPI.')
    else:
        target.write_text(content, encoding='utf-8')
        print('API reference exported.')
