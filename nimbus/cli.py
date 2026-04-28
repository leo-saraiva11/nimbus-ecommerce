"""REPL CLI do agente Nimbus."""
from __future__ import annotations
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from nimbus.agent import Agent, AgentConfig
from nimbus.llm.base import LLMError
from nimbus.llm.groq_client import GroqClient
from nimbus.llm.openrouter_client import OpenRouterClient
from nimbus.rag.chunker import chunk_markdown
from nimbus.rag.embeddings import SentenceTransformerEmbedder
from nimbus.rag.store import VectorStore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CORPUS_DIR = PROJECT_ROOT / "corpus"
PEDIDOS_DIR = PROJECT_ROOT / "pedidos"
LOGS_DIR = PROJECT_ROOT / "logs"
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "nimbus" / "prompts" / "system.md"


def _setup_logging(verbose: bool, logs_dir: Path = LOGS_DIR) -> Path:
    """Configura console + arquivo. Retorna o caminho do arquivo de log da sessão.

    - Console (stderr): SEMPRE em ``WARNING`` — mantém o terminal limpo.
      Em modo ``--debug`` o trace visual (stdout) já mostra todos os eventos do
      turno; duplicar via logger no stderr só polui.
    - Arquivo ``logs/session_<timestamp>.log``: SEMPRE em ``INFO`` — registra
      todos os eventos de cada turno (USER, TOOL CALL, TOOL OK/ERROR, FINAL)
      com timestamp completo. Para debugging post-mortem, ler o arquivo.
    - Loggers de bibliotecas ruidosas (``httpx``, ``httpcore``,
      ``sentence_transformers``) ficam em ``WARNING`` pra não vazar entradas
      de HTTP/transformers no console nem no arquivo.

    O parâmetro ``verbose`` (vindo de ``--debug`` / ``NIMBUS_DEBUG``) é mantido
    na assinatura por compatibilidade, mas hoje só liga o trace visual via
    ``AgentConfig.debug``; o logger não é mais afetado por ele.
    """
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    formatter_console = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    formatter_file = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter_console)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter_file)

    root = logging.getLogger()
    root.setLevel(logging.INFO)  # handlers filtram individualmente
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    # silencia libs ruidosas (HTTP, transformers) tanto no console quanto no arquivo
    for noisy in ("httpx", "httpcore", "sentence_transformers", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _ = verbose  # mantido na assinatura por compatibilidade — ver docstring
    return log_file


def _build_rag(debug: bool) -> VectorStore:
    print("[setup] carregando embeddings (primeira vez baixa o modelo, ~80MB)...", file=sys.stderr)
    store = VectorStore(embedder=SentenceTransformerEmbedder())
    n = 0
    for md in sorted(CORPUS_DIR.glob("*.md")):
        chunks = chunk_markdown(md.read_text(encoding="utf-8"), source=md.name, overlap=1)
        store.add(chunks)
        n += 1
        if debug:
            print(f"[setup] indexado {md.name}: {len(chunks)} chunks", file=sys.stderr)
    print(f"[setup] corpus indexado: {n} arquivos.", file=sys.stderr)
    return store


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nimbus",
        description="Assistente virtual da Loja Nimbus — agente conversacional CLI.",
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help=(
            "Imprime trace completo de cada turno: chamada à tool de busca em "
            "políticas (RAG), requisição/resposta do LLM (com tool_calls), "
            "execução de cada tool (args, resultado completo, duração), tokens "
            "consumidos por iteração + acumulado, e resposta final."
        ),
    )
    parser.add_argument(
        "--provider",
        choices=["groq", "openrouter"],
        default=None,
        help="Provider de LLM (padrão: groq, ou NIMBUS_PROVIDER do .env).",
    )
    return parser.parse_args(argv)


def _build_llm(provider: str):
    if provider == "groq":
        if not os.environ.get("GROQ_API_KEY"):
            raise LLMError("GROQ_API_KEY não definida no .env (veja .env.example).")
        return GroqClient()
    if provider == "openrouter":
        if not os.environ.get("OPENROUTER_API_KEY"):
            raise LLMError("OPENROUTER_API_KEY não definida no .env (veja .env.example).")
        return OpenRouterClient()
    raise LLMError(f"Provider desconhecido: {provider!r} (use 'groq' ou 'openrouter')")


def main() -> None:
    args = _parse_args()
    load_dotenv()
    debug = args.debug or bool(os.environ.get("NIMBUS_DEBUG"))
    log_file = _setup_logging(verbose=debug)
    print(f"[setup] log da sessão: {log_file}", file=sys.stderr)

    provider = args.provider or os.environ.get("NIMBUS_PROVIDER", "groq")
    try:
        llm = _build_llm(provider)
    except LLMError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)

    rag = _build_rag(debug=debug)
    agent = Agent(
        llm=llm,
        rag=rag,
        config=AgentConfig(debug=debug),
        data_dir=DATA_DIR,
        pedidos_dir=PEDIDOS_DIR,
        system_prompt_template=SYSTEM_PROMPT_PATH.read_text(encoding="utf-8"),
    )

    banner = f"Loja Nimbus — assistente virtual (provider: {provider}). Digite 'sair' para encerrar."
    if debug:
        banner += "  [modo DEBUG ligado: trace completo após cada pergunta]"
    print(banner + "\n")

    while True:
        try:
            user = input("você> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo!")
            break
        if not user:
            continue
        if user.lower() in {"sair", "exit", "quit"}:
            print("Até logo!")
            break
        resposta = agent.run_turn(user)
        print(f"\nNimbus> {resposta}\n")


if __name__ == "__main__":
    main()
