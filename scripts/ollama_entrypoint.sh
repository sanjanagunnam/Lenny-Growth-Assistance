#!/bin/sh
set -e

echo "[ollama-entrypoint] Starting Ollama daemon in background..."
ollama serve &
OLLAMA_PID=$!

echo "[ollama-entrypoint] Waiting for Ollama service to become responsive..."
until ollama list >/dev/null 2>&1; do
  sleep 1
done

echo "[ollama-entrypoint] Pulling embedding model: nomic-embed-text (768 dimensions)..."
ollama pull nomic-embed-text || echo "[ollama-entrypoint] Warning: Failed to pull nomic-embed-text, will retry on demand."

echo "[ollama-entrypoint] Pulling chat model: llama3.2..."
ollama pull llama3.2 || echo "[ollama-entrypoint] Warning: Failed to pull llama3.2, will retry on demand."

echo "[ollama-entrypoint] Models pulled successfully. Ollama daemon is ready."
wait $OLLAMA_PID
