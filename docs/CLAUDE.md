# HOTARU — Référence agent

**Documentation principale :** [README.md](../README.md)

Ce fichier centralise les instructions pour l'agent (Cursor/Claude). Toute la doc projet (architecture, SaaS, structure, conventions, roadmap) est dans **README.md**. Consulter README.md pour :

- Vision produit et modules (Audit, Authority, Master, Leaf, Eco-Score)
- Structure du repo et rôles des fichiers
- Logique SaaS (auth, session_keys, isolation user_email)
- Navigation et onglets
- Installation, configuration, design system
- Conventions de code (session, fetch_page, section-title, version)
- Roadmap

**Règles à respecter en priorité :** design noir + rouge sur fond blanc ; titres `XX / TITRE` ; usage de `core.session_keys` et `get_current_user_email()` pour les données utilisateur ; fetch d'une page via `core.scraping.fetch_page`.

**Versioning (à ne jamais oublier) :** À chaque push ou merge sur `main` (pull request), mettre à jour `version.py` avec la date et l'heure courantes (`BUILD_DATE = "YYYY-MM-DD HH:MM"`) et incrémenter `VERSION` si besoin. L'app affiche cette version dans le header et le footer. Ne jamais pusher sans mettre à jour `version.py`.
