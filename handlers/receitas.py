"""
handlers/receitas.py — Registra receitas do usuário autenticado.
Uso: /receita <valor> <categoria>
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers._security import verificar_acesso, sanitizar_categoria, validar_valor
from services.storage import StorageService

logger = logging.getLogger(__name__)
storage = StorageService()


async def registrar_receita(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await verificar_acesso(update, context):
        return

    user_id = update.effective_user.id

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Formato: /receita <valor> <categoria>\n"
            "Exemplo: /receita 3000 salario"
        )
        return

    valor = validar_valor(context.args[0])
    if valor is None:
        await update.message.reply_text(
            "⚠️ Valor inválido. Use um número positivo (ex: 3000.00)."
        )
        return

    categoria = sanitizar_categoria(context.args[1])
    if categoria is None:
        await update.message.reply_text(
            "⚠️ Categoria inválida. Use letras, números, hífen ou underscore (máx. 50 chars)."
        )
        return

    try:
        storage.salvar_registro(user_id=user_id, tipo="receita", valor=valor, categoria=categoria)
        logger.info("Receita registrada — user_id=%s categoria=%s", user_id, categoria)
    except Exception:
        logger.exception("Erro ao salvar receita — user_id=%s", user_id)
        await update.message.reply_text("❌ Erro interno ao salvar. Tente novamente.")
        return

    await update.message.reply_text(
        f"✅ Receita registrada!\n"
        f"💰 Valor: R$ {valor:,.2f}\n"
        f"🏷️ Categoria: {categoria}"
    )
