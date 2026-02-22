"""
Enhanced features for LeadGen India Dashboard
Features: Advanced filters, analytics, export, real-time progress
"""
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import io

def apply_advanced_filters(leads, filters):
    """Apply advanced filtering to leads"""
    filtered = leads.copy()
    
    # Score range
    if 'score_range' in filters:
        min_score, max_score = filters['score_range']
        filtered = [l for l in filtered if min_score <= l.get('lead_score', 0) <= max_score]
    
    # Urgency
    if filters.get('urgency'):
        filtered = [l for l in filtered if l.get('urgency') in filters['urgency']]
    
    # Google rating
    if 'min_rating' in filters:
        filtered = [l for l in filtered if (l.get('google_rating') or 0) >= filters['min_rating']]
    
    # Min reviews
    if 'min_reviews' in filters:
        filtered = [l for l in filtered if (l.get('google_reviews') or 0) >= filters['min_reviews']]
    
    # Must have website
    if filters.get('must_have_website'):
        filtered = [l for l in filtered if l.get('website') or l.get('raw_url')]
    
    # Must have WhatsApp
    if filters.get('must_have_whatsapp'):
        filtered = [l for l in filtered if l.get('has_whatsapp')]
    
    # Deal size
    if filters.get('deal_size'):
        filtered = [l for l in filtered if l.get('estimated_deal_size') in filters['deal_size']]
    
    # City filter
    if filters.get('cities'):
        filtered = [l for l in filtered if l.get('city') in filters['cities']]
    
    # Business type filter
    if filters.get('business_types'):
        filtered = [l for l in filtered if l.get('business_type') in filters['business_types']]
    
    return filtered


def sort_leads(leads, sort_by):
    """Sort leads by specified criteria"""
    if sort_by == "Lead Score (High to Low)":
        return sorted(leads, key=lambda x: x.get('lead_score', 0), reverse=True)
    elif sort_by == "Google Rating (High to Low)":
        return sorted(leads, key=lambda x: x.get('google_rating', 0), reverse=True)
    elif sort_by == "Reviews (Most to Least)":
        return sorted(leads, key=lambda x: x.get('google_reviews', 0), reverse=True)
    elif sort_by == "Urgency (High to Low)":
        urgency_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        return sorted(leads, key=lambda x: urgency_order.get(x.get('urgency', 'LOW'), 0), reverse=True)
    elif sort_by == "Date Added (Newest First)":
        return sorted(leads, key=lambda x: x.get('date_added', ''), reverse=True)
    return leads


def export_to_excel(leads):
    """Export leads to Excel with multiple sheets"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Main leads sheet
        df = pd.DataFrame(leads)
        df.to_excel(writer, sheet_name='Leads', index=False)
        
        # Summary sheet
        summary = {
            'Total Leads': len(leads),
            'Avg Score': round(df['lead_score'].mean(), 2) if 'lead_score' in df else 0,
            'High Urgency': len([l for l in leads if l.get('urgency') == 'HIGH']),
            'With Website': len([l for l in leads if l.get('website')]),
            'With Email': len([l for l in leads if l.get('email')]),
        }
        pd.DataFrame([summary]).to_excel(writer, sheet_name='Summary', index=False)
        
        # By city
        if 'city' in df.columns:
            city_stats = df.groupby('city').size().reset_index(name='count')
            city_stats.to_excel(writer, sheet_name='By City', index=False)
    
    return output.getvalue()


def render_advanced_filters():
    """Render advanced filter sidebar"""
    with st.sidebar:
        st.markdown("### 🔍 Advanced Filters")
        
        filters = {}
        
        # Score range
        filters['score_range'] = st.slider("Lead Score Range", 1, 10, (7, 10))
        
        # Urgency
        filters['urgency'] = st.multiselect("Urgency", ["HIGH", "MEDIUM", "LOW"], default=["HIGH", "MEDIUM"])
        
        # Google rating
        filters['min_rating'] = st.slider("Min Google Rating", 0.0, 5.0, 3.5, 0.5)
        
        # Min reviews
        filters['min_reviews'] = st.number_input("Min Reviews", 0, 1000, 10, 5)
        
        # Digital signals
        filters['must_have_website'] = st.checkbox("Must have website")
        filters['must_have_whatsapp'] = st.checkbox("Must have WhatsApp")
        
        # Deal size
        filters['deal_size'] = st.multiselect("Deal Size", ["small", "medium", "large"])
        
        return filters


def render_analytics_dashboard(leads):
    """Render analytics dashboard"""
    if not leads:
        st.info("No data to display. Run the pipeline first.")
        return
    
    df = pd.DataFrame(leads)
    
    st.markdown("### 📊 Performance Analytics")
    
    # Key metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Leads", len(leads))
    with col2:
        avg_score = round(df['lead_score'].mean(), 1) if 'lead_score' in df else 0
        st.metric("Avg Score", f"{avg_score}/10")
    with col3:
        high_urgency = len([l for l in leads if l.get('urgency') == 'HIGH'])
        st.metric("High Urgency", high_urgency)
    with col4:
        with_email = len([l for l in leads if l.get('email')])
        st.metric("With Email", with_email)
    with col5:
        conversion_rate = round((high_urgency / len(leads)) * 100, 1) if leads else 0
        st.metric("Hot Lead %", f"{conversion_rate}%")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏙️ Leads by City")
        if 'city' in df.columns:
            city_counts = df['city'].value_counts()
            st.bar_chart(city_counts)
    
    with col2:
        st.markdown("#### 💼 Leads by Business Type")
        if 'business_type' in df.columns:
            biz_counts = df['business_type'].value_counts().head(10)
            st.bar_chart(biz_counts)
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("#### 📊 Score Distribution")
        if 'lead_score' in df.columns:
            score_counts = df['lead_score'].value_counts().sort_index()
            st.bar_chart(score_counts)
    
    with col4:
        st.markdown("#### 🚨 Urgency Breakdown")
        if 'urgency' in df.columns:
            urgency_counts = df['urgency'].value_counts()
            st.bar_chart(urgency_counts)


def render_lead_card_enhanced(lead, idx):
    """Render enhanced lead card with actions"""
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
    
    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📞 Call", key=f"call_{idx}"):
            st.write(f"☎️ {phone}")
    with col2:
        if email and st.button("📧 Email", key=f"email_{idx}"):
            st.code(f"mailto:{email}")
    with col3:
        if st.button("📋 Copy Pitch", key=f"pitch_{idx}"):
            st.code(pitch)
    with col4:
        with st.expander("✏️ Notes"):
            notes = st.text_area("Add notes", key=f"notes_{idx}", height=100)
            tags = st.multiselect("Tags", ["Hot Lead", "Follow-up", "Demo Scheduled", "Not Interested"], key=f"tags_{idx}")
            if st.button("💾 Save", key=f"save_{idx}"):
                st.success("Notes saved!")


def render_real_time_progress(stage, current, total, message):
    """Render real-time progress updates"""
    progress_pct = (current / total * 100) if total > 0 else 0
    
    stage_emoji = {
        'search': '🔍',
        'scrape': '🌐',
        'score': '🎯',
        'enrich': '📧',
        'save': '💾'
    }
    
    st.markdown(f"### {stage_emoji.get(stage, '⚡')} {stage.upper()}")
    st.progress(progress_pct / 100)
    st.caption(f"{current}/{total} — {message}")
    
    # Estimated time
    if current > 0 and current < total:
        rate = current / ((datetime.now() - st.session_state.start_time).seconds + 1)
        remaining = (total - current) / rate if rate > 0 else 0
        st.caption(f"⏱️ Est. {int(remaining)}s remaining")
