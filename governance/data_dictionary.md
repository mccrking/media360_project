# Data Dictionary

## Bronze (Raw)
- article_id: unique hash de l'URL
- title: titre brut de l'article
- author: auteur brut
- published_at: date de publication brute (ISO)
- category: categorie brute
- content_html: contenu HTML brut
- content: contenu texte brut
- source: nom de la source
- source_country: pays de la source
- url: URL de l'article
- scraped_at: timestamp de scraping
- ingested_at: timestamp d'ingestion
- ingestion_mode: batch ou streaming

## Silver (Clean)
- content_clean: contenu normalise
- content_from_html: texte extrait de HTML
- content_final: contenu nettoye final
- language: langue detectee
- published_at: date normalisee UTC

## Gold (Analytics)
- articles_by_day(published_day, articles_count)
- articles_by_theme(theme, articles_count)
- articles_by_country(source_country, articles_count)
- articles_by_source(source, articles_count)
- top_keywords(keyword, frequency)
