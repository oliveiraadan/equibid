# EquiBid Notifications — Fluxo de Confirmação (WhatsApp)

Este pacote sobe um **worker** e um **webhook** para o fluxo:
1) Worker pega notificações `pending` (WhatsApp, `new_search_result`) e envia **pergunta de confirmação**.
2) Usuário clica **SIM** ou **NÃO** (ou responde 1/2).
3) Webhook registra a resposta e:
   - SIM: envia os **detalhes do lote**;
   - NÃO: agradece e envia **link para editar a busca**.

## Rodar
```bash
cp .env.example .env
# edite .env com credenciais
docker compose up -d --build
docker compose logs -f worker
docker compose logs -f webhook
```

## SQL extra recomendado
Veja `sql/notifications_extras.sql` para colunas/índices de provider/webhook/backoff.
