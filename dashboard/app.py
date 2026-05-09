from __future__ import annotations

import os
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import yaml
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import create_engine

st.set_page_config(page_title="News Trends Dashboard", page_icon="📈", layout="wide")

# Mark as 100% automated
AUTOMATED_MODE = True


def _theme_tokens(theme_name: str) -> dict[str, str]:
    if theme_name == "Light":
        return {
            "bg": "#f4f7fb",
            "panel": "#ffffff",
            "panel_2": "#eef3fb",
            "text": "#101828",
            "muted": "#5f6b85",
            "accent": "#246bff",
            "accent_2": "#ff9f43",
            "line": "rgba(16, 24, 40, 0.09)",
            "shadow": "rgba(16, 24, 40, 0.08)",
            "chart": "plotly_white",
        }
    return {
        "bg": "#09101c",
        "panel": "#101b31",
        "panel_2": "#16233d",
        "text": "#e8eefc",
        "muted": "#9fb0d0",
        "accent": "#67d4ff",
        "accent_2": "#ffca62",
        "line": "rgba(255, 255, 255, 0.08)",
        "shadow": "rgba(0, 0, 0, 0.28)",
        "chart": "plotly_dark",
    }


if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark"

with st.sidebar:
    st.markdown("### Préférences")
    st.session_state.theme_mode = st.radio("Theme", ["Dark", "Light"], index=0, horizontal=True)

TOKENS = _theme_tokens(st.session_state.theme_mode)

st.markdown(
    f"""
    <style>
        :root {{
            --bg: {TOKENS['bg']};
            --panel: {TOKENS['panel']};
            --panel-2: {TOKENS['panel_2']};
            --text: {TOKENS['text']};
            --muted: {TOKENS['muted']};
            --accent: {TOKENS['accent']};
            --accent-2: {TOKENS['accent_2']};
            --line: {TOKENS['line']};
            --shadow: {TOKENS['shadow']};
        }}

        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(103, 212, 255, 0.14), transparent 28%),
                radial-gradient(circle at top right, rgba(255, 202, 98, 0.14), transparent 22%),
                linear-gradient(180deg, var(--bg) 0%, var(--panel-2) 100%);
            color: var(--text);
        }}

        .hero {{
            padding: 1.4rem 1.5rem;
            border: 1px solid var(--line);
            border-radius: 20px;
            background: linear-gradient(135deg, var(--panel), var(--panel-2));
            box-shadow: 0 20px 50px var(--shadow);
            margin-bottom: 1.25rem;
        }}

        .hero h1 {{
            margin: 0;
            color: var(--text);
            font-size: 2.2rem;
            letter-spacing: -0.04em;
        }}

        .hero p {{
            margin: 0.45rem 0 0;
            color: var(--muted);
            font-size: 0.98rem;
            max-width: 900px;
            line-height: 1.55;
        }}

        .kpi, .insight {{
            border: 1px solid var(--line);
            border-radius: 18px;
            background: linear-gradient(180deg, var(--panel-2), var(--panel));
            box-shadow: 0 16px 40px var(--shadow);
        }}

        .kpi {{
            padding: 1rem 1rem 0.9rem;
        }}

        .insight {{
            padding: 1rem 1rem 0.9rem;
            border-radius: 16px;
            height: 100%;
        }}

        .insight-title {{
            color: var(--muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.14em;
        }}

        .insight-value {{
            margin-top: 0.25rem;
            color: var(--text);
            font-size: 1.25rem;
            font-weight: 700;
        }}

        .insight-sub {{
            color: var(--muted);
            font-size: 0.92rem;
            margin-top: 0.25rem;
        }}

        .badge {{
            display: inline-block;
            padding: 0.38rem 0.7rem;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.04);
            color: var(--text);
            margin: 0.15rem 0.3rem 0.15rem 0;
            font-size: 0.82rem;
        }}

        .kpi-label {{
            color: var(--muted);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
        }}

        .kpi-value {{
            margin-top: 0.3rem;
            color: var(--text);
            font-size: 1.8rem;
            font-weight: 700;
        }}

        .kpi-hint {{
            color: var(--muted);
            font-size: 0.9rem;
            margin-top: 0.2rem;
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0b1324 0%, #101b31 100%);
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid var(--line);
            border-radius: 14px;
            overflow: hidden;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>MediaPulse 360</h1>
    </div>
    """,
    unsafe_allow_html=True,
)


def warehouse_engine():
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "news_dw")
    user = os.getenv("POSTGRES_USER", "news")
    pwd = os.getenv("POSTGRES_PASSWORD", "news")
    return create_engine(f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}")


@st.cache_data(ttl=300)
def load_data(query: str) -> pd.DataFrame:
    eng = warehouse_engine()
    # Use a raw DB-API connection (psycopg2) so pandas can call .cursor()
    raw_conn = eng.raw_connection()
    try:
        df = pd.read_sql(query, raw_conn)
    finally:
        try:
            raw_conn.close()
        except Exception:
            pass
    return df


@st.cache_data(ttl=300)
def get_available_sources() -> list[str]:
    """Load all available sources from the data warehouse."""
    # load from DB
    query = "SELECT DISTINCT source FROM articles_by_source ORDER BY source"
    eng = warehouse_engine()
    try:
        db_sources = pd.read_sql(query, eng)['source'].tolist()
    except Exception:
        db_sources = []

    # load from config file to include configured but not-yet-ingested sources
    config_sources = []
    try:
        # Try multiple paths for portability (dev env vs Docker)
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "config", "sources.yml"),
            "/opt/project/config/sources.yml",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "sources.yml"),
        ]
        cfg_path = None
        for candidate in candidates:
            if os.path.exists(candidate):
                cfg_path = candidate
                break
        
        if cfg_path:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh)
                for entry in cfg.get("sources", []):
                    name = entry.get("name")
                    if name:
                        config_sources.append(name)
    except Exception:
        config_sources = []

    # merge and preserve order: configured sources first, then DB-only
    merged = []
    for s in config_sources + db_sources:
        if s not in merged:
            merged.append(s)
    return ["Toutes"] + merged


with st.sidebar:
    st.markdown("### Filtres")
    available_sources = get_available_sources()
    chosen_source = st.selectbox("Source", available_sources, index=0)
    metric_window = st.slider("Fenêtre d'analyse (jours)", 1, 30, 7)
    auto_refresh_minutes = st.slider("Auto-refresh (minutes)", 1, 30, 5)
    st.caption("Les filtres s'appliquent en temps réel à tous les graphiques.")

# Auto-refresh to keep the dashboard live without manual reload.
components.html(
    f"""
    <script>
    setTimeout(function() {{
        window.parent.location.reload();
    }}, {auto_refresh_minutes * 60 * 1000});
    </script>
    """,
    height=0,
)

st.caption(f"Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (rafraîchissement auto: {auto_refresh_minutes} min)")


# Calculate total articles based on filters
# Each table has different columns, so we construct queries individually
if chosen_source != "Toutes":
    # articles_by_source has the source column but not published_day
    total_articles_query = f"SELECT articles_count FROM articles_by_source WHERE source = '{chosen_source}'"
    result = load_data(total_articles_query)
    total_articles = int(result.iloc[0, 0]) if not result.empty else 0
else:
    # articles_by_day has published_day but not source - only apply date filter here
    if metric_window < 30:
        total_articles_query = f"SELECT COALESCE(SUM(articles_count), 0) AS total FROM articles_by_day WHERE published_day >= CURRENT_DATE - INTERVAL '{metric_window} days'"
    else:
        total_articles_query = "SELECT COALESCE(SUM(articles_count), 0) AS total FROM articles_by_day"
    total_articles = int(load_data(total_articles_query).iloc[0, 0])

# For source-filtered KPI, we need raw article data
if chosen_source != "Toutes":
    top_source_query = f"SELECT source, articles_count FROM articles_by_source WHERE source = '{chosen_source}' ORDER BY articles_count DESC LIMIT 1"
else:
    top_source_query = "SELECT source, articles_count FROM articles_by_source ORDER BY articles_count DESC LIMIT 1"
top_source = load_data(top_source_query)
top_source_name = top_source.iloc[0]["source"] if not top_source.empty else "N/A"
top_source_count = int(top_source.iloc[0]["articles_count"]) if not top_source.empty else 0

metric_col1, metric_col2 = st.columns(2)

with metric_col1:
    st.markdown(
        f"""
        <div class="kpi">
            <div class="kpi-label">Articles analysés</div>
            <div class="kpi-value">{total_articles}</div>
            <div class="kpi-hint">Historique agrégé du Data Warehouse</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with metric_col2:
    st.markdown(
        f"""
        <div class="kpi">
            <div class="kpi-label">Source dominante</div>
            <div class="kpi-value">{top_source_name}</div>
            <div class="kpi-hint">{top_source_count} articles</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



st.markdown("### Insights rapides")
insight_col1, insight_col2 = st.columns(2)

# keywords_preview removed from insights display (badges were removed)

with insight_col1:
    st.markdown(
        f"""
        <div class="insight">
            <div class="insight-title">Lecture métier</div>
            <div class="insight-value">Veille continue</div>
            <div class="insight-sub">Le pipeline alimente des indicateurs journaliers, sectoriels et lexicaux exploitables en soutenance.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with insight_col2:
    st.markdown(
        f"""
        <div class="insight">
            <div class="insight-title">Source la plus active</div>
            <div class="insight-value">{top_source_name}</div>
            <div class="insight-sub">{top_source_count} articles cumulés dans le DWH.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Third insight column removed per request

st.markdown("### Vue synthétique")

col1, col2 = st.columns((1.2, 1))

with col1:
    if chosen_source != "Toutes":
        by_source_query = f"SELECT source, articles_count FROM articles_by_source WHERE source = '{chosen_source}' ORDER BY articles_count DESC"
    else:
        by_source_query = "SELECT source, articles_count FROM articles_by_source ORDER BY articles_count DESC"
    by_source = load_data(by_source_query)
    fig_source = px.bar(
        by_source,
        x="source",
        y="articles_count",
        title=f"Nombre d'articles par source {('(filtré: ' + chosen_source + ')') if chosen_source != 'Toutes' else ''}",
        color="articles_count",
        color_continuous_scale=["#67d4ff", "#2679ff"],
    )
    fig_source.update_layout(template=TOKENS["chart"], title_font_size=18, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_source, use_container_width=True)

with col2:
    # articles_by_theme doesn't have published_day column, so we don't filter by date
    by_theme_query = "SELECT theme, articles_count FROM articles_by_theme ORDER BY articles_count DESC"
    by_theme = load_data(by_theme_query)
    fig_theme = px.pie(
        by_theme,
        names="theme",
        values="articles_count",
        title=f"Répartition par thème (historique)",
        color_discrete_sequence=["#67d4ff", "#4fc3f7", "#ffca62", "#7ee081"],
        hole=0.42,
    )
    fig_theme.update_layout(template=TOKENS["chart"], title_font_size=18, margin=dict(l=10, r=10, t=50, b=10), legend_title_text="")
    st.plotly_chart(fig_theme, use_container_width=True)

st.markdown("### Tendance temporelle")
if metric_window < 30:
    by_day_query = f"SELECT published_day, articles_count FROM articles_by_day WHERE published_day >= CURRENT_DATE - INTERVAL '{metric_window} days' ORDER BY published_day"
else:
    by_day_query = "SELECT published_day, articles_count FROM articles_by_day ORDER BY published_day"
by_day = load_data(by_day_query)
fig_day = px.line(
    by_day,
    x="published_day",
    y="articles_count",
    markers=True,
    title=f"Tendance d'actualité (derniers {metric_window} jours)",
    line_shape="spline",
)
fig_day.update_traces(line=dict(color="#67d4ff", width=4), marker=dict(size=10, color="#ffca62"))
fig_day.update_layout(template=TOKENS["chart"], title_font_size=18, margin=dict(l=10, r=10, t=50, b=10))
st.plotly_chart(fig_day, use_container_width=True)

st.markdown("### Activité par heure (24h)")
if chosen_source != "Toutes":
    by_hour_query = (
        "SELECT date_trunc('hour', published_at) AS published_hour, source, COUNT(*) AS articles_count "
        f"FROM articles_detail WHERE source = '{chosen_source}' AND published_at >= NOW() - INTERVAL '24 hours' "
        "GROUP BY 1, 2 ORDER BY 1"
    )
else:
    by_hour_query = (
        "SELECT date_trunc('hour', published_at) AS published_hour, source, COUNT(*) AS articles_count "
        "FROM articles_detail WHERE published_at >= NOW() - INTERVAL '24 hours' "
        "GROUP BY 1, 2 ORDER BY 1"
    )

by_hour = load_data(by_hour_query)
if not by_hour.empty:
    fig_hour = px.line(
        by_hour,
        x="published_hour",
        y="articles_count",
        color="source",
        markers=True,
        title="Volume d'articles par heure et par source (24h)",
    )
    fig_hour.update_layout(template=TOKENS["chart"], title_font_size=18, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_hour, use_container_width=True)
else:
    st.info("Pas encore assez de données pour la vue horaire sur les 24 dernières heures.")

st.markdown("### Articles récents")
show_quarantine = st.sidebar.checkbox("Afficher les titres en quarantaine", value=False)

if chosen_source != "Toutes":
    articles_query = f"SELECT article_id, title, author, source, published_at, url, quarantine FROM articles_detail WHERE source = '{chosen_source}' ORDER BY published_at DESC LIMIT 10"
else:
    articles_query = (
        "SELECT article_id, title, author, source, published_at, url, quarantine FROM ("
        " SELECT article_id, title, author, source, published_at, url, quarantine,"
        " ROW_NUMBER() OVER (PARTITION BY source ORDER BY published_at DESC) AS rn"
        " FROM articles_detail"
        ") t WHERE rn <= 10 ORDER BY source, published_at DESC"
    )
articles = load_data(articles_query)

if not articles.empty:
    # Validation heuristics: separate suspicious titles into quarantine
    def is_suspicious_title(t: str) -> bool:
        if not t:
            return True
        lt = t.strip()
        if len(lt) < 15:
            return True
        low = lt.lower()
        nav_blacklist = ("register", "sign in", "signin", "home", "news", "sport", "live", "watch", "listen")
        if any(word in low for word in nav_blacklist):
            return True
        # too many punctuation or all-caps
        if sum(1 for c in lt if c.isupper()) > len(lt) * 0.6 and len(lt) > 5:
            return True
        return False

    def is_suspicious_url(url: str, source: str) -> bool:
        if not url:
            return True
        u = url.strip()
        if not (u.startswith("http://") or u.startswith("https://")):
            return True

        try:
            parsed = urlparse(u)
        except Exception:
            return True

        host = parsed.netloc.lower()
        path = parsed.path.lower()
        src = (source or "").lower()

        if src == "bbc news":
            if "bbc.com" not in host:
                return True
            if not path.startswith("/news/"):
                return True
        elif src == "hespress":
            if "hespress.com" not in host:
                return True
            # Real Hespress article pages are usually HTML article pages.
            if not path.endswith(".html"):
                return True
        elif src == "reuters world":
            if "reuters.com" not in host:
                return True
            if "/world/" not in path:
                return True

        return False

    good = []
    quarantine = []
    for idx, row in articles.iterrows():
        title = str(row.get("title", ""))
        source = str(row.get("source", ""))
        url = str(row.get("url", ""))
        qflag = bool(row.get("quarantine", False)) if "quarantine" in row else False
        if qflag:
            quarantine.append(row)
        else:
            good.append(row)

    if good:
        st.caption("Affichage: 10 derniers articles fiables par source.")
        current_source = None
        for row in good:
            if chosen_source == "Toutes" and current_source != row["source"]:
                current_source = row["source"]
                st.markdown(f"#### {current_source}")
            # make title clickable
            url = row.get("url", "#")
            title_html = f'<a href="{url}" target="_blank" rel="noopener" style="color:inherit; text-decoration:none">{row["title"]}</a>'
            st.markdown(
                f"""
                <div class="insight" style="margin-bottom:0.9rem; padding: 1rem;">
                    <div class="insight-title">{row['source']}</div>
                    <div class="insight-value" style="font-size: 1.1rem; margin-top: 0.4rem;">{title_html}</div>
                    <div class="insight-sub" style="margin-top: 0.4rem;">
                        <strong>Auteur:</strong> {row['author']} | <strong>Date:</strong> {row['published_at']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Aucun article fiable trouvé pour cette source.")

    if quarantine and show_quarantine:
        with st.expander("Titres suspectés (quarantaine)"):
            # bulk approve button
            q_ids = [row.get("article_id") for row in quarantine]
            if q_ids:
                if st.button("Valider tout", key="val_all"):
                    try:
                        eng = warehouse_engine()
                        eng.execute(
                            "UPDATE articles_detail SET quarantine = FALSE WHERE article_id = ANY(%s)",
                            (q_ids,)
                        )
                        # insert audit records for bulk approval
                        try:
                            eng.execute(
                                "INSERT INTO quarantine_audit (article_id, action, performed_by, reason) SELECT aid, 'unmark', 'ui', 'approved_ui' FROM unnest(%s::text[]) AS aid",
                                (q_ids,)
                            )
                        except Exception:
                            pass
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erreur en mettant à jour la quarantaine: {e}")

            for row in quarantine:
                url = row.get("url", "#")
                aid = row.get("article_id")
                cols = st.columns((8, 1))
                with cols[0]:
                    st.markdown(
                        f"- **{row['source']}**: [{row['title']}]({url}) — {row['author']} ({row['published_at']})",
                        unsafe_allow_html=True,
                    )
                with cols[1]:
                    btn = st.button("Valider", key=f"val_{aid}")
                    if btn:
                        # mark as not quarantined in DB and refresh
                        try:
                            eng = warehouse_engine()
                            eng.execute(
                                f"UPDATE articles_detail SET quarantine = FALSE WHERE article_id = '{aid}'"
                            )
                            try:
                                eng.execute(
                                    "INSERT INTO quarantine_audit (article_id, action, performed_by, reason) VALUES (%s, 'unmark', 'ui', 'approved_ui')",
                                    (aid,)
                                )
                            except Exception:
                                pass
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Erreur en mettant à jour la quarantaine: {e}")
else:
    st.info("Aucun article trouvé pour cette source.")

    # top_keywords table is global; do not filter by published_day (column not present)
keywords = load_data("SELECT keyword, frequency FROM top_keywords ORDER BY frequency DESC LIMIT 25")
st.markdown("### Top mots-clés / Top sources")

bottom_left, bottom_right = st.columns((1, 1.1))

with bottom_left:
    st.markdown(
        "<div class='insight'><div class='insight-title'>Mots-clés les plus fréquents</div></div>",
        unsafe_allow_html=True,
    )
    st.dataframe(
        keywords,
        use_container_width=True,
        hide_index=True,
        column_config={"frequency": st.column_config.NumberColumn("Fréquence", format="%d")},
    )

with bottom_right:
    st.markdown(
        "<div class='insight'><div class='insight-title'>Sources dominantes</div></div>",
        unsafe_allow_html=True,
    )
    for row in by_source.head(5).itertuples(index=False):
        st.markdown(
            f"""
            <div class="insight" style="margin-bottom:0.7rem;">
                <div class="insight-value">{row.source}</div>
                <div class="insight-sub">{int(row.articles_count)} articles analysés</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("### Répartition par pays")
by_country = load_data("SELECT source_country, articles_count FROM articles_by_country ORDER BY articles_count DESC")
if not by_country.empty:
    fig_country = px.bar(
        by_country,
        x="source_country",
        y="articles_count",
        title="Nombre d'articles par pays / zone source",
        color="articles_count",
        color_continuous_scale=["#ffca62", "#2679ff"],
    )
    fig_country.update_layout(template=TOKENS["chart"], title_font_size=18, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_country, use_container_width=True)
else:
    st.info("Aucune donnée disponible pour la répartition par pays.")
