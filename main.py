import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# =====================================================
# CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Nicole - Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# AUTHENTICATION
# =====================================================

# Load authentication config from Streamlit secrets (production) or YAML file (local)
try:
    # Production: Manually build config from Streamlit secrets
    config = {
        'credentials': {
            'usernames': {
                username: {
                    'email': st.secrets['credentials']['usernames'][username]['email'],
                    'name': st.secrets['credentials']['usernames'][username]['name'],
                    'password': st.secrets['credentials']['usernames'][username]['password']
                }
                for username in st.secrets['credentials']['usernames']
            }
        },
        'cookie': {
            'name': st.secrets['cookie']['name'],
            'key': st.secrets['cookie']['key'],
            'expiry_days': st.secrets['cookie']['expiry_days']
        },
        'preauthorized': {
            'emails': list(st.secrets.get('preauthorized', {}).get('emails', []))
        }
    }
except:
    # Local development: Load from YAML file
    with open('auth_config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
        
# Create authenticator object
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Login widget
authenticator.login()

# Get authentication status
name = st.session_state.get("name")
authentication_status = st.session_state.get("authentication_status")
username = st.session_state.get("username")

# Handle authentication states
if authentication_status == False:
    st.error('Username/Password is incorrect')
    st.stop()
    
if authentication_status == None:
    st.warning('Please enter your username and password')
    st.stop()

# =====================================================
# AUTHENTICATED AREA - Dashboard Code Below
# =====================================================

# Logout button in sidebar
with st.sidebar:
    st.write(f'Welcome *{name}*')
    authenticator.logout()
    st.markdown("---")

# =====================================================
# SUPABASE CONNECTION
# =====================================================

# Get credentials from Streamlit secrets (production) or set manually (local)
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    # For local development, replace these with your actual credentials
    SUPABASE_URL = "YOUR_SUPABASE_URL"
    SUPABASE_KEY = "YOUR_SUPABASE_KEY"

@st.cache_resource
def init_supabase() -> Client:
    """Initialize Supabase client"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# =====================================================
# DATA FUNCTIONS
# =====================================================

@st.cache_data(ttl=60)
def get_all_contacts():
    """Get all contacts from Supabase"""
    response = supabase.table('contacts').select('*').order('created_at', desc=True).execute()
    return pd.DataFrame(response.data)

def update_contact(contact_id, updates):
    """Update a contact in Supabase"""
    response = supabase.table('contacts').update(updates).eq('id', contact_id).execute()
    return response

def delete_contact(contact_id):
    """Delete a contact from Supabase"""
    response = supabase.table('contacts').delete().eq('id', contact_id).execute()
    return response

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def get_stats(df):
    """Calculate dashboard statistics"""
    total_users = len(df)
    active_challenges = len(df[df['status'] == 'challenge_running'])
    completed_challenges = len(df[df['status'] == 'challenge_completed'])
    paid_users = len(df[df['status'] == 'paid_member']) if 'status' in df.columns else 0
    
    # Calculate revenue (assuming €9.99 per paid user)
    revenue = paid_users * 9.99
    
    # Conversion rate (completed to paid)
    conversion_rate = (paid_users / completed_challenges * 100) if completed_challenges > 0 else 0
    
    return {
        'total_users': total_users,
        'active_challenges': active_challenges,
        'completed_challenges': completed_challenges,
        'paid_users': paid_users,
        'revenue': revenue,
        'conversion_rate': conversion_rate
    }

def status_color(status):
    """Return color for status badge"""
    colors = {
        'lead_new': '🔵',
        'challenge_running': '🟢',
        'challenge_completed': '🟡',
        'paid_member': '👑'
    }
    return colors.get(status, '⚪')

# =====================================================
# MAIN APP
# =====================================================

st.title("🌿 Nicole - Admin Dashboard")
st.markdown("---")

# Sidebar navigation
with st.sidebar:
    st.image("https://via.placeholder.com/150x150/4CAF50/FFFFFF?text=Nicole", width=150)
    st.title("Navigation")
    page = st.radio(
        "Go to",
        ["📊 Overview", "👥 Users", "📈 Analytics", "⚙️ Settings"]
    )
    
    st.markdown("---")
    st.markdown("### Quick Actions")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    if st.button("📥 Export All Data"):
        df = get_all_contacts()
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"nicole_contacts_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# =====================================================
# PAGE: OVERVIEW
# =====================================================

if page == "📊 Overview":
    st.header("📊 Dashboard Overview")
    
    # Load data
    df = get_all_contacts()
    
    if df.empty:
        st.warning("No contacts found in database.")
    else:
        stats = get_stats(df)
        
        # Stats Cards
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="👥 Total Users",
                value=stats['total_users']
            )
        
        with col2:
            st.metric(
                label="🟢 Active Challenges",
                value=stats['active_challenges']
            )
        
        with col3:
            st.metric(
                label="👑 Paid Members",
                value=stats['paid_users']
            )
        
        st.markdown("---")
        
        # Charts Row 1
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Status Distribution")
            if 'status' in df.columns:
                status_counts = df['status'].value_counts()
                fig = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="Users by Status",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig, width='stretch')
        
        with col2:
            st.subheader("📅 Current Day Distribution")
            if 'current_day' in df.columns:
                day_counts = df['current_day'].value_counts().sort_index()
                fig = px.bar(
                    x=day_counts.index,
                    y=day_counts.values,
                    labels={'x': 'Day', 'y': 'Number of Users'},
                    title="Users by Challenge Day"
                )
                st.plotly_chart(fig, width='stretch')
        
        st.markdown("---")
        
        # Charts Row 2
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Signups Over Time")
            if 'created_at' in df.columns:
                df['date'] = pd.to_datetime(df['created_at']).dt.date
                daily_signups = df.groupby('date').size().reset_index(name='signups')
                fig = px.line(
                    daily_signups,
                    x='date',
                    y='signups',
                    title="Daily Signups",
                    markers=True
                )
                st.plotly_chart(fig, width='stretch')
        
        with col2:
            st.subheader("🎯 Conversion Funnel")
            funnel_data = {
                'Stage': ['Signups', 'Active', 'Completed', 'Paid'],
                'Count': [
                    stats['total_users'],
                    stats['active_challenges'],
                    stats['completed_challenges'],
                    stats['paid_users']
                ]
            }
            fig = go.Figure(go.Funnel(
                y=funnel_data['Stage'],
                x=funnel_data['Count'],
                textinfo="value+percent initial"
            ))
            fig.update_layout(title="User Journey Funnel")
            st.plotly_chart(fig, width='stretch')
        
        # Recent Activity
        st.markdown("---")
        st.subheader("🕐 Recent Activity")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Latest Signups**")
            # Convert created_at to datetime for sorting
            df_sorted = df.copy()
            df_sorted['created_at'] = pd.to_datetime(df_sorted['created_at'])
            recent = df_sorted.nlargest(5, 'created_at')[['first_name', 'email', 'created_at', 'status']]
            for _, row in recent.iterrows():
                status_emoji = status_color(row['status'])
                st.text(f"{status_emoji} {row['first_name']} - {row['email']}")
                st.caption(f"Signed up: {row['created_at']}")
        
        with col2:
            st.markdown("**Users Completing Today**")
            today_completers = df[(df['current_day'] == 8) & (df['status'] == 'challenge_running')]
            if not today_completers.empty:
                for _, row in today_completers.head(5).iterrows():
                    st.text(f"🎉 {row['first_name']} - {row['email']}")
            else:
                st.info("No users completing challenge today")

# =====================================================
# PAGE: USERS
# =====================================================

elif page == "👥 Users":
    st.header("👥 User Management")
    
    df = get_all_contacts()
    
    if df.empty:
        st.warning("No contacts found in database.")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                options=df['status'].unique() if 'status' in df.columns else [],
                default=df['status'].unique() if 'status' in df.columns else []
            )
        
        with col2:
            day_filter = st.multiselect(
                "Filter by Day",
                options=sorted(df['current_day'].unique()) if 'current_day' in df.columns else [],
                default=sorted(df['current_day'].unique()) if 'current_day' in df.columns else []
            )
        
        with col3:
            search = st.text_input("🔍 Search by name/email/phone")
        
        # Apply filters
        filtered_df = df.copy()
        
        if status_filter and 'status' in df.columns:
            filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
        
        if day_filter and 'current_day' in df.columns:
            filtered_df = filtered_df[filtered_df['current_day'].isin(day_filter)]
        
        if search:
            mask = (
                filtered_df['first_name'].str.contains(search, case=False, na=False) |
                filtered_df['email'].str.contains(search, case=False, na=False) |
                filtered_df['phone'].astype(str).str.contains(search, case=False, na=False)
            )
            filtered_df = filtered_df[mask]
        
        st.markdown(f"**Showing {len(filtered_df)} of {len(df)} users**")
        
        # Display users
        for idx, row in filtered_df.iterrows():
            with st.expander(f"{status_color(row['status'])} {row['first_name']} - {row['email']}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**Contact Info**")
                    st.write(f"📧 Email: {row['email']}")
                    st.write(f"📱 Phone: {row['phone']}")
                    st.write(f"📅 Signed up: {row['created_at']}")
                
                with col2:
                    st.write("**Challenge Progress**")
                    st.write(f"📍 Current Day: {row['current_day']}")
                    st.write(f"🎯 Status: {row['status']}")
                    if 'consent_whatsapp' in row:
                        st.write(f"💬 WhatsApp: {'✅' if row['consent_whatsapp'] else '❌'}")
                    if 'consent_email' in row:
                        st.write(f"📧 Email: {'✅' if row['consent_email'] else '❌'}")
                
                with col3:
                    st.write("**Actions**")
                    
                    # Update Status
                    new_status = st.selectbox(
                        "Change Status",
                        options=['lead_new', 'challenge_running', 'challenge_completed', 'paid_member'],
                        index=['lead_new', 'challenge_running', 'challenge_completed', 'paid_member'].index(row['status']),
                        key=f"status_{row['id']}"
                    )
                    
                    # Update Day
                    new_day = st.number_input(
                        "Change Day",
                        min_value=0,
                        max_value=30,
                        value=int(row['current_day']),
                        key=f"day_{row['id']}"
                    )
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("💾 Save", key=f"save_{row['id']}"):
                            updates = {
                                'status': new_status,
                                'current_day': new_day
                            }
                            update_contact(row['id'], updates)
                            st.success("Updated!")
                            st.cache_data.clear()
                            st.rerun()
                    
                    with col_b:
                        if st.button("🗑️ Delete", key=f"delete_{row['id']}"):
                            if st.session_state.get(f'confirm_delete_{row["id"]}'):
                                delete_contact(row['id'])
                                st.success("Deleted!")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.session_state[f'confirm_delete_{row["id"]}'] = True
                                st.warning("Click again to confirm")

# =====================================================
# PAGE: ANALYTICS
# =====================================================

elif page == "📈 Analytics":
    st.header("📈 Analytics")
    
    df = get_all_contacts()
    
    if df.empty:
        st.warning("No contacts found in database.")
    else:
        # Date range selector
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=30)
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now()
            )
        
        # Filter by date range
        if 'created_at' in df.columns:
            df['date'] = pd.to_datetime(df['created_at']).dt.date
            mask = (df['date'] >= start_date) & (df['date'] <= end_date)
            filtered_df = df[mask]
            
            st.markdown(f"**Analyzing {len(filtered_df)} users from {start_date} to {end_date}**")
            st.markdown("---")
            
            # Metrics Row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Signups", len(filtered_df))
            
            with col2:
                avg_day = filtered_df['current_day'].mean() if 'current_day' in filtered_df.columns else 0
                st.metric("Avg Current Day", f"{avg_day:.1f}")
            
            with col3:
                completion_rate = (len(filtered_df[filtered_df['status'] == 'challenge_completed']) / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
                st.metric("Completion Rate", f"{completion_rate:.1f}%")
            
            with col4:
                paid_rate = (len(filtered_df[filtered_df['status'] == 'paid_member']) / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
                st.metric("Conversion Rate", f"{paid_rate:.1f}%")
            
            st.markdown("---")
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📅 Daily Signups Trend")
                daily = filtered_df.groupby('date').size().reset_index(name='count')
                fig = px.area(
                    daily,
                    x='date',
                    y='count',
                    title="Signups per Day"
                )
                st.plotly_chart(fig, width='stretch')
            
            with col2:
                st.subheader("🔄 Status Changes Over Time")
                status_over_time = filtered_df.groupby(['date', 'status']).size().reset_index(name='count')
                fig = px.line(
                    status_over_time,
                    x='date',
                    y='count',
                    color='status',
                    title="Status Distribution Over Time"
                )
                st.plotly_chart(fig, width='stretch')
            

# =====================================================
# PAGE: SETTINGS
# =====================================================

elif page == "⚙️ Settings":
    st.header("⚙️ Settings")
    
    st.subheader("👤 Account")
    st.write(f"**Logged in as:** {name}")
    st.write(f"**Username:** {username}")
    
    st.markdown("---")
    
    st.subheader("🔗 Supabase Connection")
    st.code(f"URL: {SUPABASE_URL}")
    st.info("⚠️ Update credentials in Streamlit Cloud secrets")
    
    st.markdown("---")
    
    st.subheader("📊 Database Info")
    df = get_all_contacts()
    st.write(f"**Total Records:** {len(df)}")
    st.write(f"**Columns:** {', '.join(df.columns)}")
    
    st.markdown("---")
    
    st.subheader("🔧 Maintenance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared!")
    
    with col2:
        if st.button("📥 Export All Data"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"nicole_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

# =====================================================
# FOOTER
# =====================================================

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        🌿 Nicole Challenge Admin Dashboard | Built with Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
