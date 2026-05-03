"""
handlers/_security.py — Controle de acesso e sanitização de entradas.

NOVO MODELO DE ACESSO:
  - Qualquer pessoa pode dar /start e solicitar acesso
  - O admin recebe uma notificação e aprova/reprova via comando
  - Sem aprovação, o bot não responde a comandos financeiros
  - Não é mais necessário editar variáveis de ambiente para cada novo usuário
"""

import logging
import re
from telegram import Update
from telegram.ext import ContextTypes
from services.storage import StorageService

logger = logging.getLogger(__name__)
storage = StorageService()

MAX_CATEGORIA_LEN = 50
MAX_VALOR = 1_000_000.0
CATEGORIA_PATTERN = re.compile(r"^[\w\-]{1,50}$", re.UNICODE)


def get_admin_id(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Retorna o ID do administrador armazenado no bot_data."""
    return context.bot_data["admin_id"]


async def verificar_acesso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Verifica se o usuário está aprovado para usar o bot.

    Fluxo:
      1. Se não existe no banco → pede para usar /start primeiro
      2. Se existe mas não aprovado → informa que está aguardando aprovação
      3. Se aprovado → libera
    """
    user_id = update.effective_user.id

    if not storage.usuario_existe(user_id):
        await update.message.reply_text(
            "👋 Você ainda não solicitou acesso.\n"
            "Envie /start para solicitar."
        )
        return False

    if not storage.usuario_aprovado(user_id):
        await update.message.reply_text(
            "⏳ Seu acesso ainda não foi aprovado.\n"
            "Aguarde a aprovação do administrador."
        )
        return False

    return True


def sanitizar_categoria(categoria: str) -> str | None:
    categoria = categoria.strip()
    if len(categoria) > MAX_CATEGORIA_LEN:
        return None
    if not CATEGORIA_PATTERN.match(categoria):
        return None
    return categoria.lower()


def validar_valor(valor_str: str) -> float | None:
    valor_str = valor_str.strip().replace(",", ".")
    try:
        valor = float(valor_str)
    except ValueError:
        return None
    if valor <= 0 or valor > MAX_VALOR:
        return None
    return round(valor, 2)
