"""
handlers/resumo.py — Resumo financeiro mensal do usuário.
Uso: /resumo [AAAA-MM]
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from handlers._security import verificar_acesso
from services.report import ReportService

logger = logging.getLogger(__name__)
report = ReportService()


async def exibir_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await verificar_acesso(update, context):
        return

    user_id = update.effective_user.id

    if context.args:
        try:
            datetime.strptime(context.args[0], "%Y-%m")
            periodo = context.args[0]
        except ValueError:
            await update.message.reply_text("⚠️ Formato inválido. Use AAAA-MM. Ex: /resumo 2024-03")
            return
    else:
        periodo = datetime.now().strftime("%Y-%m")

    try:
        dados = report.resumo_mensal(user_id, periodo)
    except Exception:
        logger.exception("Erro ao gerar resumo — user_id=%s", user_id)
        await update.message.reply_text("❌ Erro ao gerar resumo. Tente novamente.")
        return

    if dados["total_gastos"] == 0 and dados["total_receitas"] == 0:
        await update.message.reply_text(
            f"📭 Nenhum registro encontrado para *{periodo}*.",
            parse_mode="Markdown",
        )
        return

    saldo_emoji = "✅" if dados["saldo"] >= 0 else "🔴"
    linhas = [
        f"📊 *Resumo — {periodo}*\n",
        f"💸 Gastos:   R$ {dados['total_gastos']:>10,.2f}",
        f"💰 Receitas: R$ {dados['total_receitas']:>10,.2f}",
        f"{saldo_emoji} Saldo:    R$ {dados['saldo']:>10,.2f}",
    ]
    if dados["por_categoria"]:
        linhas += ["", "📂 *Gastos por categoria:*"]
        for cat, val in sorted(dados["por_categoria"].items(), key=lambda x: -x[1]):
            linhas.append(f"  • {cat}: R$ {val:,.2f}")

    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")
