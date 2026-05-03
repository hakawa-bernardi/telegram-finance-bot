"""
handlers/deletar.py — Deleta lançamentos do usuário autenticado.
Uso:
  /deletar           → lista os últimos 10 lançamentos
  /deletar <id>      → deleta o lançamento com aquele ID
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers._security import verificar_acesso
from services.storage import StorageService

logger = logging.getLogger(__name__)
storage = StorageService()
LIMITE = 10


def _listar(df) -> str:
    recentes = df.tail(LIMITE).iloc[::-1]
    linhas = ["🗒️ *Últimos lançamentos:*\n"]
    for _, row in recentes.iterrows():
        emoji = "💸" if row["tipo"] == "gasto" else "💰"
        data = row["data"].strftime("%d/%m %H:%M")
        linhas.append(
            f"`#{int(row['id'])}` {emoji} R$ {row['valor']:,.2f} "
            f"— {row['categoria']} _{data}_"
        )
    linhas += ["", "Para deletar: `/deletar <número>`"]
    return "\n".join(linhas)


async def deletar_registro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await verificar_acesso(update, context):
        return

    user_id = update.effective_user.id
    df = storage.carregar_dados(user_id)

    if not context.args:
        if df.empty:
            await update.message.reply_text("📭 Nenhum lançamento encontrado.")
            return
        await update.message.reply_text(_listar(df), parse_mode="Markdown")
        return

    try:
        registro_id = int(context.args[0].strip().lstrip("#"))
    except ValueError:
        await update.message.reply_text("⚠️ ID inválido. Use /deletar para ver a lista.")
        return

    try:
        removido = storage.deletar_registro(user_id, registro_id)
    except Exception:
        logger.exception("Erro ao deletar — user_id=%s", user_id)
        await update.message.reply_text("❌ Erro interno. Tente novamente.")
        return

    if removido is None:
        await update.message.reply_text("⚠️ Lançamento não encontrado. Use /deletar para ver a lista.")
        return

    emoji = "💸" if removido["tipo"] == "gasto" else "💰"
    await update.message.reply_text(
        f"🗑️ *Lançamento deletado!*\n\n"
        f"{emoji} Tipo: {removido['tipo']}\n"
        f"💲 Valor: R$ {float(removido['valor']):,.2f}\n"
        f"🏷️ Categoria: {removido['categoria']}",
        parse_mode="Markdown",
    )
