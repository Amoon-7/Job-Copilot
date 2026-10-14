# Décisions d'architecture

1. **Humain dans la boucle, pas d'auto-envoi.** Limite les risques (hallucinations, CGU) et produit
   un signal d'amélioration (approbations / rejets / éditions) exploitable plus tard.
2. **Ancrage vérifiable.** Le CV est découpé en passages numérotés (`E1…En`). Le vérificateur doit
   citer des passages valides pour chaque affirmation ; un garde-fou déterministe rejette les
   nombres absents du CV et de l'offre.
3. **Juge indépendant en évaluation.** Le vérificateur du pipeline ne se note pas lui-même :
   `EVAL_JUDGE_MODEL` est un modèle différent.
4. **Routage coût/qualité.** Petit modèle pour l'analyse et le reranking, gros modèle pour la
   rédaction et la vérification ; l'éval mesure le compromis.
5. **LiteLLM** comme couche unique : bascule API ↔ modèle local sans toucher au code.
6. **Prompts = fichiers versionnés**, identifiés par hash et stockés avec chaque résultat
   (reproductibilité, comparaison entre versions).

## Limites connues (V0)

- Le garde-fou numérique ne couvre pas les noms propres/outils inventés (le vérificateur LLM s'en charge).
- Pas d'authentification : usage mono-utilisateur local.
- Les sources RSS n'indiquent pas toujours l'entreprise (déduplication moins fine).
