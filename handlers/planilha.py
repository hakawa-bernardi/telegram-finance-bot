"""
handlers/planilha.py — Gera e envia planilha Excel do usuário.
Uso: /planilha [AAAA-MM]
"""

import logging
import os
import tempfile
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from handlers._security import verificar_acesso
from services.report import ReportService

logger = logging.getLogger(__name__)
report = ReportService()


async def enviar_planilha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await verificar_acesso(update, context):
        return

    user_id = update.effective_user.id

    if context.args:
        try:
            datetime.strptime(context.args[0], "%Y-%m")
            periodo = context.args[0]
        except ValueError:
            await update.message.reply_text("⚠️ Formato inválido. Use AAAA-MM. Ex: /planilha 2024-03")
            return
    else:
        periodo = datetime.now().strftime("%Y-%m")

    await update.message.reply_text(f"⏳ Gerando planilha para *{periodo}*…", parse_mode="Markdown")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        sucesso = report.exportar_xlsx(user_id=user_id, periodo=periodo, caminho=tmp_path)

        if not sucesso:
            await update.message.reply_text(
                f"📭 Nenhum registro encontrado para *{periodo}*.", parse_mode="Markdown"
            )
            return

        with open(tmp_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"financeiro_{periodo}.xlsx",
                caption=f"📊 Planilha — {periodo}",
            )
        logger.info("Planilha enviada — user_id=%s periodo=%s", user_id, periodo)

    except Exception:
        logger.exception("Erro ao gerar planilha — user_id=%s", user_id)
        await update.message.reply_text("❌ Erro ao gerar planilha. Tente novamente.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
