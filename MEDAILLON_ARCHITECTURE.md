# Architecture Médaillon - MediaPulse 360

## Vue d'ensemble

L'architecture Médaillon implémente un pipeline de données en 3 couches :

```
Bronze (Raw) → Silver (Clean) → Gold (Analytics)
```

## 1. Bronze Layer (Données Brutes)

**Stockage:** MinIO Object Storage  
**Format:** JSONL (JSON Lines)  
**Contenu:** Articles bruts du scraper RSS sans modifications

### Fichiers de Bronze:
- `articles_raw_YYYYMMDD_HHMMSS.jsonl` — Articles non traités du scraper

### Caractéristiques:
- Historique complet conservé
- Pas de suppression de données
- Audit trail des ingestions
- Extraction programmée (toutes les heures via Airflow)

## 2. Silver Layer (Données Nettoyées)

**Stockage:** 
- MinIO (Parquet files)
- PostgreSQL table `articles_silver`

**Transformations appliquées:**
- ✓ Suppression des balises HTML
- ✓ Normalisation du texte (accents, espaces)
- ✓ Calcul de la longueur du contenu
- ✓ Comptage des mots
- ✓ Détection automatique de la langue
- ✓ Score de qualité des données (0-1)

### Métadonnées ajoutées:
```sql
- content_clean: Contenu sans HTML
- content_length: Nombre de caractères
- word_count: Nombre de mots
- detected_language: 'fr', 'en', 'mixed'
- data_quality_score: Score 0-1 basé sur la complétude
- silver_timestamp: Timestamp de transformation
```

### Table PostgreSQL:
```sql
articles_silver (
    article_id PRIMARY KEY,
    title, title_normalized,
    content, content_clean,
    content_length, word_count,
    source, category, detected_language,
    data_quality_score,
    published_at, url, canonical_url,
    silver_timestamp,
    transformation_audit (référence)
)
```

## 3. Gold Layer (Tables Analytiques)

**Stockage:** PostgreSQL  
**Contenu:** Agrégations et indicateurs clés pour les dashboards

### Tables Gold principales:

#### articles_by_source
```sql
source | articles_count | last_updated
```
Distribution des articles par source.

#### articles_by_category
```sql
category | articles_count | last_updated
```
Distribution des articles par catégorie.

#### top_keywords
```sql
keyword | frequency | last_updated
```
Les 100 mots-clés les plus fréquents.

#### daily_article_trends
```sql
trend_date | source | articles_count | avg_word_count | avg_quality_score
```
Tendances quotidiennes par source.

#### analytics_summary
```sql
summary_timestamp | total_articles | articles_today | 
quarantined_articles | unique_sources | avg_quality_score | languages_detected
```
Résumé horaire des KPIs.

## Orchestration avec Apache Airflow

### DAG Principal: `mediapulse360_pipeline`

**Schedule:** Horaire (`0 * * * *`)

**Tâches:**
1. `extract_bronze` — Scrape RSS → Stocke dans MinIO Bronze
2. `transform_silver` — Nettoie et normalise → MinIO Silver + PostgreSQL
3. `load_gold` — Agrège → Tables analytiques PostgreSQL
4. `generate_metrics` — Génère KPIs pour dashboards
5. `data_quality_check` — Valide intégrité des données

**Dépendances:**
```
bronze → silver → gold → [metrics, quality]
```

### Airflow UI:
- **Webserver:** http://localhost:8081 (Admin / admin)
- **Logs:** `/airflow/logs/`
- **DAGs:** `/airflow/dags/`

## Qualité des Données

### Trois dimensions validées:

#### 1. Complétude
- Articles sans titre
- Contenu manquant
- Dates manquantes

#### 2. Cohérence
- Absence de clés étrangères orphelines
- Validité des références (audit → articles)

#### 3. Validité
- Dates futures (invalides)
- Scores de qualité en dehors [0,1]
- Longueurs négatives

### Rapport de qualité:
```json
{
  "timestamp": "2026-05-08T21:00:00",
  "summary": {
    "total_checks": 10,
    "passed": 9,
    "failed": 1,
    "pass_rate": 90.0
  },
  "checks": [
    {"name": "articles_detail.title_null", "status": "PASS", "value": 0},
    ...
  ]
}
```

## MinIO - Data Lake

### Configuration:
- **Endpoint:** http://localhost:9000
- **Console:** http://localhost:9001
- **Credentials:** minioadmin / minioadmin

### Buckets:
```
bronze-articles/     ← Articles bruts (JSONL)
silver-articles/     ← Articles nettoyés (Parquet)
gold-analytics/      ← Tables analytiques (CSV)
```

## Flux de Données Complet

```
RSS Feeds
   ↓
[Scraper] (Bronze)
   ↓
MinIO Bronze: articles_raw_*.jsonl
   ↓
[Transform] (Silver)
   ↓
MinIO Silver: articles_cleaned_*.parquet
PostgreSQL: articles_silver table
   ↓
[Aggregate] (Gold)
   ↓
PostgreSQL: articles_by_source, top_keywords, daily_trends
   ↓
[Streamlit Dashboard]
```

## Migrations et Déploiement

### Migrations à exécuter (dans l'ordre):

1. `sql/init_dw.sql` — Initialisation du schema
2. `migrations/20260507_add_canonical_and_quarantine_audit.sql`
3. `migrations/20260508_backfill_quarantine_audit.sql`
4. `migrations/20260509_create_silver_layer.sql`
5. `migrations/20260510_create_gold_layer.sql`

### Docker Compose Services:

```yaml
postgres:        # Data Warehouse (port 5432)
minio:           # Data Lake (ports 9000, 9001)
airflow_db:      # Airflow Metadata (PostgreSQL)
airflow_webserver:  # Airflow UI (port 8080)
airflow_scheduler:  # Airflow Scheduler (background)
streamlit:       # Dashboard (port 8501)
ingest:          # Ingestion Service (backup)
```

## Démarrage complet

```bash
# Construire et lancer tous les services
docker compose up -d

# Initialiser les migrations
docker compose exec -T postgres psql -U news -d news_dw < sql/init_dw.sql
docker compose exec -T postgres psql -U news -d news_dw < migrations/20260509_create_silver_layer.sql
docker compose exec -T postgres psql -U news -d news_dw < migrations/20260510_create_gold_layer.sql

# Vérifier les services
docker compose ps
```

## Accès aux interfaces

- **Streamlit Dashboard:** http://localhost:8501
- **Airflow Webserver:** http://localhost:8081 (admin/admin)
- **MinIO Console:** http://localhost:9001 (minioadmin/minioadmin)
- **PostgreSQL:** localhost:5432 (news/news)

## Performance & Scalabilité

### Optimisations implémentées:

- ✓ Indexes sur colonnes fréquemment filtrées
- ✓ Partitioning temporel possiblein Gold layer
- ✓ Compression Parquet pour MinIO
- ✓ Connection pooling SQLAlchemy
- ✓ Incremental processing par heure

### Bottlenecks identifiés:

1. Scraping RSS — Limité par les timeouts réseau
2. Détection de langue — Utilise heuristique simple (peut être améliorée avec ML)
3. Stockage MinIO — Escalabilité limitée par disque local (utiliser S3 en prod)

## Évolutions futures

1. **Détection d'anomalies** — Machine Learning pour qualifier les articles
2. **Streaming Kafka** — Complément au batch pour temps réel
3. **dbt for Transformations** — Remplacer SQL ad-hoc
4. **Data Catalog** — Apache Atlas pour governance
5. **API REST** — Exposer les données Gold via API
6. **Monitoring** — Prometheus + Grafana pour observabilité
