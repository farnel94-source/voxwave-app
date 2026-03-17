# Plan : Streaming par chunks pendant l'enregistrement

**Date** : 2026-03-17
**Statut** : A planifier (futur ticket)
**Priorité** : Haute (supprime la limite de durée d'enregistrement)

## Problème actuel

L'audio est enregistré en entier, puis envoyé d'un bloc à Groq/Whisper.
Conséquences :
- Limite de durée (actuellement 300s / 5 min)
- Latence proportionnelle à la durée de l'enregistrement
- Risque de timeout Groq sur les longs enregistrements (>25 Mo)

## Architecture cible

### Principe
Détecter les silences **pendant** l'enregistrement, envoyer chaque chunk à Groq en parallèle, injecter le texte progressivement (sous-titres temps réel).

### Pipeline

```
Hotkey (start)
  → Capture audio en continu
  → VAD détecte les silences (>500ms)
  → Découpe en chunks (~5-15s chacun)
  → Envoi parallèle à Groq (chunk N transcrit pendant chunk N+1 enregistré)
  → Injection progressive du texte (chunk par chunk)
Hotkey (stop)
  → Dernier chunk envoyé
  → Nettoyage LLM sur le texte complet (ou par chunk)
  → Remplacement final
```

### Bénéfices
- **Plus aucune limite de durée** — l'enregistrement peut durer indéfiniment
- **Latence constante ~2s** — indépendante de la durée totale
- **Meilleure UX** — l'utilisateur voit le texte apparaître en temps réel

### Fichiers impactés
- `src/audio/capture.py` — détection de silences en temps réel pendant la capture
- `src/audio/processor.py` — découpage en chunks au lieu de traitement monolithique
- `src/transcription/groq_engine.py` — envoi parallèle de chunks (asyncio ou ThreadPool)
- `src/app.py` — orchestration du pipeline streaming
- `src/injection/progressive_injector.py` — injection chunk par chunk

### Défis techniques
1. **Contexte inter-chunks** : Whisper fonctionne mieux avec du contexte. Options :
   - `initial_prompt` avec les derniers mots du chunk précédent
   - Overlap de 500ms entre chunks
2. **Ordre d'injection** : Les chunks peuvent revenir dans le désordre → file d'attente ordonnée
3. **Nettoyage LLM** : Nettoyer chunk par chunk (rapide mais moins cohérent) ou attendre la fin (cohérent mais plus lent)
4. **Gestion d'erreurs** : Si un chunk échoue côté Groq → fallback Whisper local pour ce chunk uniquement
5. **Thread safety** : Plusieurs transcriptions en parallèle + injection séquentielle → synchronisation

### Approche recommandée
1. Phase 1 : Découpage post-enregistrement (chunks envoyés en parallèle après stop) — plus simple
2. Phase 2 : Streaming temps réel (chunks envoyés pendant l'enregistrement) — UX optimale
