import streamlit as st
import requests
import json

st.set_page_config(page_title="Hyper Sync Playground", layout="wide")

BASE_URL = st.secrets["SUPABASE_BASE_URL"]

# ---------------------------
# SESSION STATE INIT
# ---------------------------
if "token" not in st.session_state:
    st.session_state.token = None

# ---------------------------
# LOGIN SECTION
# ---------------------------
st.title("⚡ Hyper Sync Playground")

with st.expander("🔐 Authentication", expanded=True):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        url = f"{BASE_URL}/auth/v1/token?grant_type=password"

        payload = {
            "email": email,
            "password": password
        }

        res = requests.post(url, json=payload)

        if res.status_code == 200:
            data = res.json()
            st.session_state.token = data.get("access_token")
            st.success("Logged in successfully")
        else:
            st.error(f"Login failed: {res.text}")

# ---------------------------
# APP KEY INPUT
# ---------------------------
st.subheader("🔑 App Configuration")

app_key = st.text_input("App Key")

# ---------------------------
# TRIGGER EVENT
# ---------------------------
st.subheader("🚀 Trigger Event")

col1, col2, col3 = st.columns(3)

with col1:
    channel = st.text_input("Channel", value="my-channel")

with col2:
    event = st.text_input("Event", value="my-event")

with col3:
    message = st.text_input("Message", value="Hello from Streamlit!")

if st.button("Trigger Event"):
    if not st.session_state.token:
        st.error("Login first")
    else:
        url = f"{BASE_URL}/sync-gateway/trigger"

        headers = {
            "Authorization": f"Bearer {st.session_state.token}",
            "Content-Type": "application/json"
        }

        payload = {
            "app_key": app_key,
            "channel": channel,
            "event": event,
            "data": {
                "message": message
            }
        }

        res = requests.post(url, headers=headers, json=payload)

        if res.status_code == 200:
            st.success("Event triggered successfully")
            st.json(res.json())
        else:
            st.error(res.text)

# ---------------------------
# CHANNELS LIST
# ---------------------------
st.subheader("📡 Active Channels")

if st.button("Fetch Channels"):
    if not st.session_state.token:
        st.error("Login first")
    else:
        url = f"{BASE_URL}/sync-gateway/channels"

        headers = {
            "Authorization": f"Bearer {st.session_state.token}"
        }

        res = requests.get(url, headers=headers)

        if res.status_code == 200:
            st.json(res.json())
        else:
            st.error(res.text)

# ---------------------------
# USAGE STATS
# ---------------------------
st.subheader("📊 Usage Stats")

if st.button("Fetch Stats"):
    if not st.session_state.token:
        st.error("Login first")
    else:
        url = f"{BASE_URL}/sync-gateway/stats"

        headers = {
            "Authorization": f"Bearer {st.session_state.token}"
        }

        res = requests.get(url, headers=headers)

        if res.status_code == 200:
            st.json(res.json())
        else:
            st.error(res.text)

# ---------------------------
# CLIENT SDK SNIPPET
# ---------------------------
st.subheader("🧪 Client Test Snippet")

soketi_host = st.text_input("Soketi Host", value="your-vps-ip")

js_code = f"""
import Pusher from 'pusher-js';

const pusher = new Pusher('{app_key}', {{
  wsHost: '{soketi_host}',
  wsPort: 6001,
  forceTLS: false,
  disableStats: true,
  enabledTransports: ['ws', 'wss'],
  cluster: 'mt1',
  authorizer: (channel) => ({{
    authorize: async (socketId, callback) => {{
      const res = await fetch('{BASE_URL}/sync-gateway/auth', {{
        method: 'POST',
        headers: {{
          'Authorization': 'Bearer YOUR_TOKEN',
          'Content-Type': 'application/json',
        }},
        body: JSON.stringify({{
          socket_id: socketId,
          channel_name: channel.name,
          app_key: '{app_key}',
        }}),
      }});
      const data = await res.json();
      callback(null, data);
    }},
  }}),
}});

const channel = pusher.subscribe('{channel}');
channel.bind('{event}', (data) => {{
  console.log('Received:', data);
}});
"""

st.code(js_code, language="javascript")

# ---------------------------
# DEBUG PANEL
# ---------------------------
with st.expander("🛠 Debug Info"):
    st.write("Token:", st.session_state.token)
    st.write("Base URL:", BASE_URL)
