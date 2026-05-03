"""
handlers/editar.py — Edita lançamentos do usuário autenticado.
Uso:
  /editar                          → lista os últimos 10 lançamentos
  /editar <id> valor <novo>        → altera o valor
  /editar <id> categoria <nova>    → altera a categoria
  /editar <id> tipo <gasto|receita>→ altera o tipo
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers._security import verificar_acesso, sanitizar_categoria, validar_valor
from services.storage import StorageService

logger = logging.getLogger(__name__)
storage = StorageService()
LIMITE = 10


def _listar(df) -> str:
    recentes = df.tail(LIMITE).iloc[::-1]
    linhas = ["✏️ *Selecione o lançamento para editar:*\n"]
    for _, row in recentes.iterrows():
        emoji = "💸" if row["tipo"] == "gasto" else "💰"
        data = row["data"].strftime("%d/%m %H:%M")
        linhas.append(
            f"`#{int(row['id'])}` {emoji} R$ {row['valor']:,.2f} "
            f"— {row['categoria']} _{data}_"
        )
    linhas += [
        "",
        "*Campos:* `valor`, `categoria`, `tipo`",
        "Exemplos:",
        "`/editar 3 valor 49.90`",
        "`/editar 3 categoria conta-luz`",
        "`/editar 3 tipo receita`",
    ]
    return "\n".join(linhas)


async def editar_registro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    if len(context.args) < 3:
        await update.message.reply_text(
            "⚠️ Formato: `/editar <id> <campo> <valor>`\n"
            "Use /editar para ver a lista.",
            parse_mode="Markdown",
        )
        return

    try:
        registro_id = int(context.args[0].strip().lstrip("#"))
    except ValueError:
        await update.message.reply_text("⚠️ ID inválido.")
        return

    campo = context.args[1].strip().lower()
    novo_str = context.args[2].strip()

    if campo not in ("valor", "categoria", "tipo"):
        await update.message.reply_text(
            "⚠️ Campo inválido. Use `valor`, `categoria` ou `tipo`.",
            parse_mode="Markdown",
        )
        return

    # Valida o novo valor conforme o campo
    if campo == "valor":
        novo = validar_valor(novo_str)
        if novo is None:
            await update.message.reply_text("⚠️ Valor inválido. Ex: 49.90")
            return
    elif campo == "categoria":
        novo = sanitizar_categoria(novo_str)
        if novo is None:
            await update.message.reply_text("⚠️ Categoria inválida. Use letras, números, hífen ou underscore.")
            return
    elif campo == "tipo":
        novo = novo_str.lower()
        if novo not in ("gasto", "receita"):
            await update.message.reply_text("⚠️ Tipo inválido. Use `gasto` ou `receita`.", parse_mode="Markdown")
            return

    # Busca valor anterior para mostrar no resumo
    linha_anterior = df[df["id"] == registro_id]
    valor_anterior = linha_anterior.iloc[0][campo] if not linha_anterior.empty else "?"

    try:
        atualizado = storage.editar_registro(user_id, registro_id, campo, novo)
    except Exception:
        logger.exception("Erro ao editar — user_id=%s", user_id)
        await update.message.reply_text("❌ Erro interno. Tente novamente.")
        return

    if atualizado is None:
        await update.message.reply_text("⚠️ Lançamento não encontrado. Use /editar para ver a lista.")
        return

    emoji = "💸" if atualizado["tipo"] == "gasto" else "💰"
    antes = f"R$ {float(valor_anterior):,.2f}" if campo == "valor" else str(valor_anterior)
    depois = f"R$ {float(novo):,.2f}" if campo == "valor" else str(novo)

    await update.message.reply_text(
        f"✅ *Lançamento #{registro_id} atualizado!*\n\n"
        f"{emoji} Tipo: {atualizado['tipo']}\n"
        f"💲 Valor: R$ {float(atualizado['valor']):,.2f}\n"
        f"🏷️ Categoria: {atualizado['categoria']}\n\n"
        f"📝 *Alteração em* `{campo}`:\n"
        f"   Antes:  `{antes}`\n"
        f"   Depois: `{depois}`",
        parse_mode="Markdown",
    )
