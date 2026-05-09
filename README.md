# MediaPulse 360

MediaPulse 360 est une solution de veille de presse automatisée. Le projet collecte des articles depuis plusieurs sources RSS, les nettoie, les organise dans une architecture en couches, puis les affiche dans un tableau de bord simple à lire.

L’objectif est de transformer des flux d’actualités en informations compréhensibles par un utilisateur non technique, tout en conservant une chaîne de traitement claire, traçable et fiable.

## Vue d’ensemble

Le projet repose sur quatre idées principales :

1. Collecter automatiquement les articles de presse.
2. Nettoyer et structurer les données pour éviter les doublons et les contenus inutilisables.
3. Produire des indicateurs simples pour suivre l’activité des sources.
4. Présenter les résultats dans un dashboard accessible et interactif.

## Fonctionnement du projet

### 1. Collecte des articles

Le pipeline lit les flux RSS configurés dans le projet et récupère les nouveaux articles de façon régulière. Chaque article est identifié avec un identifiant stable afin de conserver une cohérence dans le temps.

### 2. Stockage initial

Les données brutes sont d’abord conservées dans le data lake. Cette étape garde une copie fidèle des contenus récupérés avant toute transformation.

### 3. Nettoyage et transformation

Les articles sont ensuite nettoyés pour supprimer le HTML, normaliser les champs, détecter la langue et calculer des indicateurs utiles comme la longueur du texte ou le nombre de mots.

### 4. Analyse et restitution

Les données consolidées alimentent le data warehouse et le tableau de bord. L’utilisateur peut visualiser les sources, les thèmes, les tendances et les articles en quarantaine.

## Architecture technique

Le projet utilise une architecture medallion :

- **Bronze** : stockage des données brutes.
- **Silver** : données nettoyées et standardisées.
- **Gold** : agrégations et tableaux analytiques.

Cette organisation permet de passer progressivement d’un contenu brut à une information prête à l’analyse.

## Technologies utilisées

- Python 3.11 pour la collecte et le traitement.
- Streamlit pour le tableau de bord.
- PostgreSQL 16 pour le data warehouse.
- MinIO pour le data lake.
- Apache Airflow pour l’orchestration des tâches.
- Docker Compose pour lancer l’ensemble des services.
- BeautifulSoup, feedparser, pandas, SQLAlchemy et psycopg2 pour le traitement des données.

## Lancement du projet

Pour démarrer tous les services :

```bash
docker compose up -d
```

Ensuite, ouvrir :

- Tableau de bord : http://localhost:8501
- Airflow : http://localhost:8081
- MinIO Console : http://localhost:9001

## Ingestion manuelle

Pour lancer une ingestion ponctuelle :

```bash
docker compose exec -T streamlit python /opt/project/scripts/run_batch_insert.py
```

Le service `ingest` fonctionne aussi en continu dans Docker pour exécuter la collecte à intervalles réguliers.

## Migrations

Le dépôt contient plusieurs migrations pour garder le schéma de données à jour :

- `sql/init_dw.sql` initialise le data warehouse.
- `migrations/20260507_add_canonical_and_quarantine_audit.sql` ajoute les colonnes liées aux URL canoniques et à l’audit de quarantaine.
- `migrations/20260508_backfill_quarantine_audit.sql` complète l’historique pour les lignes déjà en quarantaine.

## Tests

Pour exécuter les tests du projet :

```bash
.venv\Scripts\python -m pytest -q
```

## Points importants

- Le tableau de bord se rafraîchit automatiquement toutes les 5 minutes.
- Les titres d’articles ouvrent la source originale dans un nouvel onglet.
- Les articles suspects peuvent être isolés pour contrôle avant publication.
- Le projet est prêt pour une démonstration, une remise GitHub et le rapport final.

## Auteur

Nom : Mehdi Chmiti

Surnom : mccrking