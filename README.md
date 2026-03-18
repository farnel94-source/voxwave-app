# VoxWave — Dictee Vocale Intelligente

> Parle → Transcrit → Nettoie → Colle le texte propre

## Comment ça marche

1. Appuie sur **F8** → commence à parler 🔴
2. Appuie sur **F8** → arrête, transcrit, nettoie ✨
3. Le texte propre est collé dans ton app active ✅

## Installation

```bash
# Cloner le projet
git clone <repo> && cd voxwave

# Installer les dépendances
pip install -r requirements.txt

# (Optionnel) Installer Ollama pour le nettoyage IA
# https://ollama.ai
ollama pull gemma3:4b
```

## Utilisation

```bash
# Lancer l'app
python -m voxwave

# Avec un modèle Whisper spécifique
python -m voxwave --model small

# Tester le micro
python -m voxwave --test
```

## Configuration

Éditer `config.yaml` :

```yaml
hotkey: F8          # Touche pour dicter
language: fr        # Langue
model: base         # tiny/base/small/medium/large-v3
cleaning: quality   # fast (regex) ou quality (regex + IA)
injection: paste    # paste ou type
```

## Stack

- **faster-whisper** : transcription vocale locale
- **sounddevice** : capture microphone
- **pynput** : hotkeys + injection clavier
- **Ollama** : nettoyage IA local (optionnel)

## Développement

```bash
# Tests
pytest tests/ -v

# Formatage
black src/ tests/

# Coverage
pytest tests/ --cov=src --cov-report=html
```

## Licence

MIT
