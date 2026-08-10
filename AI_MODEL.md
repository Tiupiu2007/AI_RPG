# AI RPG — Modello AI di riferimento

## Modello Ollama obbligatorio

Il progetto AI_RPG usa questa versione precisa di Qwen:

```text
qwen3:30b-a3b-instruct-2507-q4_K_M
```

Model ID:

```text
19e422b02313
```

Dimensione locale indicata da Ollama: **18 GB**.

## Regola importante

NON sostituire, aggiornare, downgradare o scegliere automaticamente un altro modello Qwen/Ollama durante le modifiche al progetto.

In particolare NON usare come sostituti:

- `qwen3:8b`
- altre varianti `qwen3`
- altri modelli Ollama

Se il modello deve essere cambiato intenzionalmente, deve essere richiesto esplicitamente dall'utente.

## Configurazione corrente

```python
MODEL_NAME = "qwen3:30b-a3b-instruct-2507-q4_K_M"
```

Questo file è una nota di progetto e deve essere consultato prima di modificare `app/ai_provider.py` o qualsiasi altra parte che selezioni il modello AI.