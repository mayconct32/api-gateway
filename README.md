# Payment E-commerce API

E-commerce em **FastAPI + SQLAlchemy** com pedidos e pagamentos via **Stripe Checkout** e **Razorpay Payment Link**, autenticação JWT e valores sempre calculados no servidor.

## Funcionalidades

- **Usuários**: cadastro, login (OAuth2 password + JWT Bearer), consulta/atualização do próprio perfil, listagem exclusiva de ADMIN. Senhas com hash bcrypt.
- **Produtos**: CRUD administrativo (criar/atualizar/desativar), listagem pública com paginação (`X-Total-Count`), preço em reais convertido para centavos no servidor.
- **Pedidos**: criados apenas com `product_id` + `quantity`; nomes, preços unitários e total são resolvidos no banco (`OrderItem` congela o preço da compra). Consulta restrita ao dono (ou ADMIN).
- **Pagamentos**: link por (pedido, provedor) com idempotência — pedir novamente reutiliza o link pendente em vez de gerar cobrança nova. Verificação sempre contra o gateway (consulta direta ou webhook assinado), com comparação de valor e moeda BRL. Estados: pedido `PENDING → CONFIRMED`, pagamento `PENDING → PAID`.
- **Webhooks**: `POST /api/v1/payments/webhooks/{stripe|razorpay}` verificam assinatura (HMAC) antes de processar; eventos repetidos são ignorados.

## Como executar

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings stripe razorpay pyjwt bcrypt email-validator python-multipart

cp .env.example .env   # preencha com suas credenciais reais (não comitar .env)
uvicorn main:app --reload
```

Documentação interativa: `http://localhost:8000/docs`.

## Variáveis de ambiente

| Variável | Descrição |
| --- | --- |
| `SECRET_KEY` | Chave JWT (gere com `openssl rand -hex 32`) |
| `DATABASE_URL` | Padrão `sqlite:///./dev.db`; compatível com PostgreSQL/MySQL via SQLAlchemy |
| `BASE_URL` | URL pública base, usada nas URLs de retorno dos gateways |
| `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET` | Credenciais Stripe (opcionais: só habilita se presente) |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | Credenciais Razorpay |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token (padrão 30) |

Atenção: sem `SECRET_KEY` forte em produção os tokens são forjáveis.

## Banco de dados

SQLite por padrão; o schema é criado idempotentemente na inicialização (`Base.metadata.create_all`). Para evolução de schema em produção, adote migrações versionadas (ex.: Alembic).

## Testes

```bash
pip install pytest
python -m pytest -q
```

A suíte usa SQLite em memória e provedores de pagamento fake (injeção via dependency overrides) — nenhuma chamada real de gateway.
