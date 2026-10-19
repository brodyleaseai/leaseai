"""
LeaseAI - Lease Comparison Tool
Compare two leases side-by-side to identify differences
"""

import streamlit as st
from typing import Dict, List, Tuple
from datetime import datetime

def calculate_field_differences(fields_a: List[Dict], fields_b: List[Dict]) -> Dict:
    """
    Compare two sets of extracted fields and identify differences
    
    Returns:
        {
            'identical': [field_names],
            'different': [(field_name, value_a, value_b, difference_type)],
            'only_in_a': [field_names],
            'only_in_b': [field_names]
        }
    """
    # Build dictionaries for easy lookup
    dict_a = {
        f.get('field_name'): f.get('reviewed_value') or f.get('raw_value') or 'NOT FOUND'
        for f in fields_a
    }
    dict_b = {
        f.get('field_name'): f.get('reviewed_value') or f.get('raw_value') or 'NOT FOUND'
        for f in fields_b
    }
    
    all_fields = set(dict_a.keys()) | set(dict_b.keys())
    
    identical = []
    different = []
    only_in_a = []
    only_in_b = []
    
    for field_name in sorted(all_fields):
        value_a = dict_a.get(field_name, 'NOT FOUND')
        value_b = dict_b.get(field_name, 'NOT FOUND')
        
        if field_name not in dict_a:
            only_in_b.append(field_name)
        elif field_name not in dict_b:
            only_in_a.append(field_name)
        elif value_a == value_b:
            identical.append(field_name)
        else:
            # Determine difference type
            diff_type = _classify_difference(field_name, value_a, value_b)
            different.append((field_name, value_a, value_b, diff_type))
    
    return {
        'identical': identical,
        'different': different,
        'only_in_a': only_in_a,
        'only_in_b': only_in_b
    }

def _classify_difference(field_name: str, value_a: str, value_b: str) -> str:
    """Classify the type of difference between two values"""
    field_lower = field_name.lower()
    
    # Date fields
    if 'date' in field_lower:
        try:
            # Try to parse as dates and compare
            from dateutil import parser
            date_a = parser.parse(value_a)
            date_b = parser.parse(value_b)
            diff_days = abs((date_b - date_a).days)
            if diff_days < 30:
                return 'MINOR_DATE_CHANGE'
            elif diff_days < 365:
                return 'MODERATE_DATE_CHANGE'
            else:
                return 'MAJOR_DATE_CHANGE'
        except:
            return 'DATE_FORMAT_CHANGE'
    
    # Rent/monetary fields
    if 'rent' in field_lower or 'amount' in field_lower or 'deposit' in field_lower:
        try:
            # Extract numeric values
            import re
            num_a = float(re.sub(r'[^\d.]', '', value_a))
            num_b = float(re.sub(r'[^\d.]', '', value_b))
            
            if num_a == 0 or num_b == 0:
                return 'VALUE_ADDED_OR_REMOVED'
            
            pct_change = abs((num_b - num_a) / num_a) * 100
            
            if pct_change < 5:
                return 'MINOR_AMOUNT_CHANGE'
            elif pct_change < 20:
                return 'MODERATE_AMOUNT_CHANGE'
            else:
                return 'MAJOR_AMOUNT_CHANGE'
        except:
            return 'AMOUNT_FORMAT_CHANGE'
    
    # Text fields
    if len(value_a) < 50 and len(value_b) < 50:
        return 'TEXT_CHANGE'
    else:
        return 'LONG_TEXT_CHANGE'

def get_difference_badge(diff_type: str) -> str:
    """Return HTML badge for difference type"""
    badges = {
        'MINOR_DATE_CHANGE': '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:4px;font-size:0.7rem;">📅 Minor Date</span>',
        'MODERATE_DATE_CHANGE': '<span style="background:#fed7aa;color:#9a3412;padding:2px 8px;border-radius:4px;font-size:0.7rem;">📅 Date Change</span>',
        'MAJOR_DATE_CHANGE': '<span style="background:#fecaca;color:#991b1b;padding:2px 8px;border-radius:4px;font-size:0.7rem;">📅 Major Date</span>',
        'MINOR_AMOUNT_CHANGE': '<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:4px;font-size:0.7rem;">💰 ~Minor $</span>',
        'MODERATE_AMOUNT_CHANGE': '<span style="background:#bfdbfe;color:#1e3a8a;padding:2px 8px;border-radius:4px;font-size:0.7rem;">💰 ~$ Change</span>',
        'MAJOR_AMOUNT_CHANGE': '<span style="background:#fecaca;color:#991b1b;padding:2px 8px;border-radius:4px;font-size:0.7rem;">💰 Major $</span>',
        'TEXT_CHANGE': '<span style="background:#e0e7ff;color:#3730a3;padding:2px 8px;border-radius:4px;font-size:0.7rem;">📝 Text</span>',
        'LONG_TEXT_CHANGE': '<span style="background:#e0e7ff;color:#3730a3;padding:2px 8px;border-radius:4px;font-size:0.7rem;">📝 Long Text</span>',
        'VALUE_ADDED_OR_REMOVED': '<span style="background:#fecaca;color:#991b1b;padding:2px 8px;border-radius:4px;font-size:0.7rem;">⚠️ Added/Removed</span>',
    }
    return badges.get(diff_type, '<span style="background:#e5e7eb;color:#374151;padding:2px 8px;border-radius:4px;font-size:0.7rem;">Changed</span>')

def render_comparison_view(lease_a: Dict, fields_a: List[Dict], lease_b: Dict, fields_b: List[Dict], supabase_client):
    """Render the lease comparison interface"""
    
    st.markdown("### 🔍 Lease Comparison")
    
    # Lease headers
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style="background:#1a1f2e;border:2px solid #3b82f6;border-radius:10px;padding:15px;margin-bottom:20px;">
            <h4 style="color:#3b82f6;margin:0 0 10px 0;">📄 Lease A</h4>
            <p style="margin:0;color:#e5e7eb;"><strong>{lease_a.get('filename', 'Unknown')}</strong></p>
            <p style="margin:5px 0 0 0;color:#9ca3af;font-size:0.85rem;">{lease_a.get('property_address', '')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background:#1a1f2e;border:2px solid #10b981;border-radius:10px;padding:15px;margin-bottom:20px;">
            <h4 style="color:#10b981;margin:0 0 10px 0;">📄 Lease B</h4>
            <p style="margin:0;color:#e5e7eb;"><strong>{lease_b.get('filename', 'Unknown')}</strong></p>
            <p style="margin:5px 0 0 0;color:#9ca3af;font-size:0.85rem;">{lease_b.get('property_address', '')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Calculate differences
    differences = calculate_field_differences(fields_a, fields_b)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Fields", len(fields_a) + len(fields_b) - len(differences['identical']))
    with col2:
        st.metric("Identical", len(differences['identical']), delta=None, delta_color="off")
    with col3:
        st.metric("Different", len(differences['different']), delta=None, delta_color="inverse")
    with col4:
        differences_pct = round((len(differences['different']) / max(len(fields_a), 1)) * 100)
        st.metric("Difference %", f"{differences_pct}%")
    
    st.markdown("---")
    
    # View selector
    view_mode = st.radio(
        "View Mode:",
        ["🔴 Differences Only", "✅ All Fields", "📊 Summary"],
        horizontal=True
    )
    
    if view_mode == "📊 Summary":
        # Summary view
        st.subheader("📊 Comparison Summary")
        
        if differences['different']:
            st.markdown("#### 🔴 Key Differences")
            
            for field_name, value_a, value_b, diff_type in differences['different'][:10]:
                with st.expander(f"{field_name} {get_difference_badge(diff_type)}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Lease A:**")
                        st.info(value_a if len(value_a) < 100 else value_a[:97] + "...")
                    with col2:
                        st.markdown("**Lease B:**")
                        st.success(value_b if len(value_b) < 100 else value_b[:97] + "...")
            
            if len(differences['different']) > 10:
                st.caption(f"Showing 10 of {len(differences['different'])} differences")
        
        if differences['only_in_a']:
            st.markdown(f"#### 📄 Only in Lease A ({len(differences['only_in_a'])})")
            st.caption(", ".join(differences['only_in_a'][:10]))
        
        if differences['only_in_b']:
            st.markdown(f"#### 📄 Only in Lease B ({len(differences['only_in_b'])})")
            st.caption(", ".join(differences['only_in_b'][:10]))
        
        # Export comparison
        st.markdown("---")
        if st.button("📥 Export Comparison Report", type="primary"):
            st.success("✅ Comparison report exported! (Feature coming soon)")
    
    elif view_mode == "🔴 Differences Only":
        # Show only different fields
        st.subheader("🔴 Field Differences")
        
        if not differences['different']:
            st.success("✅ No differences found! These leases are identical.")
        else:
            for field_name, value_a, value_b, diff_type in differences['different']:
                st.markdown(f"### {field_name} {get_difference_badge(diff_type)}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Lease A:**")
                    st.text_area(
                        "Lease A value",
                        value=value_a,
                        height=100,
                        key=f"a_{field_name}",
                        label_visibility="collapsed"
                    )
                
                with col2:
                    st.markdown("**Lease B:**")
                    st.text_area(
                        "Lease B value",
                        value=value_b,
                        height=100,
                        key=f"b_{field_name}",
                        label_visibility="collapsed"
                    )
                
                st.markdown("---")
    
    else:
        # Show all fields side by side
        st.subheader("✅ All Fields (Side-by-Side)")
        
        # Build combined field list
        dict_a = {f.get('field_name'): f for f in fields_a}
        dict_b = {f.get('field_name'): f for f in fields_b}
        all_field_names = sorted(set(dict_a.keys()) | set(dict_b.keys()))
        
        for field_name in all_field_names:
            field_a = dict_a.get(field_name)
            field_b = dict_b.get(field_name)
            
            value_a = (field_a.get('reviewed_value') or field_a.get('raw_value') or 'NOT FOUND') if field_a else 'NOT FOUND'
            value_b = (field_b.get('reviewed_value') or field_b.get('raw_value') or 'NOT FOUND') if field_b else 'NOT FOUND'
            
            # Check if different
            is_different = value_a != value_b
            
            header = f"{'🔴 ' if is_different else '✅ '}{field_name}"
            
            with st.expander(header, expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Lease A:**")
                    if is_different:
                        st.warning(value_a)
                    else:
                        st.info(value_a)
                
                with col2:
                    st.markdown("**Lease B:**")
                    if is_different:
                        st.warning(value_b)
                    else:
                        st.info(value_b)
    
    # Log this comparison to database
    if st.session_state.get('user_id') and supabase_client:
        try:
            supabase_client.table("lease_comparisons").insert({
                "user_id": st.session_state.get('user_id'),
                "lease_a_id": lease_a['id'],
                "lease_b_id": lease_b['id'],
                "comparison_type": view_mode,
                "fields_compared": list(set(dict_a.keys()) | set(dict_b.keys())),
                "differences_found": len(differences['different'])
            }).execute()
        except:
            pass  # Silently fail if logging doesn't work
