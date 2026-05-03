"""
main.py — Inicialização do Bot de Controle Financeiro.

Variáveis de ambiente necessárias (.env):
  TELEGRAM_TOKEN    — Token do BotFather
  TELEGRAM_ADMIN_ID — Seu user_id do Telegram

Novos usuários usam /start para solicitar acesso.
O admin aprova/reprova via /aprovar e /reprovar.
"""

import logging
import os

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler

from handlers.start import cmd_start
from handlers.help import exibir_ajuda
from handlers.gastos import registrar_gasto
from handlers.receitas import registrar_receita
from handlers.resumo import exibir_resumo
from handlers.planilha import enviar_planilha
from handlers.deletar import deletar_registro
from handlers.editar import editar_registro
from handlers.admin import cmd_aprovar, cmd_reprovar, cmd_pendentes, cmd_usuarios

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    if not token:
        logger.critical("TELEGRAM_TOKEN não definido. Encerrando.")
        raise SystemExit(1)

    admin_id_str = os.environ.get("TELEGRAM_ADMIN_ID", "").strip()
    if not admin_id_str:
        logger.critical("TELEGRAM_ADMIN_ID não definido. Encerrando.")
        raise SystemExit(1)

    try:
        admin_id = int(admin_id_str)
    except ValueError:
        logger.critical("TELEGRAM_ADMIN_ID inválido: %s", admin_id_str)
        raise SystemExit(1)

    logger.info("Bot iniciando… Admin ID: %s", admin_id)

    app = Application.builder().token(token).build()

    # Armazena o admin_id para uso nos handlers
    app.bot_data["admin_id"] = admin_id

    # Comandos públicos (qualquer um pode usar para solicitar acesso)
    app.add_handler(CommandHandler("start", cmd_start))

    # Comandos financeiros (exigem aprovação)
    app.add_handler(CommandHandler("help", exibir_ajuda))
    app.add_handler(CommandHandler("gasto", registrar_gasto))
    app.add_handler(CommandHandler("receita", registrar_receita))
    app.add_handler(CommandHandler("resumo", exibir_resumo))
    app.add_handler(CommandHandler("planilha", enviar_planilha))
    app.add_handler(CommandHandler("deletar", deletar_registro))
    app.add_handler(CommandHandler("editar", editar_registro))

    # Comandos exclusivos do admin
    app.add_handler(CommandHandler("aprovar", cmd_aprovar))
    app.add_handler(CommandHandler("reprovar", cmd_reprovar))
    app.add_handler(CommandHandler("pendentes", cmd_pendentes))
    app.add_handler(CommandHandler("usuarios", cmd_usuarios))

    logger.info("Bot pronto. Aguardando comandos…")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
