import streamlit as st
import asyncio
import pandas as pd
import json
import os
from datetime import datetime
import threading
import queue
import time
from config import get_config

# ── Page config ───────────────────────────────
st.set_page_config(
    page_title="LeadGen India",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1, h2, h3, .stMetric label {
    font-family: 'Syne', sans-serif !important;
}

/* Main header */
.main-header {
    background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 50%, #16213e 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 2rem;
    border: 1px solid #ffffff15;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, #e94560 0%, transparent 70%);
    opacity: 0.15;
    border-radius: 50%;
}
.main-header h1 {
    color: #ffffff;
    font-size: 2.4rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.02em;
}
.main-header p {
    color: #aaaaaa;
    margin: 0.4rem 0 0 0;
    font-size: 1rem;
}
.accent { color: #e94560; }

/* Score badge */
.score-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.85rem;
}
.score-high { background: #0d2b1f; color: #2ecc71; border: 1px solid #2ecc71; }
.score-med  { background: #2b1f0d; color: #f39c12; border: 1px solid #f39c12; }
.score-low  { background: #2b0d0d; color: #e74c3c; border: 1px solid #e74c3c; }

/* Lead card */
.lead-card {
    background: #0f0f1a;
    border: 1px solid #ffffff12;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.8rem;
    transition: border-color 0.2s;
}
.lead-card:hover { border-color: #e9456050; }
.lead-name { font-family: 'Syne', sans-serif; font-weight: 700; font-size: 1.05rem; color: #fff; }
.lead-meta { color: #888; font-size: 0.85rem; margin-top: 0.2rem; }
.pitch-box {
    background: #1a1a2e;
    border-left: 3px solid #e94560;
    padding: 0.6rem 1rem;
    border-radius: 0 8px 8px 0;
    color: #ddd;
    font-size: 0.9rem;
    margin-top: 0.8rem;
    font-style: italic;
}
.signal-pill {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    margin: 2px;
}
.pill-good { background: #0d2b1f; color: #2ecc71; }
.pill-bad  { background: #2b0d0d; color: #e74c3c; }

/* Progress */
.progress-step {
    padding: 0.5rem 1rem;
    background: #0f0f1a;
    border-radius: 8px;
    margin: 0.3rem 0;
    border-left: 3px solid #333;
    font-size: 0.9rem;
    color: #ccc;
}
.progress-active { border-left-color: #e94560; color: #fff; }
.progress-done   { border-left-color: #2ecc71; color: #888; }

/* Metric cards */
.metric-box {
    background: #0f0f1a;
    border: 1px solid #ffffff12;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.metric-value { font-family: 'Syne', sans-serif; font-size: 2.2rem; font-weight: 800; color: #e94560; }
.metric-label { color: #888; font-size: 0.85rem; margin-top: 0.2rem; }

[data-testid="stSidebar"] { background: #0a0a12; border-right: 1px solid #ffffff10; }
.stButton button { font-family: 'Syne', sans-serif !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────
if 'results' not in st.session_state:
    st.session_state.results = None
if 'running' not in st.session_state:
    st.session_state.running = False
if 'progress_log' not in st.session_state:
    st.session_state.progress_log = []
if 'queries' not in st.session_state:
    st.session_state.queries = [
        ("wedding planner", "Mumbai"),
        ("skin clinic", "Hyderabad"),
        ("dental clinic", "Pune"),
        ("fitness center", "Bangalore"),
        ("interior designer", "Delhi"),
    ]
if 'query_version' not in st.session_state:
    st.session_state.query_version = 0


# ─────────────────────────────────────────────────────
# LOAD CONFIG FROM .ENV
# ─────────────────────────────────────────────────────
env_config = get_config()

# ─────────────────────────────────────────────────────
# SIDEBAR — CONFIG
# ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 Configuration")
    st.markdown("*Loaded from .env file*")
    
    st.markdown("#### API Keys")
    serpapi_status = "✓ Set" if env_config['serpapi_key'] else "✗ Missing"
    openrouter_status = "✓ Set" if env_config['openrouter_key'] else "✗ Missing"
    hunter_status = "✓ Set" if env_config['hunter_key'] else "✗ Not set (optional)"
    
    st.markdown(f"**SerpAPI:** {serpapi_status}")
    st.markdown(f"**OpenRouter:** {openrouter_status}")
    st.markdown(f"**Hunter.io:** {hunter_status}")
    
    st.markdown("#### Google Sheets")
    sheet_status = "✓ Set" if env_config['sheet_id'] else "✗ Missing"
    sa_status = "✓ Set" if env_config['sheets_service_account_json'] else "✗ Missing"
    
    st.markdown(f"**Sheet ID:** {sheet_status}")
    st.markdown(f"**Service Account:** {sa_status}")

    st.markdown("#### ⚙️ Settings")
    min_score = st.slider("Minimum Lead Score", 1, 10, env_config['min_score'])
    max_concurrent = st.slider("Concurrent Scrapes", 1, 10, env_config['max_concurrent_scrapes'])

    st.markdown("---")
    st.markdown("<small style='color:#555'>LeadGen India v1.0<br>Built with ❤️</small>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🎯 LeadGen <span class="accent">India</span></h1>
    <p>AI-powered local business lead generation — find, score, and pitch Indian SMBs</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🚀 Run Pipeline", "📋 Results", "📈 Analytics"])


# ─────────────────────────────────────────────────────
# TAB 1: RUN PIPELINE
# ─────────────────────────────────────────────────────
with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### 🔍 Search Queries")
        st.caption("Add business type + city combinations to search")

        # Query builder - use version in key to force refresh
        queries_display = []
        for i, (biz, city) in enumerate(st.session_state.queries):
            c1, c2, c3 = st.columns([3, 3, 1])
            with c1:
                new_biz = st.text_input(f"Business Type", value=biz, key=f"biz_{i}_v{st.session_state.query_version}", label_visibility="collapsed")
            with c2:
                new_city = st.text_input(f"City", value=city, key=f"city_{i}_v{st.session_state.query_version}", label_visibility="collapsed")
            with c3:
                if st.button("✕", key=f"del_{i}_v{st.session_state.query_version}"):
                    st.session_state.queries.pop(i)
                    st.session_state.query_version += 1
                    st.rerun()
            queries_display.append((new_biz, new_city))

        # Update queries from user input
        st.session_state.queries = queries_display

        col_add1, col_add2, col_add3 = st.columns([3, 3, 1])
        with col_add1:
            new_biz_input = st.text_input("New business type", placeholder="e.g. yoga studio", label_visibility="collapsed", key=f"new_biz_v{st.session_state.query_version}")
        with col_add2:
            new_city_input = st.text_input("New city", placeholder="e.g. Chennai", label_visibility="collapsed", key=f"new_city_v{st.session_state.query_version}")
        with col_add3:
            if st.button("＋ Add", key=f"add_v{st.session_state.query_version}"):
                if new_biz_input and new_city_input:
                    st.session_state.queries.append((new_biz_input, new_city_input))
                    st.session_state.query_version += 1
                    st.rerun()

    with col2:
        st.markdown("#### 📦 Quick Presets")
        if st.button("🏥 Healthcare Bundle", width="stretch", key="preset_healthcare"):
            st.session_state.queries = [
                ("dental clinic", "Mumbai"), ("skin clinic", "Delhi"),
                ("physiotherapy", "Bangalore"), ("eye clinic", "Chennai"),
                ("dentist", "Hyderabad"),
            ]
            st.session_state.query_version += 1  # Force refresh
            st.rerun()
        if st.button("💒 Wedding Industry", width="stretch", key="preset_wedding"):
            st.session_state.queries = [
                ("wedding planner", "Mumbai"), ("wedding photographer", "Delhi"),
                ("wedding venue", "Bangalore"), ("bridal makeup", "Jaipur"),
                ("wedding caterer", "Kochi"),
            ]
            st.session_state.query_version += 1  # Force refresh
            st.rerun()
        if st.button("🏋️ Fitness & Wellness", width="stretch", key="preset_fitness"):
            st.session_state.queries = [
                ("gym", "Mumbai"), ("yoga studio", "Delhi"),
                ("fitness center", "Pune"), ("crossfit", "Bangalore"),
                ("zumba classes", "Hyderabad"),
            ]
            st.session_state.query_version += 1  # Force refresh
            st.rerun()
        if st.button("🎓 Education", width="stretch", key="preset_education"):
            st.session_state.queries = [
                ("coaching institute", "Lucknow"), ("tuition center", "Patna"),
                ("ias coaching", "Delhi"), ("ca coaching", "Mumbai"),
                ("neet coaching", "Chennai"),
            ]
            st.session_state.query_version += 1  # Force refresh
            st.rerun()

    st.markdown("---")

    # Run button
    if not st.session_state.running:
        if st.button("🚀 Start Lead Generation", type="primary", width="stretch"):
            if not env_config['serpapi_key']:
                st.error("SerpAPI key required! Check your .env file.")
            elif not st.session_state.queries:
                st.error("Add at least one search query!")
            else:
                st.session_state.running = True
                st.session_state.progress_log = []
                st.session_state.results = None
                st.rerun()
    else:
        st.button("⏳ Running...", disabled=True, width="stretch")

    # Progress display
    if st.session_state.running:
        st.markdown("#### ⚡ Pipeline Progress")
        progress_container = st.container()

        # Use config from .env
        config = env_config

        progress_queue = queue.Queue()
        log_lines = []

        def progress_cb(stage, current, total, message):
            progress_queue.put((stage, current, total, message))

        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from pipeline import run_pipeline

        # Run pipeline
        try:
            with progress_container:
                status_area = st.empty()
                bar = st.progress(0)

                async def run_with_progress():
                    return await run_pipeline(
                        config,
                        queries=st.session_state.queries,
                        progress_callback=progress_cb,
                        min_score=min_score,
                        max_concurrent_scrapes=max_concurrent,
                    )

                # We need to run the async pipeline
                result = asyncio.run(run_with_progress())
                st.session_state.results = result
                st.session_state.running = False

                st.success(f"✅ Done! Found **{len(result['qualified_leads'])}** qualified leads. Saved **{result['saved_to_sheet']}** to Google Sheets.")
                st.rerun()

        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.session_state.running = False


# ─────────────────────────────────────────────────────
# TAB 2: RESULTS
# ─────────────────────────────────────────────────────
with tab2:
    if not st.session_state.results:
        st.info("Run the pipeline first to see results here.")
    else:
        results = st.session_state.results
        leads = results.get('qualified_leads', [])

        # Summary metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.markdown(f'<div class="metric-box"><div class="metric-value">{results["total_scraped"]}</div><div class="metric-label">Total Found</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-box"><div class="metric-value">{len(leads)}</div><div class="metric-label">Qualified Leads</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-box"><div class="metric-value">{results["saved_to_sheet"]}</div><div class="metric-label">Saved to Sheet</div></div>', unsafe_allow_html=True)
        with m4:
            avg = round(sum(l.get('lead_score',0) for l in leads) / len(leads), 1) if leads else 0
            st.markdown(f'<div class="metric-box"><div class="metric-value">{avg}</div><div class="metric-label">Avg Score</div></div>', unsafe_allow_html=True)
        with m5:
            high = sum(1 for l in leads if l.get('urgency') == 'HIGH')
            st.markdown(f'<div class="metric-box"><div class="metric-value">{high}</div><div class="metric-label">High Urgency</div></div>', unsafe_allow_html=True)

        st.markdown("---")

        # Filters
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            cities = sorted(set(l.get('city', '') for l in leads))
            filter_city = st.multiselect("Filter by City", cities)
        with fc2:
            biztypes = sorted(set(l.get('business_type', '') for l in leads))
            filter_biz = st.multiselect("Filter by Business Type", biztypes)
        with fc3:
            filter_score = st.slider("Min Score", 1, 10, min_score)

        # Filter leads
        filtered = leads
        if filter_city:
            filtered = [l for l in filtered if l.get('city') in filter_city]
        if filter_biz:
            filtered = [l for l in filtered if l.get('business_type') in filter_biz]
        filtered = [l for l in filtered if l.get('lead_score', 0) >= filter_score]

        st.caption(f"Showing {len(filtered)} of {len(leads)} leads")

        # Export
        if filtered:
            df = pd.DataFrame(filtered)
            csv = df.to_csv(index=False).encode()
            st.download_button("⬇️ Export CSV", csv, "leads.csv", "text/csv")

        st.markdown("---")

        # Lead cards
        for lead in filtered:
            score = lead.get('lead_score', 0)
            if score >= 8:
                badge_class = 'score-high'
            elif score >= 6:
                badge_class = 'score-med'
            else:
                badge_class = 'score-low'

            urgency_color = {'HIGH': '#e94560', 'MEDIUM': '#f39c12', 'LOW': '#3498db'}.get(lead.get('urgency', ''), '#888')

            signals_html = ''
            signal_map = [
                ('SSL', lead.get('has_ssl')), ('Mobile', lead.get('has_mobile_viewport')),
                ('WhatsApp', lead.get('has_whatsapp')), ('Booking', lead.get('has_booking_form')),
                ('Chatbot', lead.get('has_chatbot')), ('Payment', lead.get('has_online_payment')),
            ]
            for sig_name, sig_val in signal_map:
                cls = 'pill-good' if sig_val else 'pill-bad'
                icon = '✓' if sig_val else '✗'
                signals_html += f'<span class="signal-pill {cls}">{icon} {sig_name}</span>'

            website_display = lead.get('website') or lead.get('raw_url') or 'No website'
            phone = lead.get('phone', 'N/A')
            email = lead.get('email', '')
            pitch = lead.get('recommended_pitch', '')
            service = lead.get('service_opportunity', '')
            rated = f"⭐ {lead.get('google_rating', 'N/A')} ({lead.get('google_reviews', 0)} reviews)"

            st.markdown(f"""
<div class="lead-card">
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
            <div class="lead-name">{lead.get('company_name', '')}</div>
            <div class="lead-meta">📍 {lead.get('city', '')} &nbsp;|&nbsp; 💼 {lead.get('business_type', '')} &nbsp;|&nbsp; {rated}</div>
            <div class="lead-meta" style="margin-top:4px">🌐 {website_display} &nbsp;|&nbsp; 📞 {phone}{' | 📧 ' + email if email else ''}</div>
        </div>
        <div style="text-align:right; flex-shrink:0; margin-left:1rem;">
            <span class="score-badge {badge_class}">{score}/10</span>
            <div style="color:{urgency_color}; font-size:0.75rem; margin-top:4px; font-weight:600">{lead.get('urgency','')}</div>
            <div style="color:#888; font-size:0.75rem">{service}</div>
        </div>
    </div>
    <div style="margin-top:0.8rem">{signals_html}</div>
    {f'<div class="pitch-box">💬 {pitch}</div>' if pitch else ''}
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# TAB 3: ANALYTICS
# ─────────────────────────────────────────────────────
with tab3:
    if not st.session_state.results:
        st.info("Run the pipeline first.")
    else:
        leads = st.session_state.results.get('qualified_leads', [])
        if not leads:
            st.warning("No qualified leads found.")
        else:
            df = pd.DataFrame(leads)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📊 Score Distribution")
                score_counts = df['lead_score'].value_counts().sort_index()
                st.bar_chart(score_counts)

            with col2:
                st.markdown("#### 🏙️ Leads by City")
                city_counts = df['city'].value_counts()
                st.bar_chart(city_counts)

            col3, col4 = st.columns(2)

            with col3:
                st.markdown("#### 💼 Leads by Business Type")
                biz_counts = df['business_type'].value_counts()
                st.bar_chart(biz_counts)

            with col4:
                st.markdown("#### 🚨 Urgency Breakdown")
                if 'urgency' in df.columns:
                    urgency_counts = df['urgency'].value_counts()
                    st.bar_chart(urgency_counts)

            # Signal heatmap
            st.markdown("#### 📡 Digital Signal Analysis")
            signal_cols = ['has_ssl', 'has_mobile_viewport', 'has_whatsapp',
                          'has_booking_form', 'has_chatbot', 'has_online_payment']
            signal_cols_present = [c for c in signal_cols if c in df.columns]
            if signal_cols_present:
                signal_pct = df[signal_cols_present].mean() * 100
                signal_df = pd.DataFrame({'Signal': signal_cols_present, '% Have It': signal_pct.values})
                st.dataframe(signal_df.set_index('Signal').round(1), width="stretch")

            st.markdown("#### 📋 Full Data Table")
            display_cols = ['company_name', 'city', 'business_type', 'lead_score',
                           'urgency', 'service_opportunity', 'website', 'phone', 'email']
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[display_cols], width="stretch")
