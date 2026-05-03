"""
handlers/gastos.py — Registra gastos do usuário autenticado.
Uso: /gasto <valor> <categoria>
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers._security import verificar_acesso, sanitizar_categoria, validar_valor
from services.storage import StorageService

logger = logging.getLogger(__name__)
storage = StorageService()


async def registrar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await verificar_acesso(update, context):
        return

    user_id = update.effective_user.id

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Formato: /gasto <valor> <categoria>\n"
            "Exemplo: /gasto 59.90 mercado"
        )
        return

    valor = validar_valor(context.args[0])
    if valor is None:
        await update.message.reply_text(
            "⚠️ Valor inválido. Use um número positivo (ex: 59.90)."
        )
        return

    categoria = sanitizar_categoria(context.args[1])
    if categoria is None:
        await update.message.reply_text(
            "⚠️ Categoria inválida. Use letras, números, hífen ou underscore (máx. 50 chars)."
        )
        return

    try:
        storage.salvar_registro(user_id=user_id, tipo="gasto", valor=valor, categoria=categoria)
        logger.info("Gasto registrado — user_id=%s categoria=%s", user_id, categoria)
    except Exception:
        logger.exception("Erro ao salvar gasto — user_id=%s", user_id)
        await update.message.reply_text("❌ Erro interno ao salvar. Tente novamente.")
        return

    await update.message.reply_text(
        f"✅ Gasto registrado!\n"
        f"💸 Valor: R$ {valor:,.2f}\n"
        f"🏷️ Categoria: {categoria}"
    )
