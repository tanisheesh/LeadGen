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
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.now()
if 'filters' not in st.session_state:
    st.session_state.filters = {}
if 'config_submitted' not in st.session_state:
    st.session_state.config_submitted = False
if 'uploaded_config' not in st.session_state:
    st.session_state.uploaded_config = None
if 'show_results_tab' not in st.session_state:
    st.session_state.show_results_tab = False


# ─────────────────────────────────────────────────────
# LOAD CONFIG FROM .ENV OR UPLOADED FILE
# ─────────────────────────────────────────────────────
env_config = get_config()

# Use uploaded config if available and merge with env_config
if st.session_state.uploaded_config:
    for key, value in st.session_state.uploaded_config.items():
        if value:  # Only update if value is not empty
            env_config[key] = value

# ─────────────────────────────────────────────────────
# SIDEBAR — CONFIG UPLOAD
# ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 Configuration")
    
    # Check if config is complete
    has_serpapi = bool(env_config.get('serpapi_key'))
    has_openrouter = bool(env_config.get('openrouter_key'))
    has_hunter = bool(env_config.get('hunter_key'))
    config_ready = has_serpapi and has_openrouter and has_hunter
    
    if not config_ready:
        st.warning("⚠️ Configuration Required")
        st.markdown("Upload your `.env` file to get started")
        
        # .env file upload
        uploaded_env = st.file_uploader(
            "Upload .env file",
            type=['env', 'txt'],
            help="Upload your .env file with API keys",
            key="env_uploader"
        )
        
        if uploaded_env is not None:
            try:
                # Parse .env file
                env_content = uploaded_env.read().decode('utf-8')
                parsed_config = {}
                
                for line in env_content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        parsed_config[key.lower()] = value
                
                # Map to expected keys (support both GROQ_API_KEY and OPENROUTER_KEY)
                temp_config = {
                    'serpapi_key': parsed_config.get('serpapi_key', ''),
                    'openrouter_key': parsed_config.get('groq_api_key', '') or parsed_config.get('openrouter_key', ''),
                    'hunter_key': parsed_config.get('hunter_key', ''),
                    'sheet_id': parsed_config.get('sheet_id', ''),
                    'min_score': int(parsed_config.get('min_score', 7)),
                    'max_concurrent_scrapes': int(parsed_config.get('max_concurrent', 5)),
                }
                
                # Show parsed values
                st.success("✓ .env file parsed successfully!")
                st.markdown("**Found:**")
                st.markdown(f"- SerpAPI: {'✓' if temp_config['serpapi_key'] else '✗'}")
                st.markdown(f"- Groq AI: {'✓' if temp_config['openrouter_key'] else '✗'}")
                st.markdown(f"- Hunter.io: {'✓' if temp_config['hunter_key'] else '✗'}")
                st.markdown(f"- Sheet ID: {'✓' if temp_config['sheet_id'] else '⚠️ Optional'}")
                
            except Exception as e:
                st.error(f"Error parsing .env file: {e}")
                temp_config = None
        else:
            temp_config = None
        
        st.markdown("---")
        
        # Optional: Sheet ID (from .env or manual input)
        st.markdown("#### 📊 Google Sheets (Optional)")
        
        # Show Sheet ID from .env if available
        env_sheet_id = temp_config.get('sheet_id', '') if temp_config else ''
        if env_sheet_id:
            st.info(f"✓ Sheet ID from .env: {env_sheet_id[:20]}...")
            use_env_sheet = st.checkbox("Use Sheet ID from .env", value=True, key="use_env_sheet")
            if use_env_sheet:
                final_sheet_id = env_sheet_id
            else:
                final_sheet_id = st.text_input(
                    "Override Sheet ID",
                    value="",
                    placeholder="1TJE2gs4J19L6FhZ6A0Sh...",
                )
        else:
            final_sheet_id = st.text_input(
                "Sheet ID",
                value="",
                placeholder="1TJE2gs4J19L6FhZ6A0Sh...",
                help="Optional - Leave empty to skip Google Sheets"
            )
        
        # Service Account JSON upload (required if Sheet ID is provided)
        if final_sheet_id:
            st.warning("⚠️ Sheet ID provided - Service Account JSON required!")
            uploaded_json = st.file_uploader(
                "Service Account JSON (Required for Sheets)",
                type=['json'],
                help="Upload service_account.json for Google Sheets access"
            )
        else:
            uploaded_json = st.file_uploader(
                "Service Account JSON (Optional)",
                type=['json'],
                help="Optional - Upload service_account.json for Google Sheets"
            )
        
        service_account_json = ""
        if uploaded_json is not None:
            try:
                service_account_json = uploaded_json.read().decode('utf-8')
                json.loads(service_account_json)  # Validate
                st.success("✓ Valid JSON uploaded")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
                service_account_json = ""
        
        st.markdown("---")
        
        # Submit button
        if st.button("✅ Submit Configuration", type="primary", use_container_width=True):
            if temp_config and temp_config['serpapi_key'] and temp_config['openrouter_key'] and temp_config['hunter_key']:
                # Add Sheet ID (from .env or manual)
                temp_config['sheet_id'] = final_sheet_id
                
                # Add Service Account JSON
                temp_config['sheets_service_account_json'] = service_account_json
                
                # Validate: If Sheet ID provided, JSON must be uploaded
                if final_sheet_id and not service_account_json:
                    st.error("❌ Sheet ID provided but Service Account JSON missing! Upload JSON file or remove Sheet ID.")
                else:
                    st.session_state.uploaded_config = temp_config
                    st.session_state.config_submitted = True
                    st.success("✅ Configuration saved! You can now run the pipeline.")
                    st.rerun()
            else:
                st.error("❌ Please upload .env file with all required keys (SerpAPI, OpenRouter, Hunter.io)")
    
    else:
        # Config is ready - show status
        st.success("✅ Configuration Ready")
        
        with st.expander("📋 View Configuration"):
            st.markdown("**API Keys:**")
            st.markdown(f"- SerpAPI: {'✓ Set' if has_serpapi else '✗'}")
            st.markdown(f"- OpenRouter: {'✓ Set' if has_openrouter else '✗'}")
            st.markdown(f"- Hunter.io: {'✓ Set' if has_hunter else '✗'}")
            
            st.markdown("**Google Sheets:**")
            has_sheet = bool(env_config.get('sheet_id'))
            has_sa = bool(env_config.get('sheets_service_account_json'))
            st.markdown(f"- Sheet ID: {'✓ Set' if has_sheet else '⚠️ Not set'}")
            st.markdown(f"- Service Account: {'✓ Set' if has_sa else '⚠️ Not set'}")
            
            if st.button("🔄 Reset Configuration"):
                st.session_state.uploaded_config = None
                st.session_state.config_submitted = False
                st.rerun()

    st.markdown("---")

    st.markdown("#### ⚙️ Settings")
    min_score = st.slider("Minimum Lead Score", 1, 10, env_config.get('min_score', 7))
    max_concurrent = st.slider("Concurrent Scrapes", 1, 10, env_config.get('max_concurrent_scrapes', 5))

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #555; font-size: 0.85rem; padding: 1rem 0;'>
        <p style='margin: 0;'>LeadGen India v2.0</p>
        <p style='margin: 0.5rem 0 0 0;'>
            Made with <span style='color: #e94560;'>❤️</span> by 
            <a href='https://tanisheesh.is-a.dev/' target='_blank' style='color: #e94560; text-decoration: none;'>Tanish Poddar</a>
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🎯 LeadGen <span class="accent">India</span></h1>
    <p>AI-powered local business lead generation — find, score, and pitch Indian SMBs</p>
</div>
""", unsafe_allow_html=True)

# Import enhancements
from enhancements import (
    apply_advanced_filters, sort_leads, export_to_excel,
    render_advanced_filters, render_analytics_dashboard,
    render_lead_card_enhanced, render_real_time_progress
)

# Auto-switch to Results tab if pipeline just completed
if st.session_state.show_results_tab and st.session_state.results:
    # Show big success message
    st.success("🎉 Lead Generation Complete! Showing results below...")
    st.session_state.show_results_tab = False  # Reset flag
    
    # Force show results directly (skip tabs)
    results = st.session_state.results
    leads = results.get('qualified_leads', [])
    
    # Show quick summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Found", results["total_scraped"])
    with col2:
        st.metric("Qualified Leads", len(leads))
    with col3:
        st.metric("Saved to Sheet", results.get("saved_to_sheet", 0))
    with col4:
        avg = round(sum(l.get('lead_score',0) for l in leads) / len(leads), 1) if leads else 0
        st.metric("Avg Score", f"{avg}/10")
    
    st.markdown("---")
    st.info("👇 Scroll down to see all tabs (Results, Analytics, Settings)")
    st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["🚀 Run Pipeline", "📋 Results", "📈 Analytics", "📚 Documentation"])


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
            # Check if config is ready
            if not env_config.get('serpapi_key'):
                st.error("❌ SerpAPI key required! Upload .env file in sidebar.")
            elif not env_config.get('openrouter_key'):
                st.error("❌ Groq API key required! Upload .env file in sidebar.")
            elif not env_config.get('hunter_key'):
                st.error("❌ Hunter.io key required! Upload .env file in sidebar.")
            elif not st.session_state.queries:
                st.error("❌ Add at least one search query!")
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

        # Progress tracking
        progress_data = {
            'stage': 'Starting...',
            'current': 0,
            'total': 100,
            'message': 'Initializing pipeline...',
            'percentage': 0
        }

        def progress_cb(stage, current, total, message):
            # Calculate overall progress based on stages
            stage_weights = {
                'search': (0, 20),      # 0-20%
                'scrape': (20, 50),     # 20-50%
                'score': (50, 80),      # 50-80%
                'enrich': (80, 90),     # 80-90%
                'save': (90, 100)       # 90-100%
            }
            
            if stage in stage_weights:
                start, end = stage_weights[stage]
                if total > 0:
                    stage_progress = (current / total)
                    overall = start + (stage_progress * (end - start))
                else:
                    overall = start
                
                progress_data['stage'] = stage.upper()
                progress_data['current'] = current
                progress_data['total'] = total
                progress_data['message'] = message
                progress_data['percentage'] = int(overall)

        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from pipeline import run_pipeline

        # Run pipeline
        try:
            with progress_container:
                # Progress UI elements
                progress_bar = st.progress(0)
                status_text = st.empty()
                stage_text = st.empty()
                
                # Copy session state values to local variables (for thread safety)
                queries_to_run = st.session_state.queries.copy()
                
                # Start pipeline in background
                import threading
                result_holder = {'result': None, 'error': None}
                
                def run_async_pipeline():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(run_pipeline(
                            config,
                            queries=queries_to_run,
                            progress_callback=progress_cb,
                            min_score=min_score,
                            max_concurrent_scrapes=max_concurrent,
                        ))
                        result_holder['result'] = result
                    except Exception as e:
                        result_holder['error'] = str(e)
                
                thread = threading.Thread(target=run_async_pipeline)
                thread.start()
                
                # Update UI while pipeline runs
                while thread.is_alive():
                    progress_bar.progress(progress_data['percentage'] / 100)
                    status_text.markdown(f"**{progress_data['stage']}** ({progress_data['current']}/{progress_data['total']}) — {progress_data['percentage']}%")
                    stage_text.caption(progress_data['message'])
                    time.sleep(0.5)
                
                thread.join()
                
                # Check for errors
                if result_holder['error']:
                    raise Exception(result_holder['error'])
                
                result = result_holder['result']
                
                # Complete!
                progress_bar.progress(1.0)
                status_text.markdown("**COMPLETE** — 100%")
                
                st.session_state.results = result
                st.session_state.running = False
                st.session_state.show_results_tab = True  # Flag to show results

                st.success(f"✅ Pipeline Complete! Found **{len(result['qualified_leads'])}** qualified leads.")
                st.info("🔄 Refreshing to show results...")
                time.sleep(1)
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

        # Advanced Filters
        col_filter, col_sort, col_export = st.columns([2, 1, 1])
        
        with col_filter:
            with st.expander("🔍 Advanced Filters", expanded=False):
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    cities = sorted(set(l.get('city', '') for l in leads if l.get('city')))
                    filter_city = st.multiselect("City", cities)
                    filter_score = st.slider("Min Score", 1, 10, 7)
                with fc2:
                    biztypes = sorted(set(l.get('business_type', '') for l in leads if l.get('business_type')))
                    filter_biz = st.multiselect("Business Type", biztypes)
                    filter_urgency = st.multiselect("Urgency", ["HIGH", "MEDIUM", "LOW"])
                with fc3:
                    filter_rating = st.slider("Min Rating", 0.0, 5.0, 3.5, 0.5)
                    filter_reviews = st.number_input("Min Reviews", 0, 1000, 10)
                
                must_have_website = st.checkbox("Must have website")
                must_have_whatsapp = st.checkbox("Must have WhatsApp")
        
        with col_sort:
            sort_by = st.selectbox("Sort by", [
                "Lead Score (High to Low)",
                "Google Rating (High to Low)",
                "Reviews (Most to Least)",
                "Urgency (High to Low)",
            ])
        
        with col_export:
            st.markdown("#### Export")
            if leads:
                # CSV Export
                df = pd.DataFrame(leads)
                csv = df.to_csv(index=False).encode()
                st.download_button("📥 CSV", csv, "leads.csv", "text/csv", use_container_width=True)
                
                # Excel Export
                excel_data = export_to_excel(leads)
                st.download_button("📊 Excel", excel_data, "leads.xlsx", 
                                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 use_container_width=True)

        # Apply filters
        filtered = leads
        if filter_city:
            filtered = [l for l in filtered if l.get('city') in filter_city]
        if filter_biz:
            filtered = [l for l in filtered if l.get('business_type') in filter_biz]
        if filter_urgency:
            filtered = [l for l in filtered if l.get('urgency') in filter_urgency]
        filtered = [l for l in filtered if l.get('lead_score', 0) >= filter_score]
        filtered = [l for l in filtered if (l.get('google_rating') or 0) >= filter_rating]
        filtered = [l for l in filtered if (l.get('google_reviews') or 0) >= filter_reviews]
        if must_have_website:
            filtered = [l for l in filtered if l.get('website') or l.get('raw_url')]
        if must_have_whatsapp:
            filtered = [l for l in filtered if l.get('has_whatsapp')]
        
        # Apply sorting
        filtered = sort_leads(filtered, sort_by)

        st.caption(f"Showing {len(filtered)} of {len(leads)} leads")
        st.markdown("---")

        # Lead cards with enhanced features
        for idx, lead in enumerate(filtered):
            render_lead_card_enhanced(lead, idx)


# ─────────────────────────────────────────────────────
# TAB 3: ANALYTICS
# ─────────────────────────────────────────────────────
with tab3:
    if not st.session_state.results:
        st.info("Run the pipeline first to see analytics.")
    else:
        leads = st.session_state.results.get('qualified_leads', [])
        render_analytics_dashboard(leads)


# ─────────────────────────────────────────────────────
# TAB 4: DOCUMENTATION
# ─────────────────────────────────────────────────────
with tab4:
    st.markdown("### 📚 Complete Documentation")
    st.caption("Everything you need to know about LeadGen India")
    
    # Create sub-tabs for different documentation sections
    doc_tab1, doc_tab2, doc_tab3, doc_tab4, doc_tab5 = st.tabs([
        "🔑 API Keys Setup",
        "📊 Google Sheets",
        "🎯 Features Guide",
        "💡 Tips & Tricks",
        "❓ FAQ"
    ])
    
    # ═══════════════════════════════════════════════════
    # API KEYS SETUP
    # ═══════════════════════════════════════════════════
    with doc_tab1:
        st.markdown("## 🔑 How to Get API Keys")
        st.markdown("---")
        
        # SerpAPI
        st.markdown("### 1️⃣ SerpAPI (Required)")
        st.markdown("**What it does:** Fetches business data from Google Maps")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
            **Steps to get API key:**
            1. Go to [serpapi.com](https://serpapi.com/)
            2. Click "Register" (top right)
            3. Sign up with email or Google
            4. Verify your email
            5. Go to Dashboard → API Key
            6. Copy your API key
            
            **Free Tier:**
            - 100 searches per month
            - No credit card required
            - Perfect for testing
            
            **Pricing:**
            - $50/month for 5,000 searches
            - $75/month for 10,000 searches
            """)
        with col2:
            st.info("💡 **Tip:** Start with free tier to test the system")
        
        st.markdown("---")
        
        # Groq AI
        st.markdown("### 2️⃣ Groq AI (Required)")
        st.markdown("**What it does:** AI-powered lead scoring and pitch generation")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
            **Steps to get API key:**
            1. Go to [console.groq.com](https://console.groq.com/)
            2. Click "Sign Up" → Sign up with Google/GitHub
            3. Verify your email
            4. Go to "API Keys" section
            5. Click "Create API Key"
            6. Give it a name (e.g., "LeadGen India")
            7. Copy the key (starts with `gsk_`)
            
            **Free Tier:**
            - 100% FREE forever!
            - No credit card required
            - 30 requests per minute
            - 14,400 requests per day
            - More than enough for lead generation
            
            **Model Used:**
            - Llama 3.3 70B Versatile
            - Super fast (10x faster than others!)
            - High quality scoring
            - Perfect for lead generation
            """)
        with col2:
            st.success("✅ **Best Choice:** FREE + FAST + RELIABLE!")
        
        st.markdown("---")
        # Hunter.io
        st.markdown("### 3️⃣ Hunter.io (Required)")
        st.markdown("**What it does:** Finds email addresses for businesses")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
            **Steps to get API key:**
            1. Go to [hunter.io](https://hunter.io/)
            2. Click "Sign up free"
            3. Verify your email
            4. Go to Dashboard → API
            5. Copy your API key
            
            **Free Tier:**
            - 25 searches per month
            - 50 email verifications
            - No credit card required
            
            **Pricing:**
            - $49/month for 500 searches
            - $99/month for 1,000 searches
            """)
        with col2:
            st.warning("⚠️ **Note:** Free tier is limited but good for testing")
        
        st.markdown("---")
        
        # How to use
        st.markdown("### 📝 How to Add Keys to App")
        st.markdown("""
        **Option 1: Upload .env file (Recommended)**
        1. Create a file named `.env`
        2. Add your keys:
        ```
        SERPAPI_KEY=your_serpapi_key_here
        GROQ_API_KEY=your_groq_api_key_here
        HUNTER_KEY=your_hunter_key_here
        ```
        3. Upload in sidebar → "Upload .env file"
        4. Click "Submit Configuration"
        
        **Option 2: Streamlit Cloud Secrets**
        - If deployed on Streamlit Cloud
        - Go to App Settings → Secrets
        - Add keys in TOML format
        """)
    
    # ═══════════════════════════════════════════════════
    # GOOGLE SHEETS SETUP
    # ═══════════════════════════════════════════════════
    with doc_tab2:
        st.markdown("## 📊 Google Sheets Integration")
        st.markdown("---")
        
        st.info("ℹ️ **Google Sheets is OPTIONAL** - You can download leads as CSV/Excel without it")
        
        st.markdown("### Why Use Google Sheets?")
        st.markdown("""
        ✅ **Automatic saving** - Leads saved directly to cloud  
        ✅ **Team collaboration** - Share with team members  
        ✅ **Deduplication** - Prevents duplicate leads  
        ✅ **Track status** - Add notes, tags, follow-up dates  
        ✅ **Always accessible** - Access from anywhere  
        """)
        
        st.markdown("---")
        
        st.markdown("### 📋 Step-by-Step Setup")
        
        # Step 1
        with st.expander("**Step 1: Create Google Sheet**", expanded=True):
            st.markdown("""
            1. Go to [sheets.google.com](https://sheets.google.com/)
            2. Click "+ Blank" to create new sheet
            3. Name it (e.g., "LeadGen India - Leads")
            4. Copy the Sheet ID from URL:
            
            ```
            https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit
            ```
            
            Example:
            ```
            https://docs.google.com/spreadsheets/d/1TJE2gs4J19L6FhZ6A0Sh1DlsVfTEklrAd3OKd5KxWYY/edit
            ```
            
            Sheet ID = `1TJE2gs4J19L6FhZ6A0Sh1DlsVfTEklrAd3OKd5KxWYY`
            """)
        
        # Step 2
        with st.expander("**Step 2: Create Service Account**"):
            st.markdown("""
            **What is a Service Account?**
            - A special Google account for apps (not humans)
            - Allows the app to access your sheet
            - More secure than using your personal account
            
            **Steps:**
            1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
            2. Create new project:
               - Click "Select a project" (top left)
               - Click "New Project"
               - Name: "LeadGen India"
               - Click "Create"
            
            3. Enable APIs:
               - Go to "APIs & Services" → "Library"
               - Search "Google Sheets API" → Enable
               - Search "Google Drive API" → Enable
            
            4. Create Service Account:
               - Go to "IAM & Admin" → "Service Accounts"
               - Click "Create Service Account"
               - Name: "leadgen-sa"
               - Click "Create and Continue"
               - Skip role assignment → Click "Continue"
               - Click "Done"
            
            5. Create JSON Key:
               - Click on the service account you created
               - Go to "Keys" tab
               - Click "Add Key" → "Create New Key"
               - Choose "JSON" format
               - Click "Create"
               - JSON file will download automatically
            """)
        
        # Step 3
        with st.expander("**Step 3: Share Sheet with Service Account**"):
            st.markdown("""
            **IMPORTANT:** This step is required for the app to access your sheet!
            
            1. Open your JSON file (downloaded in Step 2)
            2. Find the `client_email` field:
            ```json
            {
              "client_email": "leadgen-sa@project-id.iam.gserviceaccount.com"
            }
            ```
            
            3. Copy that email address
            
            4. Open your Google Sheet
            
            5. Click "Share" button (top right)
            
            6. Paste the service account email
            
            7. Give "Editor" access
            
            8. Uncheck "Notify people" (it's a bot, not a person!)
            
            9. Click "Share"
            
            ✅ Done! The app can now access your sheet.
            """)
        
        # Step 4
        with st.expander("**Step 4: Add to App**"):
            st.markdown("""
            **Option 1: Via .env file**
            ```
            SHEET_ID=your_sheet_id_here
            ```
            Then upload JSON file in sidebar.
            
            **Option 2: Manual input**
            - Enter Sheet ID in sidebar
            - Upload JSON file in sidebar
            - Click "Submit Configuration"
            """)
        
        st.markdown("---")
        
        st.markdown("### 📋 Sheet Structure")
        st.markdown("The app automatically creates these columns:")
        
        st.code("""
Company Name | Website | Phone | Email | Contact Name | City | Address | Country
Business Type | Google Rating | Google Reviews | Lead Score | Urgency | Deal Size
Service Opportunity | Gaps Found | Reasoning | Recommended Pitch
Has WhatsApp | Has Booking | Has SSL | Mobile Optimized | Has Payment | Has Chatbot
Tech Stack | Copyright Year | Source | Date Added | Tags | Notes | Status | Last Contact
        """, language="text")
        
        st.markdown("""
        **Key Columns:**
        - **Lead Score** (1-10): Overall quality score
        - **Urgency** (HIGH/MEDIUM/LOW): Priority level
        - **Service Opportunity**: What service to pitch
        - **Recommended Pitch**: AI-generated pitch in Hindi/English
        - **Tags**: Add custom tags (Hot Lead, Follow-up, etc.)
        - **Notes**: Your notes about the lead
        - **Status**: New, Contacted, Demo Scheduled, etc.
        - **Last Contact**: When you last reached out
        """)
        
        st.markdown("---")
        
        st.markdown("### 🔄 Deduplication")
        st.markdown("""
        The app automatically prevents duplicates:
        - Checks company name + phone number
        - If already exists in sheet → Skips
        - If new → Adds to sheet
        
        This means you can run the pipeline multiple times without worrying about duplicates!
        """)
    
    # ═══════════════════════════════════════════════════
    # FEATURES GUIDE
    # ═══════════════════════════════════════════════════
    with doc_tab3:
        st.markdown("## 🎯 Features Guide")
        st.markdown("---")
        
        # Search & Scrape
        st.markdown("### 🔍 Search & Scrape")
        st.markdown("""
        **What it does:**
        - Searches Google Maps for businesses
        - Extracts: Name, phone, website, rating, reviews, address
        - Scrapes websites for technical details
        
        **How to use:**
        1. Go to "Run Pipeline" tab
        2. Add business type + city combinations
        3. Use Quick Presets for common industries
        4. Click "Start Lead Generation"
        
        **Search Query Tips:**
        - ✅ Good: "dental clinic" + "Mumbai"
        - ✅ Good: "yoga studio" + "Bangalore"
        - ❌ Bad: "business" + "India" (too generic)
        - ❌ Bad: "Dr. Sharma's Clinic" (too specific)
        """)
        
        st.markdown("---")
        
        # Lead Scoring
        st.markdown("### 🎯 Lead Scoring System")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Rule-Based Scoring (1-10)**
            
            Automatic scoring based on:
            - ✗ No website: **10/10** (highest priority!)
            - ✗ Social media only: **9/10**
            - ✗ No SSL certificate: **+2 points**
            - ✗ Not mobile optimized: **+2 points**
            - ✗ No WhatsApp: **+1.5 points**
            - ✗ No booking system: **+1.5 points**
            - ✗ No online payment: **+1 point**
            - ✗ No chatbot: **+1 point**
            """)
        
        with col2:
            st.markdown("""
            **AI Scoring (1-10)**
            
            Google Gemini analyzes:
            - Website content quality
            - Digital maturity level
            - Service opportunities
            - Urgency assessment
            - Generates personalized pitch
            
            **Final Score:**
            - Average of rule-based + AI score
            - Minimum 7/10 to qualify (configurable)
            """)
        
        st.markdown("---")
        
        # Filters
        st.markdown("### 🔍 Advanced Filters")
        st.markdown("""
        **Available in Results tab:**
        
        **By Score & Urgency:**
        - Min Lead Score (1-10)
        - Urgency (HIGH/MEDIUM/LOW)
        
        **By Business:**
        - City (multi-select)
        - Business Type (multi-select)
        
        **By Quality:**
        - Min Google Rating (0-5 stars)
        - Min Reviews count
        - Must have website
        - Must have WhatsApp
        
        **Sorting:**
        - Lead Score (High to Low)
        - Google Rating (High to Low)
        - Reviews (Most to Least)
        - Urgency (High to Low)
        """)
        
        st.markdown("---")
        
        # Export
        st.markdown("### 📥 Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **CSV Export**
            - Simple format
            - All lead data
            - Opens in Excel/Sheets
            - Good for basic use
            """)
        
        with col2:
            st.markdown("""
            **Excel Export**
            - Multi-sheet workbook
            - Summary sheet
            - City breakdown
            - Formatted & styled
            - Best for analysis
            """)
        
        st.markdown("---")
        
        # Analytics
        st.markdown("### 📈 Analytics Dashboard")
        st.markdown("""
        **Key Metrics:**
        - Total Leads Found
        - Average Lead Score
        - High Urgency Count
        - Businesses Without Website
        - Average Google Rating
        
        **Charts:**
        1. **Score Distribution** - Histogram showing lead quality
        2. **Urgency Breakdown** - Pie chart of HIGH/MEDIUM/LOW
        3. **Top 10 Cities** - Bar chart of leads by city
        4. **Business Types** - Distribution of industries
        
        **Use Cases:**
        - Identify best cities for targeting
        - Understand lead quality distribution
        - Plan outreach strategy
        - Report to team/clients
        """)
        
        st.markdown("---")
        
        # Lead Cards
        st.markdown("### 💼 Lead Card Actions")
        st.markdown("""
        Each lead card has action buttons:
        
        **📞 Call**
        - Shows phone number
        - Click to copy
        
        **📧 Email**
        - Shows email address (if found)
        - Generates mailto: link
        
        **📋 Copy Pitch**
        - Copies AI-generated pitch
        - Ready to paste in WhatsApp/Email
        
        **✏️ Notes**
        - Add custom notes
        - Add tags (Hot Lead, Follow-up, etc.)
        - Track status
        - Save for later reference
        """)
    
    # ═══════════════════════════════════════════════════
    # TIPS & TRICKS
    # ═══════════════════════════════════════════════════
    with doc_tab4:
        st.markdown("## 💡 Tips & Tricks")
        st.markdown("---")
        
        st.markdown("### 🎯 Getting Better Leads")
        st.markdown("""
        **1. Target Specific Neighborhoods**
        - Instead of: "gym" + "Mumbai"
        - Try: "gym" + "Bandra Mumbai"
        - Result: More targeted, higher quality leads
        
        **2. Use Descriptive Keywords**
        - Instead of: "clinic"
        - Try: "dental clinic" or "skin clinic"
        - Result: More relevant businesses
        
        **3. Target New Businesses**
        - Add "new" keyword: "new yoga studio"
        - Result: Businesses more likely to need services
        
        **4. Focus on Budget Segments**
        - "affordable gym", "premium spa", "budget hotel"
        - Result: Businesses matching your service pricing
        
        **5. Use Industry-Specific Terms**
        - "coaching institute" vs "tuition center"
        - "ca coaching" vs "commerce coaching"
        - Result: More precise targeting
        """)
        
        st.markdown("---")
        
        st.markdown("### 📞 Outreach Best Practices")
        st.markdown("""
        **1. Prioritize by Score**
        - Start with 9-10/10 scores
        - These have highest conversion potential
        
        **2. Personalize Your Pitch**
        - Use the AI-generated pitch as base
        - Add specific details about their business
        - Mention their Google rating/reviews
        
        **3. Multi-Channel Approach**
        - Call first (highest response rate)
        - Follow up with WhatsApp
        - Send email with details
        
        **4. Best Time to Call**
        - Avoid lunch hours (1-2 PM)
        - Best: 10-11 AM or 4-5 PM
        - Avoid Sundays for most businesses
        
        **5. Track Everything**
        - Use Notes field in lead cards
        - Add tags: "Called", "Interested", "Follow-up"
        - Update Status regularly
        """)
        
        st.markdown("---")
        
        st.markdown("### 💰 Cost Optimization")
        st.markdown("""
        **SerpAPI (Most Expensive)**
        - Free tier: 100 searches/month
        - Each query = 1 search
        - Tip: Combine multiple business types in one city
        - Example: Run 5 queries for 5 cities = 25 searches
        
        **Groq AI (100% FREE!)**
        - Completely FREE forever
        - No credit card needed
        - 14,400 requests per day
        - Unlimited leads!
        
        **Hunter.io (Limited Free)**
        - Free tier: 25 searches/month
        - Only used if website exists
        - Tip: Focus on businesses with websites
        
        **Total Cost Example:**
        - 100 searches/month (free SerpAPI)
        - ~500 leads found
        - ~100 qualified (score ≥ 7)
        - Cost: $0 (using free tiers!)
        """)
        
        st.markdown("---")
        
        st.markdown("### 🚀 Advanced Usage")
        st.markdown("""
        **1. Weekly Automation**
        - Set up cron job (see cron_job.py)
        - Runs automatically every week
        - Fresh leads delivered to your sheet
        
        **2. Team Collaboration**
        - Share Google Sheet with team
        - Assign leads using Tags
        - Track who contacted whom
        
        **3. CRM Integration**
        - Export to Excel
        - Import into your CRM
        - Or use Google Sheets as lightweight CRM
        
        **4. A/B Testing**
        - Try different search queries
        - Compare lead quality by city
        - Optimize based on conversion rates
        
        **5. Niche Targeting**
        - Combine filters for laser focus
        - Example: "High urgency + No website + 4.5+ rating"
        - Result: Best leads for your service
        """)
        
        st.markdown("---")
        
        st.markdown("### ⚙️ Understanding Settings")
        st.markdown("""
        **Concurrent Scrapes - What is it?**
        
        When the pipeline runs, it needs to check many websites. "Concurrent" means how many websites to check at the same time (in parallel).
        
        **Example:**
        - **Concurrent = 1**: Check websites one by one (slow but safe)
          - Website 1 → Wait 5 sec → Website 2 → Wait 5 sec → Website 3
          - Total: 15 seconds for 3 websites
        
        - **Concurrent = 5** (default): Check 5 websites at once (fast!)
          - Websites 1,2,3,4,5 → All at same time → Wait 5 sec → All done
          - Total: 5 seconds for 5 websites
        
        - **Concurrent = 10**: Check 10 websites at once (very fast!)
          - Even faster but might hit rate limits
        
        **When to Change:**
        
        ✅ **Increase to 10+** if:
        - You want faster results
        - You have fast internet
        - You're not hitting rate limits
        
        ⚠️ **Decrease to 1-3** if:
        - Getting rate limit errors
        - Internet is slow
        - System is struggling
        
        💡 **Default (5) is perfect for most users!**
        
        **Min Lead Score - What is it?**
        
        Only leads with score ≥ this value will be saved.
        
        - **Score = 7** (default): Good quality leads
        - **Score = 8**: High quality only
        - **Score = 6**: More leads but lower quality
        
        💡 **Tip:** Start with 7, adjust based on results
        """)
        
        st.markdown("---")
        
    # ═══════════════════════════════════════════════════
    # FAQ
    # ═══════════════════════════════════════════════════
    with doc_tab5:
        st.markdown("## ❓ Frequently Asked Questions")
        st.markdown("---")
        
        with st.expander("**Q: How accurate is the lead scoring?**"):
            st.markdown("""
            **A:** Very accurate! The system uses:
            - Rule-based scoring (100% accurate for technical signals)
            - AI scoring (Google Gemini analyzes website content)
            - Combined score gives balanced assessment
            
            Typical accuracy: 85-90% for identifying businesses that need services.
            """)
        
        with st.expander("**Q: Why are some leads appearing twice?**"):
            st.markdown("""
            **A:** This shouldn't happen! The system has deduplication at multiple levels:
            - During scraping (by company name)
            - Before saving to sheets (by name + phone)
            - In results display (by name + phone)
            
            If you see duplicates, try:
            1. Clear browser cache
            2. Refresh the page
            3. Check if they're actually different businesses with similar names
            """)
        
        with st.expander("**Q: Can I use this without Google Sheets?**"):
            st.markdown("""
            **A:** Yes! Google Sheets is completely optional.
            
            You can:
            - Download leads as CSV
            - Download leads as Excel
            - Use the dashboard to view leads
            - Copy data manually
            
            Sheets is only needed if you want automatic cloud saving and team collaboration.
            """)
        
        with st.expander("**Q: How many leads can I generate per month?**"):
            st.markdown("""
            **A:** Depends on your API limits:
            
            **Free Tier:**
            - SerpAPI: 100 searches = ~2,000 raw leads
            - After filtering: ~200-400 qualified leads
            
            **Paid Tier ($50/month SerpAPI):**
            - 5,000 searches = ~100,000 raw leads
            - After filtering: ~10,000-20,000 qualified leads
            
            Most users find 200-400 qualified leads/month is more than enough!
            """)
        
        with st.expander("**Q: What if a business doesn't have a website?**"):
            st.markdown("""
            **A:** That's actually the BEST lead!
            
            - Scored 10/10 (highest priority)
            - Marked as HIGH urgency
            - Perfect target for website development services
            - AI generates pitch specifically for this
            
            These businesses are most likely to convert.
            """)
        
        with st.expander("**Q: Can I customize the AI pitch?**"):
            st.markdown("""
            **A:** The AI pitch is generated automatically, but you can:
            
            1. Use it as a template
            2. Copy and edit before sending
            3. Add specific details about their business
            4. Translate to local language if needed
            
            The pitch is designed to be a starting point, not final copy.
            """)
        
        with st.expander("**Q: How do I handle API rate limits?**"):
            st.markdown("""
            **A:** The app has built-in rate limiting:
            
            - Max concurrent scrapes: 5 (configurable)
            - Delays between requests
            - Automatic retry on failures
            
            If you hit limits:
            1. Reduce concurrent scrapes in settings
            2. Run smaller batches
            3. Upgrade your API plan
            4. Wait for rate limit reset (usually 24 hours)
            """)
        
        with st.expander("**Q: Is my data secure?**"):
            st.markdown("""
            **A:** Yes! Security measures:
            
            - API keys stored in .env (not in code)
            - Service account JSON never committed to git
            - All API calls over HTTPS
            - Google Sheets access via service account only
            - No data stored on our servers (runs locally)
            
            Your data is as secure as your Google account.
            """)
        
        with st.expander("**Q: Can I run this on Streamlit Cloud?**"):
            st.markdown("""
            **A:** Yes! Deployment steps:
            
            1. Push code to GitHub (without .env!)
            2. Connect to Streamlit Cloud
            3. Add secrets in app settings
            4. Deploy
            
            Or use the .env upload feature in the app itself!
            """)
        
        with st.expander("**Q: What if I get an error?**"):
            st.markdown("""
            **A:** Common errors and fixes:
            
            **"SerpAPI error 404"**
            - Check your API key is correct
            - Verify you haven't exceeded free tier
            
            **"AI API error 404"**
            - Check Groq API key is correct
            - Verify you have internet connection
            - Try running test_groq.py to verify key
            
            **"Sheet access error"**
            - Verify sheet is shared with service account email
            - Check Sheet ID is correct
            - Verify service account JSON is valid
            
            **"Configuration Required"**
            - Upload .env file with all required keys
            - Or enter keys manually in sidebar
            """)
        
        st.markdown("---")
        
        st.markdown("### 📞 Need More Help?")
        st.info("""
        **Still have questions?**
        
        - Check the other documentation tabs
        - Review the README.md file
        - Check error messages carefully
        - Try the test scripts (test_simple_sheets.py)
        """)


# ─────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #555; font-size: 0.9rem; padding: 2rem 0 1rem 0;'>
    <p style='margin: 0; font-size: 1rem;'>LeadGen India v2.0</p>
    <p style='margin: 0.8rem 0 0 0;'>
        Made with <span style='color: #e94560; font-size: 1.1rem;'>❤️</span> by 
        <a href='https://tanisheesh.is-a.dev/' target='_blank' 
           style='color: #e94560; text-decoration: none; font-weight: 600; transition: opacity 0.2s;'
           onmouseover='this.style.opacity="0.7"' 
           onmouseout='this.style.opacity="1"'>
            Tanish Poddar
        </a>
    </p>
</div>
""", unsafe_allow_html=True)
