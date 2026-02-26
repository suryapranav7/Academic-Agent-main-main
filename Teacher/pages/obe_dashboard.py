import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import requests

# API CONFIG
API_URL = "http://127.0.0.1:8001"

def render_obe_dashboard():
    st.header("📊 OBE Analytics Dashboard")
    
    # 1. Subject Filters
    subject_id = "DS203" 
    st.markdown(f"**Subject:** Data Structures ({subject_id})")
    
    # 2. Key Metrics - Fetch from API
    col1, col2, col3 = st.columns(3)
    
    results = {}
    
    with st.spinner("Fetching Attainment Data..."):
        try:
            # API CALL: CO Attainment
            resp = requests.get(f"{API_URL}/obe/analytics/attainment/co/{subject_id}")
            if resp.status_code == 200:
                results = resp.json().get("data", {})
            else:
                st.error(f"API Calculation Error: {resp.status_code}")
                return
        except Exception as e:
             st.error(f"Connection Failed: {e}")
             return
        
    if not results:
        st.info("No assessment data available for this subject yet.")
        return

    # Average Class Attainment
    avg_attainment = sum([r['avg_attainment'] for r in results.values()]) / len(results) if results else 0
    student_count = list(results.values())[0]['student_count'] if results else 0
    
    col1.metric("Class Average Attainment", f"{avg_attainment:.1f}%")
    col2.metric("Student Samples", student_count)

    st.markdown("---")

    # 3. Visualizations
    
    # Chart 1: CO Attainment Bar Chart
    st.subheader("Course Outcome (CO) Attainment")
    
    co_labels = list(results.keys())
    co_scores = [r['avg_attainment'] for r in results.values()]
    
    fig_co = go.Figure()
    fig_co.add_trace(go.Bar(
        x=co_labels, 
        y=co_scores, 
        name='Actual Attainment',
        marker_color='#4CAF50',
        text=[f"{s:.1f}%" for s in co_scores],
        textposition='auto'
    ))
    
    fig_co.update_layout(yaxis_title="Attainment (%)", yaxis_range=[0, 100], template="plotly_white")
    st.plotly_chart(fig_co, use_container_width=True)
    
    # Chart 2: PO Attainment Radar
    st.markdown("---")
    st.subheader("Program Outcome (PO) Attainment")
    
    po_results = []
    with st.spinner("Calculating PO Impact..."):
        try:
            # API CALL: PO Attainment
            po_resp = requests.get(f"{API_URL}/obe/analytics/attainment/po/{subject_id}")
            if po_resp.status_code == 200:
                po_results = po_resp.json().get("data", [])
        except:
            pass
        
    if po_results:
        po_ids = [p['po_id'] for p in po_results]
        po_vals = [p['attainment'] for p in po_results]
        
        # Close the loop
        if po_ids:
            po_ids_closed = po_ids + [po_ids[0]]
            po_vals_closed = po_vals + [po_vals[0]]
            
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=po_vals_closed,
                theta=po_ids_closed,
                fill='toself',
                name='Class PO Attainment',
                line_color='#2196F3'
            ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=False,
                height=500
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            
            with st.expander("View Data"):
                st.dataframe(po_results)
    else:
        st.info("No PO mappings found or calculation failed.")
