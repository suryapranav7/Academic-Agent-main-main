import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# API CONFIG
API_URL = "http://127.0.0.1:8001" 

def render_outcomes_manager(subject_id: str = "DS203"):
    """
    Page for managing COs and Module Maps.
    Refactored to use Teacher API.
    """
    st.header("🎯 Outcome Based Education (OBE) Manager")
    
    # 1. Subject Selector (Mocked for Pilot)
    selected_subject = st.selectbox("Select Subject", ["Data Structures (DS203)", "Discrete Math (DM201)"], index=0)
    subj_code = "DS203" if "DS203" in selected_subject else "DM201"
    
    # FETCH MODULES DYNAMICALLY
    modules = []
    try:
        mod_resp = requests.get(f"{API_URL}/obe/modules/{subj_code}")
        if mod_resp.status_code == 200:
            mod_data = mod_resp.json().get("data", [])
            # Extract module IDs from the DB response
            modules = [m["module_id"] for m in mod_data]
        else:
            st.error(f"Failed to fetch modules: {mod_resp.status_code}")
            modules = ["DS-U1", "DS-U2", "DS-U3", "DS-Final"] # Fallback
    except Exception as e:
        st.error(f"Connection Error (Modules): {e}")
        modules = ["DS-U1", "DS-U2", "DS-U3", "DS-Final"] # Fallback
    
    tab1, tab2, tab3 = st.tabs(["📝 Define Course Outcomes", "🔗 Map Assessments", "📊 CO-PO Matrix"])
    
    # --- TAB 1: DEFINE COs ---
    with tab1:
        st.subheader(f"Course Outcomes for {subj_code}")
        
        # API FETCH
        existing_cos = []
        try:
            resp = requests.get(f"{API_URL}/obe/cos/{subj_code}")
            if resp.status_code == 200:
                existing_cos = resp.json().get("data", [])
            else:
                st.error(f"API Error: {resp.status_code}")
        except Exception as e:
            st.error(f"Connection Error: {e}")
        
        # Display as Data Editor
        if existing_cos:
            df = pd.DataFrame(existing_cos)
            # Ensure columns exist
            if "co_code" in df.columns and "description" in df.columns:
                df_display = df[["co_code", "description", "co_id"]]
                
                edited_df = st.data_editor(
                    df_display, 
                    key="co_editor",
                    num_rows="dynamic",
                    column_config={
                        "co_code": st.column_config.TextColumn("CO Code", disabled=True), 
                        "description": "Description (Action Verb + Topic)",
                        "co_id": st.column_config.TextColumn("ID", disabled=True, required=False) 
                    }
                )    
        else:
            st.info("No COs defined yet. Please contact admin to seed pilot data.")

    # --- TAB 2: MAP ASSESSMENTS ---
    with tab2:
        st.subheader("Map Modules to COs")
        st.caption("Rule: Max 3 COs per Module.")

        # --- AUTO-MAPPER ---
        col_auto, col_spacer = st.columns([1, 4])
        if col_auto.button("✨ Auto-Map with AI", type="primary"):
            with st.spinner("🤖 Agent is analyzing curriculum alignment..."):
                try:
                    resp = requests.post(f"{API_URL}/obe/mappings/auto-suggest/{subj_code}")
                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        st.session_state[f"suggestions_{subj_code}"] = data
                        
                        # DIRECTLY UPDATE UI STATE
                        # Create lookup for UUID -> Code
                        co_opts_lookup = {co["co_id"]: co["co_code"] for co in existing_cos}
                        updated_count = 0
                        
                        for mod in modules:
                            sug_ids = data.get(mod, [])
                            if sug_ids:
                                # Map UUIDs to Codes
                                sug_codes = [co_opts_lookup[cid] for cid in sug_ids if cid in co_opts_lookup]
                                if sug_codes:
                                    # Set the session state for the widget
                                    st.session_state[f"ms_{mod}"] = sug_codes
                                    updated_count += 1
                        
                        st.toast(f"✅ Auto-Mapped {updated_count} modules! UI Updated.")
                        import time
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Auto-Map Failed: {resp.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")
        
        # Check for suggestions
        suggestions = st.session_state.get(f"suggestions_{subj_code}", {})
        if suggestions:
             st.info("💡 AI Suggestions applied to empty fields. Please review and click 'Update' to save.", icon="🤖")
        
        # 1. Fetch Mappings via API
        mappings = []
        try:
            map_resp = requests.get(f"{API_URL}/obe/mappings/module-co")
            if map_resp.status_code == 200:
                mappings = map_resp.json().get("data", [])
        except:
            mappings = []
            
        # 2. Get Modules (Hardcoded list for pilot)
        modules = ["DS-U1", "DS-U2", "DS-U3", "DS-Final"]
        
        for mod in modules:
            with st.expander(f"📦 {mod}", expanded=True):
                # Find current COs
                current_map = [m for m in mappings if m["module_id"] == mod]
                current_co_ids = [m["co_id"] for m in current_map]
                
                # Multi-select options
                co_opts = {co["co_code"]: co["co_id"] for co in existing_cos}
                
                # Default comes from DB state. 
                # If Auto-Map was clicked, st.session_state for this key is already set.
                # To avoid "default set but also session state set" warning, we initialize state if missing.
                default_opts = [code for code, cid in co_opts.items() if cid in current_co_ids]
                
                if f"ms_{mod}" not in st.session_state:
                    st.session_state[f"ms_{mod}"] = default_opts
                
                selected_codes = st.multiselect(
                    f"Mapped COs for {mod}", 
                    list(co_opts.keys()),
                    # default=default_opts,  <-- REMOVED default to avoid conflict
                    key=f"ms_{mod}"
                )
                
                if st.button(f"Update {mod}", key=f"btn_{mod}"):
                    # API UPDATE
                    selected_ids = [co_opts[code] for code in selected_codes]
                    payload = {"module_id": mod, "co_ids": selected_ids}
                    
                    try:
                        up_resp = requests.post(f"{API_URL}/obe/mappings/module-co", json=payload)
                        if up_resp.status_code == 200:
                            st.toast(f"✅ Updated mappings for {mod}")
                            # time.sleep(1) # Optional delay
                            st.rerun()
                        else:
                            st.error(f"Update failed: {up_resp.text}")
                    except Exception as e:
                        st.error(f"Update failed: {e}")

    # --- TAB 3: CO-PO MATRIX ---
    with tab3:
        st.subheader("CO-PO Mapping Matrix")
        st.caption("Map Course Outcomes to Program Outcomes (Read Only View).")
        
        # 1. Fetch POs via API
        pos = []
        try:
            po_resp = requests.get(f"{API_URL}/obe/pos")
            if po_resp.status_code == 200:
                pos = po_resp.json().get("data", [])
        except:
             st.error("Failed to fetch POs")
             return

        if not existing_cos:
             st.warning("Define Course Outcomes first.")
             return
            
        # 2. Fetch Matrix Mappings
        mapping_list = []
        try:
            mat_resp = requests.get(f"{API_URL}/obe/mappings/co-po")
            if mat_resp.status_code == 200:
                mapping_list = mat_resp.json().get("data", [])
        except:
            pass
            
        mapping_dict = {(m['co_id'], m['po_id']): m['weight'] for m in mapping_list}
        
        # 3. Build Matrix
        matrix_data = []
        for co in existing_cos:
            row = {"CO Name": co['description'], "_co_id": co['co_id']}
            for po in pos:
                val = mapping_dict.get((co['co_id'], po['po_id']), 0)
                row[po['po_id']] = True if val > 0 else False
            matrix_data.append(row)
            
        df_matrix = pd.DataFrame(matrix_data)
        if not df_matrix.empty:
            df_matrix.set_index("_co_id", inplace=True)
            
            col_config = {"CO Name": st.column_config.TextColumn("Course Outcome", disabled=True)}
            for po in pos:
                col_config[po['po_id']] = st.column_config.CheckboxColumn(po['po_id'], help=po['title'], default=False)
                
            st.dataframe(df_matrix, column_config=col_config, hide_index=True, use_container_width=True)
        
        st.divider()
        st.subheader("📖 Reference: Program Outcomes")
        st.dataframe(pd.DataFrame(pos), hide_index=True, use_container_width=True)
