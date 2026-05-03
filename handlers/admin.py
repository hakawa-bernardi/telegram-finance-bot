"""
handlers/admin.py — Comandos exclusivos do administrador.

Comandos:
  /aprovar <user_id>   → aprova um usuário pendente
  /reprovar <user_id>  → remove acesso de um usuário
  /pendentes           → lista usuários aguardando aprovação
  /usuarios            → lista todos os usuários aprovados

SEGURANÇA: Todos os comandos verificam se quem executou é o ADMIN_ID.
Qualquer outro usuário recebe "Acesso não autorizado" sem detalhes.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.storage import StorageService
from handlers._security import get_admin_id

logger = logging.getLogger(__name__)
storage = StorageService()


def _eh_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    return update.effective_user.id == get_admin_id(context)


async def cmd_aprovar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Aprova um usuário pelo ID."""
    if not _eh_admin(update, context):
        await update.message.reply_text("🚫 Acesso não autorizado.")
        return

    if not context.args:
        await update.message.reply_text("Uso: `/aprovar <user_id>`", parse_mode="Markdown")
        return

    try:
        alvo_id = int(context.args[0].strip())
    except ValueError:
        await update.message.reply_text("⚠️ ID inválido. Use apenas números.")
        return

    ok = storage.aprovar_usuario(alvo_id)
    if not ok:
        await update.message.reply_text(
            f"⚠️ Usuário `{alvo_id}` não encontrado.\n"
            "Use /pendentes para ver quem aguarda aprovação.",
            parse_mode="Markdown",
        )
        return

    logger.info("Usuário aprovado pelo admin — user_id=%s", alvo_id)

    # Notifica o usuário aprovado
    try:
        await context.bot.send_message(
            chat_id=alvo_id,
            text=(
                "✅ *Seu acesso foi aprovado!*\n\n"
                "Você já pode usar o bot.\n"
                "Envie /help para ver os comandos disponíveis."
            ),
            parse_mode="Markdown",
        )
    except Exception:
        logger.warning("Não foi possível notificar user_id=%s sobre aprovação", alvo_id)

    await update.message.reply_text(f"✅ Usuário `{alvo_id}` aprovado com sucesso!", parse_mode="Markdown")


async def cmd_reprovar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove o acesso de um usuário."""
    if not _eh_admin(update, context):
        await update.message.reply_text("🚫 Acesso não autorizado.")
        return

    if not context.args:
        await update.message.reply_text("Uso: `/reprovar <user_id>`", parse_mode="Markdown")
        return

    try:
        alvo_id = int(context.args[0].strip())
    except ValueError:
        await update.message.reply_text("⚠️ ID inválido. Use apenas números.")
        return

    if alvo_id == get_admin_id(context):
        await update.message.reply_text("⚠️ Você não pode reprovar a si mesmo.")
        return

    ok = storage.reprovar_usuario(alvo_id)
    if not ok:
        await update.message.reply_text(f"⚠️ Usuário `{alvo_id}` não encontrado.", parse_mode="Markdown")
        return

    logger.info("Usuário reprovado pelo admin — user_id=%s", alvo_id)
    await update.message.reply_text(f"🚫 Acesso do usuário `{alvo_id}` removido.", parse_mode="Markdown")


async def cmd_pendentes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista usuários aguardando aprovação."""
    if not _eh_admin(update, context):
        await update.message.reply_text("🚫 Acesso não autorizado.")
        return

    pendentes = storage.listar_usuarios_pendentes()

    if not pendentes:
        await update.message.reply_text("✅ Nenhuma solicitação pendente.")
        return

    linhas = ["⏳ *Usuários aguardando aprovação:*\n"]
    for u in pendentes:
        username = f"@{u['username']}" if u["username"] else "sem username"
        linhas.append(
            f"👤 {u['nome']} ({username})\n"
            f"🆔 `{u['user_id']}`\n"
            f"📅 {u['criado_em'][:10]}\n"
            f"➡️ `/aprovar {u['user_id']}`\n"
        )

    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


async def cmd_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista todos os usuários aprovados."""
    if not _eh_admin(update, context):
        await update.message.reply_text("🚫 Acesso não autorizado.")
        return

    usuarios = storage.listar_usuarios_aprovados()

    if not usuarios:
        await update.message.reply_text("📭 Nenhum usuário aprovado ainda.")
        return

    linhas = [f"👥 *Usuários aprovados ({len(usuarios)}):*\n"]
    for u in usuarios:
        username = f"@{u['username']}" if u["username"] else "sem username"
        linhas.append(f"• {u['nome']} ({username}) — `{u['user_id']}`")

    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")
