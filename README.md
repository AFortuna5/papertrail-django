# PaperTrail

**API para organizar artigos e revisar a escrita de resumos científicos, construída com Python, Django e Django REST Framework.**

Projeto de portfólio de Arthur, com escopo pequeno e funcional: autenticação, CRUD com isolamento por usuário, análise textual determinística e histórico persistido. A interface inicial usa Django Templates; a API navegável do DRF permite experimentar os endpoints sem um frontend separado.

Não é um produto da Alenna nem uma aplicação em produção. O objetivo é demonstrar fundamentos de backend com código que possa ser executado, testado e explicado.

## Funcionalidades

- Login por token ou sessão, logout e limitação de tentativas no endpoint de token.
- Cadastro, consulta, edição e exclusão de artigos em português ou inglês.
- Cada usuário vê e altera apenas os próprios artigos, inclusive nas ações de revisão.
- Busca por título/resumo, ordenação e paginação.
- Revisão de resumos: contagem de palavras e frases, palavras consecutivas repetidas, frases longas e resumos curtos.
- Histórico de revisões: conteúdo igual reutiliza a análise; conteúdo alterado gera outra.
- Django Admin para administração por usuários com privilégios.
- SQLite para execução imediata e configuração opcional de PostgreSQL.
- Migrations versionadas, testes e workflow de CI para os dois bancos.

**Limite funcional:** a análise é heurística, síncrona e local. Não há IA, tradução, avaliação científica, Celery, pagamento ou multi-tenancy por organização. Idioma é um metadado; as mesmas regras são aplicadas a ambos os idiomas. O isolamento existente é por usuário.

## Executar no Windows / PyCharm

Requer Python 3.12 ou superior. No terminal, dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
```

Se o comando `python` não estiver disponível, use `py -3` ou instale Python. Com `uv`, pode usar `uv venv --python 3.12` e `uv pip install -r requirements.lock`.

O comando `seed_demo` pede uma senha, cria o usuário **demo** sem privilégios administrativos e dois artigos fictícios. Pode ser executado novamente sem duplicar os exemplos nem trocar a senha. Para acessar o Admin, execute `python manage.py createsuperuser`.

- Página inicial: http://127.0.0.1:8000/
- Login no navegador: http://127.0.0.1:8000/api-auth/login/?next=/api/papers/
- API: http://127.0.0.1:8000/api/papers/
- Administração: http://127.0.0.1:8000/admin/

No PyCharm, selecione `.venv/Scripts/python.exe` como interpretador e execute `manage.py` com o parâmetro `runserver`. No Linux/macOS, substitua `.venv\Scripts\python.exe` por `.venv/bin/python` e `Copy-Item` por `cp`.

## Demonstração em cinco minutos

1. Execute migrations e `seed_demo`; abra a página inicial e faça login.
2. Abra `/api/papers/` e cadastre um artigo pelo formulário HTML do DRF.
3. Acesse `/api/papers/1/review/` (substitua `1` pelo ID retornado) e envie um POST vazio pelo formulário. É normal que abrir essa URL com GET retorne 405: a análise exige POST.
4. Envie novamente: a primeira resposta é `201`, a segunda é `200` com o mesmo ID de revisão.
5. Altere o resumo via PATCH; revise novamente e consulte `/api/papers/1/reviews/` para ver o histórico.
6. Execute os testes: eles demonstram que um segundo usuário não consegue ler, alterar, excluir ou revisar artigos do primeiro.

## Contrato da API

Todos os endpoints de artigos exigem sessão autenticada ou o cabeçalho `Authorization: Token <token>`. Requisições via sessão exigem CSRF em operações de escrita; a interface do DRF cuida disso.

| Método | Endpoint | Comportamento |
| --- | --- | --- |
| POST | `/api/auth/token/` | Recebe username/password e retorna token |
| POST | `/api/auth/logout/` | Revoga token e encerra a sessão atual |
| GET, POST | `/api/papers/` | Lista ou cria artigos |
| GET, PUT, PATCH, DELETE | `/api/papers/{id}/` | Consulta, altera ou exclui |
| POST | `/api/papers/{id}/review/` | Cria/reutiliza análise |
| GET | `/api/papers/{id}/reviews/` | Histórico paginado |

Exemplo de corpo para criar artigo:

```json
{
  "title": "Clareza na comunicação científica",
  "abstract": "Este estudo analisa a a comunicação científica e apresenta métodos para melhorar a clareza dos resultados.",
  "language": "pt"
}
```

O campo `owner` não é editável: o servidor determina o proprietário pela autenticação. Título: até 200 caracteres; resumo: ao menos 5 palavras e até 20.000 caracteres; idiomas: `pt` e `en`.

Exemplo de uso em PowerShell (com o servidor ativo):

```powershell
$credential = Get-Credential -UserName demo -Message 'Senha escolhida no seed_demo'
$body = @{ username = $credential.UserName; password = $credential.GetNetworkCredential().Password } | ConvertTo-Json
$auth = Invoke-RestMethod http://127.0.0.1:8000/api/auth/token/ -Method Post -ContentType 'application/json' -Body $body
$headers = @{ Authorization = "Token $($auth.token)" }
$papers = Invoke-RestMethod http://127.0.0.1:8000/api/papers/ -Headers $headers
$id = $papers.results[0].id
Invoke-RestMethod "http://127.0.0.1:8000/api/papers/$id/review/" -Method Post -Headers $headers
Invoke-RestMethod "http://127.0.0.1:8000/api/papers/$id/reviews/" -Headers $headers
Invoke-RestMethod http://127.0.0.1:8000/api/auth/logout/ -Method Post -Headers $headers
```

Busca: `/api/papers/?search=comunicação&ordering=title&page=1`. Listas retornam `count`, `next`, `previous` e `results`, com 10 registros por página. Erros comuns: `400` para dados inválidos, `401` sem autenticação, `404` para artigo inexistente ou de outro usuário e `429` após exceder o limite do login por token.

## Arquitetura e decisões

```text
config/                 configurações, rotas e WSGI
papers/models.py        Paper e Review, índice e constraint
papers/serializers.py   contrato e validação de entrada
papers/views.py         autenticação, CRUD e ações REST
papers/services.py      regras de análise e deduplicação
papers/migrations/      evolução versionada do banco
papers/tests/           testes de API, regras e persistência
templates/home.html     apresentação com Django Templates
```

`User → Paper → Review`: um usuário possui vários artigos; cada artigo possui várias revisões. A exclusão de um artigo remove suas revisões por cascade. Uma revisão guarda métricas, achados e hash do idioma/conteúdo/versão das regras; não armazena uma cópia recuperável do texto antigo.

- **Isolamento no queryset:** protege listagem e todas as operações por ID, retornando 404 para objetos de terceiros. O Admin é uma interface privilegiada separada.
- **Serviço separado:** a regra textual pode ser testada sem uma requisição HTTP e posteriormente movida para uma tarefa assíncrona.
- **Idempotência no banco:** `UniqueConstraint(paper, source_hash)` e `get_or_create` evitam duplicar a revisão da mesma versão. O hash não é uma garantia de anonimização.
- **Execução síncrona:** adequada a resumos limitados a 20.000 caracteres; uma integração lenta com IA exigiria fila, estados de processamento e política de retry.
- **Autenticação padrão do DRF:** mantém o exemplo simples. Tokens não expiram automaticamente; o logout os revoga. Produção exigiria HTTPS e política de expiração/rotação.

## Qualidade

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m coverage run manage.py test
.\.venv\Scripts\python.exe -m coverage report
```

Os testes cobrem isolamento entre usuários em cada ação, falsificação de proprietário, validação, CRUD, busca/paginação, login/logout, limitação de tentativas, histórico, deduplicação e regras textuais. A CI exige pelo menos 85% de cobertura do app e verifica SQLite e PostgreSQL. `requirements.lock` fixa as versões instaladas; `requirements.txt` registra os intervalos para atualização deliberada.

## PostgreSQL

Crie um banco e um usuário PostgreSQL com permissão de acesso. Defina `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` e `POSTGRES_PORT` no `.env`, conforme o exemplo, e execute `manage.py migrate`. Sem `POSTGRES_DB`, o projeto usa SQLite. Para rodar testes no PostgreSQL, o usuário de testes precisa poder criar o banco temporário.

## Limites e evolução

Este repositório não comprova experiência em produção. Antes de hospedar: configurar segredo próprio, `DEBUG=false`, hosts, HTTPS, servidor WSGI, arquivos estáticos e backups. O throttle usa cache local e não substitui proteção distribuída contra abuso; o login por sessão/Admin requer proteção adicional em produção. Não há cadastro público: contas são criadas via comando demo ou Admin.

Não envie artigos reais confidenciais para uma demonstração. Uma aplicação comercial exigiria políticas de retenção, exclusão/exportação, autorização por organização, auditoria e análise de requisitos LGPD. Nenhuma conformidade legal é alegada aqui.

Próximas melhorias possíveis: fila Celery/Redis para um provedor real de revisão; contratos OpenAPI; organizações e papéis; testes de carga. São próximos passos, não funcionalidades implementadas.

Referências: [Django 5.2](https://docs.djangoproject.com/en/5.2/), [DRF](https://www.django-rest-framework.org/), [filtragem de querysets](https://www.django-rest-framework.org/api-guide/filtering/).
