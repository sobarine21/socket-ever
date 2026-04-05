"""
HyperSync Playground — Streamlit App
A full playground for testing the HyperSync real-time infrastructure.

Credentials resolution order:
  1. User-entered values in the sidebar (session state)
  2. st.secrets (Streamlit Cloud / .streamlit/secrets.toml)
  3. Environment variables (for VPS / Docker / Supabase Edge)
"""

import os
import json
import time
import requests
import streamlit as st
from datetime import datetime

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="HyperSync Playground",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Styling
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}
code, pre, .stCodeBlock {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Dark card panels */
.hs-card {
    background: #0f1117;
    border: 1px solid #2a2d3e;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.hs-tag {
    display: inline-block;
    background: #1e2230;
    color: #7dd3fc;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 6px;
    margin-bottom: 4px;
    border: 1px solid #2a4a6b;
}
.success-badge {
    color: #4ade80;
    font-weight: 700;
    font-size: 0.85rem;
}
.error-badge {
    color: #f87171;
    font-weight: 700;
    font-size: 0.85rem;
}
.hs-header {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2rem;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.hs-sub {
    color: #64748b;
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
}
div[data-testid="stSidebarContent"] {
    background: #080a10;
}
.stButton > button {
    border-radius: 8px;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    border: 1px solid #334155;
    transition: all 0.2s;
}
.stButton > button:hover {
    border-color: #38bdf8;
    color: #38bdf8;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Credential helpers
# ─────────────────────────────────────────────
def _secret(section: str, key: str, fallback_env: str) -> str:
    """Read from st.secrets first, then os.environ."""
    try:
        return st.secrets[section][key]
    except Exception:
        return os.environ.get(fallback_env, "")


def get_creds():
    """Return credentials from session state (user-supplied) or defaults."""
    return {
        "traefik_host": st.session_state.get("cfg_traefik_host")
                        or _secret("hypersync", "TRAEFIK_HOST", "TRAEFIK_HOST"),
        "app_id":       st.session_state.get("cfg_app_id")
                        or _secret("hypersync", "DEFAULT_APP_ID", "DEFAULT_APP_ID"),
        "app_key":      st.session_state.get("cfg_app_key")
                        or _secret("hypersync", "DEFAULT_APP_KEY", "DEFAULT_APP_KEY"),
        "app_secret":   st.session_state.get("cfg_app_secret")
                        or _secret("hypersync", "DEFAULT_APP_SECRET", "DEFAULT_APP_SECRET"),
        "supabase_base": _secret("supabase", "FUNCTIONS_BASE", "SUPABASE_FUNCTIONS_BASE")
                         or "https://sglratpoxbdtkroqairj.supabase.co/functions/v1",
    }


# ─────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────
def api_post(url: str, payload: dict, token: str = None, extra_headers: dict = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        return r.status_code, _safe_json(r)
    except requests.exceptions.ConnectionError as e:
        return 0, {"error": f"Connection error: {e}"}
    except Exception as e:
        return 0, {"error": str(e)}


def api_get(url: str, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        return r.status_code, _safe_json(r)
    except Exception as e:
        return 0, {"error": str(e)}


def _safe_json(r):
    try:
        return r.json()
    except Exception:
        return {"raw": r.text}


def log_event(action: str, status_code: int, response: dict):
    if "hs_log" not in st.session_state:
        st.session_state["hs_log"] = []
    st.session_state["hs_log"].insert(0, {
        "ts": datetime.now().strftime("%H:%M:%S"),
        "action": action,
        "status": status_code,
        "response": response,
    })
    # Keep last 50
    st.session_state["hs_log"] = st.session_state["hs_log"][:50]


# ─────────────────────────────────────────────
# Sidebar — Credentials
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ HyperSync")
    st.markdown("---")
    st.markdown("### 🔑 Credentials")
    st.caption("Leave blank to use server defaults (secrets/env).")

    creds = get_creds()  # load defaults first

    st.session_state["cfg_traefik_host"] = st.text_input(
        "Soketi Host (TRAEFIK_HOST)",
        value=st.session_state.get("cfg_traefik_host", creds["traefik_host"]),
        placeholder="soketi.yourdomain.com",
    )
    st.session_state["cfg_app_id"] = st.text_input(
        "App ID",
        value=st.session_state.get("cfg_app_id", creds["app_id"]),
    )
    st.session_state["cfg_app_key"] = st.text_input(
        "App Key",
        value=st.session_state.get("cfg_app_key", creds["app_key"]),
    )
    st.session_state["cfg_app_secret"] = st.text_input(
        "App Secret",
        value=st.session_state.get("cfg_app_secret", creds["app_secret"]),
        type="password",
    )

    st.markdown("---")
    st.markdown("### 🔐 Auth Token")
    st.caption("Sign in to get a Bearer token for API calls.")

    auth_email = st.text_input("Email", key="auth_email")
    auth_pass  = st.text_input("Password", key="auth_pass", type="password")

    if st.button("🔑 Sign In", use_container_width=True):
        creds = get_creds()
        url = f"{creds['supabase_base']}/auth/v1/token?grant_type=password"
        code, data = api_post(url, {"email": auth_email, "password": auth_pass})
        if code == 200 and "access_token" in data:
            st.session_state["bearer_token"] = data["access_token"]
            st.success("✅ Signed in!")
        else:
            st.error(f"Auth failed ({code})")
            st.json(data)

    if st.session_state.get("bearer_token"):
        token_preview = st.session_state["bearer_token"][:20] + "..."
        st.success(f"Token: `{token_preview}`")
        if st.button("🚪 Sign Out", use_container_width=True):
            del st.session_state["bearer_token"]
            st.rerun()
    else:
        st.warning("No token — sign in above.")

    st.markdown("---")
    st.caption("HyperSync Playground v1.0")


# ─────────────────────────────────────────────
# Main Header
# ─────────────────────────────────────────────
st.markdown('<div class="hs-header">⚡ HyperSync Playground</div>', unsafe_allow_html=True)
st.markdown('<div class="hs-sub">Test your real-time infrastructure — trigger events, monitor channels, inspect stats</div>', unsafe_allow_html=True)

# Quick status row
creds = get_creds()
token = st.session_state.get("bearer_token", "")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Soketi Host", creds["traefik_host"] or "⚠ Not set")
with col2:
    st.metric("App Key", (creds["app_key"][:12] + "…") if creds["app_key"] else "⚠ Not set")
with col3:
    st.metric("Auth Status", "✅ Authenticated" if token else "❌ No Token")

st.markdown("---")

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚀 Trigger Event",
    "📡 Active Channels",
    "📊 Usage Stats",
    "🔐 Channel Auth",
    "📋 Event Log",
])

# ══════════════════════════════════════════════
# TAB 1 — Trigger Event
# ══════════════════════════════════════════════
with tab1:
    st.markdown("### Trigger a Real-Time Event")
    st.caption("Sends an event to a channel via the sync-gateway trigger endpoint.")

    col_a, col_b = st.columns(2)
    with col_a:
        channel_name = st.text_input("Channel", value="my-channel", key="trig_channel")
        event_name   = st.text_input("Event Name", value="my-event", key="trig_event")
    with col_b:
        data_str = st.text_area(
            "Event Data (JSON)",
            value='{\n  "message": "Hello from HyperSync!"\n}',
            height=130,
            key="trig_data",
        )

    # Advanced overrides
    with st.expander("⚙ Override App Key for this request"):
        override_key = st.text_input(
            "App Key (leave blank to use sidebar value)",
            key="trig_override_key",
        )

    if st.button("⚡ Trigger Event", type="primary", use_container_width=True):
        if not token:
            st.error("❌ Sign in first (sidebar).")
        else:
            try:
                data_payload = json.loads(data_str)
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
                st.stop()

            used_key = override_key.strip() or creds["app_key"]
            payload = {
                "app_key": used_key,
                "channel": channel_name,
                "event":   event_name,
                "data":    data_payload,
            }
            url = f"{creds['supabase_base']}/sync-gateway/trigger"

            with st.spinner("Triggering…"):
                code, resp = api_post(url, payload, token=token)

            log_event("trigger", code, resp)

            if code == 200:
                st.success(f"✅ Event triggered! Status {code}")
            else:
                st.error(f"❌ Failed — HTTP {code}")

            st.json(resp)

            # Show equivalent curl
            with st.expander("🔧 Equivalent cURL"):
                curl = f"""curl -X POST {url} \\
  -H "Authorization: Bearer <your-token>" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(payload, indent=2)}'"""
                st.code(curl, language="bash")

# ══════════════════════════════════════════════
# TAB 2 — Active Channels
# ══════════════════════════════════════════════
with tab2:
    st.markdown("### Active Channels")
    st.caption("Lists all currently active channels in your Soketi instance.")

    if st.button("🔄 Fetch Channels", use_container_width=True, key="fetch_ch"):
        if not token:
            st.error("❌ Sign in first.")
        else:
            url = f"{creds['supabase_base']}/sync-gateway/channels"
            with st.spinner("Fetching…"):
                code, resp = api_get(url, token)
            log_event("list_channels", code, resp)

            if code == 200:
                st.success(f"✅ HTTP {code}")
                channels = resp if isinstance(resp, list) else resp.get("channels", resp)
                if isinstance(channels, list) and channels:
                    for ch in channels:
                        name = ch if isinstance(ch, str) else ch.get("name", str(ch))
                        subs = ch.get("subscription_count", "?") if isinstance(ch, dict) else "?"
                        st.markdown(f'<span class="hs-tag">📡 {name}</span> `{subs} subscriber(s)`', unsafe_allow_html=True)
                else:
                    st.info("No active channels right now.")
            else:
                st.error(f"❌ HTTP {code}")

            st.json(resp)

# ══════════════════════════════════════════════
# TAB 3 — Usage Stats
# ══════════════════════════════════════════════
with tab3:
    st.markdown("### Usage Statistics")
    st.caption("Shows today's and total event counts.")

    col_r, col_s = st.columns([3, 1])
    with col_s:
        auto_refresh = st.checkbox("Auto-refresh (10s)", key="auto_refresh")

    if st.button("📊 Fetch Stats", use_container_width=True, key="fetch_stats") or auto_refresh:
        if not token:
            st.error("❌ Sign in first.")
        else:
            url = f"{creds['supabase_base']}/sync-gateway/stats"
            with st.spinner("Fetching…"):
                code, resp = api_get(url, token)
            log_event("stats", code, resp)

            if code == 200:
                today = resp.get("today", "N/A")
                total = resp.get("total", "N/A")
                c1, c2 = st.columns(2)
                c1.metric("📅 Events Today", today)
                c2.metric("🌐 Total Events", total)
            else:
                st.error(f"❌ HTTP {code}")
                st.json(resp)

            if auto_refresh:
                time.sleep(10)
                st.rerun()

# ══════════════════════════════════════════════
# TAB 4 — Channel Auth
# ══════════════════════════════════════════════
with tab4:
    st.markdown("### Channel Authorization")
    st.caption("Test the Pusher-compatible private/presence channel auth endpoint.")

    col_x, col_y = st.columns(2)
    with col_x:
        auth_socket_id   = st.text_input("Socket ID", value="1234.5678", key="auth_sid")
        auth_channel     = st.text_input("Channel Name", value="private-my-channel", key="auth_chn")
    with col_y:
        st.info("💡 Socket IDs come from the connected Pusher client. Use any value to test the auth endpoint response.")

    if st.button("🔐 Test Auth", use_container_width=True, key="test_auth"):
        if not token:
            st.error("❌ Sign in first.")
        else:
            url = f"{creds['supabase_base']}/sync-gateway/auth"
            payload = {
                "socket_id":    auth_socket_id,
                "channel_name": auth_channel,
                "app_key":      creds["app_key"],
            }
            with st.spinner("Authenticating…"):
                code, resp = api_post(url, payload, token=token)
            log_event("channel_auth", code, resp)

            if code == 200:
                st.success(f"✅ Auth successful (HTTP {code})")
            else:
                st.error(f"❌ HTTP {code}")
            st.json(resp)

    st.markdown("---")
    st.markdown("#### 📋 Client-Side Pusher Snippet")
    st.caption("Copy this into your frontend. Replace placeholders with your values.")

    host  = creds["traefik_host"] or "soketi.yourdomain.com"
    key   = creds["app_key"] or "<your-app-key>"
    base  = creds["supabase_base"]

    pusher_snippet = f"""import Pusher from 'pusher-js';

const pusher = new Pusher('{key}', {{
  wsHost: '{host}',
  wsPort: 6001,
  forceTLS: false,
  disableStats: true,
  enabledTransports: ['ws', 'wss'],
  cluster: 'mt1',
  authorizer: (channel) => ({{
    authorize: async (socketId, callback) => {{
      const res = await fetch('{base}/sync-gateway/auth', {{
        method: 'POST',
        headers: {{
          'Authorization': 'Bearer <your-token>',
          'Content-Type': 'application/json',
        }},
        body: JSON.stringify({{
          socket_id: socketId,
          channel_name: channel.name,
          app_key: '{key}',
        }}),
      }});
      const data = await res.json();
      callback(null, data);
    }},
  }}),
}});

const channel = pusher.subscribe('my-channel');
channel.bind('my-event', (data) => {{
  console.log('Received:', data);
}});"""

    st.code(pusher_snippet, language="javascript")

# ══════════════════════════════════════════════
# TAB 5 — Event Log
# ══════════════════════════════════════════════
with tab5:
    st.markdown("### Event Log")
    st.caption("All API calls made in this session (newest first).")

    log = st.session_state.get("hs_log", [])
    if not log:
        st.info("No events yet. Use the other tabs to make API calls.")
    else:
        col_cl, _ = st.columns([1, 5])
        with col_cl:
            if st.button("🗑 Clear Log"):
                st.session_state["hs_log"] = []
                st.rerun()

        for entry in log:
            status = entry["status"]
            badge_cls = "success-badge" if 200 <= status < 300 else "error-badge"
            with st.expander(
                f"[{entry['ts']}]  {entry['action'].upper()}  —  HTTP {status}",
                expanded=False,
            ):
                st.json(entry["response"])
