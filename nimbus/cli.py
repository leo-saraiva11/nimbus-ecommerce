"""REPL CLI do agente Nimbus."""
from __future__ import annotations
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from nimbus.agent import Agent, AgentConfig
from nimbus.llm.groq_client import GroqClient
from nimbus.rag.chunker import chunk_markdown
from nimbus.rag.embeddings import SentenceTransformerEmbedder
from nimbus.rag.store import VectorStore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CORPUS_DIR = PROJECT_ROOT / "corpus"
PEDIDOS_DIR = PROJECT_ROOT / "pedidos"
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "nimbus" / "prompts" / "system.md"


def _setup_logging() -> None:
    level = logging.INFO if os.environ.get("NIMBUS_DEBUG") else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _build_rag() -> VectorStore:
    print("[setup] carregando embeddings (primeira vez baixa o modelo, ~80MB)...", file=sys.stderr)
    store = VectorStore(embedder=SentenceTransformerEmbedder())
    for md in sorted(CORPUS_DIR.glob("*.md")):
        chunks = chunk_markdown(md.read_text(encoding="utf-8"), source=md.name, overlap=1)
        store.add(chunks)
    print(f"[setup] corpus indexado: {len(list(CORPUS_DIR.glob('*.md')))} arquivos.", file=sys.stderr)
    return store


def main() -> None:
    load_dotenv()
    _setup_logging()

    if not os.environ.get("GROQ_API_KEY"):
        print("ERRO: defina GROQ_API_KEY no .env (veja .env.example).", file=sys.stderr)
        sys.exit(1)

    rag = _build_rag()
    agent = Agent(
        llm=GroqClient(),
        rag=rag,
        config=AgentConfig(),
        data_dir=DATA_DIR,
        pedidos_dir=PEDIDOS_DIR,
        system_prompt_template=SYSTEM_PROMPT_PATH.read_text(encoding="utf-8"),
    )

    print("Loja Nimbus — assistente virtual. Digite 'sair' para encerrar.\n")
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
