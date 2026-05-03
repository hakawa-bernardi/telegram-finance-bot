"""handlers/help.py — Exibe os comandos disponíveis."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers._security import verificar_acesso

logger = logging.getLogger(__name__)

MENSAGEM_AJUDA = """
🤖 *Bot de Controle Financeiro*

━━━━━━━━━━━━━━━━━━━━━━
💸 *Registrar Gasto*
`/gasto <valor> <categoria>`
Ex: `/gasto 59.90 mercado`

💰 *Registrar Receita*
`/receita <valor> <categoria>`
Ex: `/receita 3000 salario`

📊 *Resumo Mensal*
`/resumo` — mês atual
`/resumo 2024-03` — mês específico

📥 *Planilha Excel*
`/planilha` — mês atual
`/planilha 2024-03` — mês específico

🗑️ *Deletar Lançamento*
`/deletar` — lista os seus lançamentos
`/deletar 3` — deleta o lançamento #3

✏️ *Editar Lançamento*
`/editar` — lista os seus lançamentos
`/editar 3 valor 49.90`
`/editar 3 categoria conta-luz`
`/editar 3 tipo receita`

━━━━━━━━━━━━━━━━━━━━━━
📌 Categoria: letras, números, hífen, underscore
📌 Valor: use ponto ou vírgula decimal
""".strip()


async def exibir_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await verificar_acesso(update, context):
        return
    await update.message.reply_text(MENSAGEM_AJUDA, parse_mode="Markdown")
