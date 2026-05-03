"""
handlers/start.py — Cadastro e solicitação de acesso pelo usuário.

Fluxo:
  1. Usuário envia /start
  2. Bot registra no banco (se ainda não existe)
  3. Bot notifica o ADMIN sobre o novo pedido de acesso
  4. Usuário recebe mensagem dizendo que aguarda aprovação

O admin então usa /aprovar <user_id> ou /reprovar <user_id>.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.storage import StorageService
from handlers._security import get_admin_id

logger = logging.getLogger(__name__)
storage = StorageService()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    nome = user.full_name or ""
    admin_id = get_admin_id(context)

    # Já aprovado → mostra ajuda direto
    if storage.usuario_aprovado(user_id):
        from handlers.help import MENSAGEM_AJUDA
        await update.message.reply_text(MENSAGEM_AJUDA, parse_mode="Markdown")
        return

    # Registra se for novo
    novo = storage.registrar_usuario(user_id, username, nome)

    if novo:
        # Avisa o usuário
        await update.message.reply_text(
            f"👋 Olá, {nome}!\n\n"
            "Sua solicitação de acesso foi enviada ao administrador.\n"
            "Você receberá uma mensagem assim que for aprovado. ✅"
        )
        # Notifica o admin
        username_fmt = f"@{username}" if username else "sem username"
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    "🔔 *Nova solicitação de acesso*\n\n"
                    f"👤 Nome: {nome}\n"
                    f"🔗 Username: {username_fmt}\n"
                    f"🆔 ID: `{user_id}`\n\n"
                    f"Para aprovar: `/aprovar {user_id}`\n"
                    f"Para reprovar: `/reprovar {user_id}`"
                ),
                parse_mode="Markdown",
            )
            logger.info("Admin notificado sobre novo usuário user_id=%s", user_id)
        except Exception:
            logger.exception("Falha ao notificar admin sobre user_id=%s", user_id)
    else:
        # Já existe mas ainda não aprovado
        await update.message.reply_text(
            "⏳ Sua solicitação já foi enviada.\n"
            "Aguarde a aprovação do administrador."
        )
