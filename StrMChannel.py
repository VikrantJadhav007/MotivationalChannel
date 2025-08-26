import streamlit as st
import sqlite3
from sqlite3 import Connection
from typing import List, Tuple

DB_PATH = "motivation_channel.db"

ADMIN_USERNAMES = ["Pradeep Parmar (Admin)", "Vikrant Jadhav (Admin)"]

# ---------- Database Helper Functions ----------

def get_db() -> Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            live INTEGER DEFAULT 1
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            username TEXT,
            message TEXT,
            reply TEXT,
            reply_by TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(event_id) REFERENCES events(id)
        )
        """
    )
    conn.commit()
    conn.close()

def create_event(event_name: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO events (name, live) VALUES (?, 1)", (event_name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_live_events() -> List[Tuple[int, str]]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name FROM events WHERE live=1 ORDER BY id DESC")
    events = c.fetchall()
    conn.close()
    return events

def get_event_id_by_name(event_name: str) -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM events WHERE name=?", (event_name,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def add_message(event_id: int, username: str, message: str):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (event_id, username, message) VALUES (?, ?, ?)",
        (event_id, username, message),
    )
    conn.commit()
    conn.close()

def get_messages(event_id: int) -> List[Tuple[int, str, str, str, str]]:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, username, message, reply, reply_by
        FROM messages WHERE event_id=?
        ORDER BY timestamp ASC
        """,
        (event_id,),
    )
    rows = c.fetchall()
    conn.close()
    return rows

def add_reply(message_id: int, reply: str, admin_username: str):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE messages SET reply=?, reply_by=? WHERE id=?", (reply, admin_username, message_id)
    )
    conn.commit()
    conn.close()

def close_event(event_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE events SET live=0 WHERE id=?", (event_id,))
    conn.commit()
    conn.close()

def get_unique_user_count(event_id: int) -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(DISTINCT username) FROM messages WHERE event_id=?", (event_id,)
    )
    count = c.fetchone()[0]
    conn.close()
    return count

# ---------- UI Functions ----------

def login():
    st.title("🎯 Motivational Channel Login")
    st.markdown("Please enter your username below to start:")
    username = st.text_input("", placeholder="Your name")
    login_button = st.button("🔑 Login")
    if login_button:
        if username.strip():
            st.session_state.current_user = username.strip()
            st.success(f"Welcome, {st.session_state.current_user}!")
            st.rerun()
        else:
            st.warning("⚠️ Username cannot be empty")


def show_sidebar():
    st.sidebar.title("User Info")
    st.sidebar.write(f"👤 **{st.session_state.current_user}**")
    role = "Admin" if st.session_state.current_user in ADMIN_USERNAMES else "User"
    st.sidebar.write(f"🔑 Role: **{role}**")

    if st.sidebar.button("🚪 Logout", key="logout"):
        st.session_state.current_user = None
        st.session_state.current_event = None
        st.rerun()

    if role == "Admin":
        st.sidebar.markdown("---")
        st.sidebar.header("🛠 Event Management")
        event_name = st.sidebar.text_input(
            "Create New Event", placeholder="Enter new event name"
        )
        if st.sidebar.button("➕ Create Event"):
            if event_name.strip():
                success = create_event(event_name.strip())
                if success:
                    st.sidebar.success(f"✅ Event '{event_name.strip()}' created!")
                    st.session_state.current_event = event_name.strip()
                    st.rerun()
                else:
                    st.sidebar.error("❌ Event name already exists.")
            else:
                st.sidebar.warning("⚠️ Please enter a valid event name")


def render_chat_bubble(message: str, is_admin: bool, username: str):
    bubble_color = "#E0EFFF" if is_admin else "#DCF8C6"
    align = "right" if is_admin else "left"
    username_style = (
        f'<div style="font-weight:bold; text-align:{align}; color:#0078D7; margin-bottom:4px;">{username}</div>'
        if username
        else ""
    )

    st.markdown(
        f"""
        <div style="max-width:70%; margin:5px 0; text-align:{align};">
            {username_style}
            <div style="
                display:inline-block;
                background-color:{bubble_color};
                padding:12px 16px;
                border-radius:20px;
                box-shadow: 0 1px 1px rgba(0,0,0,0.1);
                font-size:16px;
                white-space: pre-wrap;
                word-wrap: break-word;
            ">
                {message}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def user_chat():
    st.header(f"🎤 Event: {st.session_state.current_event}")

    event_id = get_event_id_by_name(st.session_state.current_event)
    if event_id is None:
        st.error("❌ Event not found or closed.")
        if st.button("🔙 Back to events"):
            st.session_state.current_event = None
            st.rerun()
        return

    messages = get_messages(event_id)
    user_count = get_unique_user_count(event_id)
    st.markdown(f"**Total participants:** {user_count}")
    st.markdown("---")

    # Manual Refresh Chat button
    if st.button("🔄 Refresh Chat"):
        st.rerun()

    # Chat container with fixed max height for scrolling
    st.markdown(
        """
        <style>
        .chat-container {
            max-height: 600px;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 10px;
            background-color: #f9f9f9;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)

    for msg_id, username, message, reply, reply_by in messages:
        render_chat_bubble(message, is_admin=False, username=username)
        if reply:
            render_chat_bubble(reply, is_admin=True, username=reply_by)

        if st.session_state.current_user in ADMIN_USERNAMES and not reply:
            with st.form(key=f"reply_form_{msg_id}", clear_on_submit=True):
                reply_text = st.text_area(
                    "Write your reply here:", key=f"reply_{msg_id}", max_chars=500, height=75
                )
                submitted = st.form_submit_button("Send Reply")
                if submitted:
                    if reply_text.strip():
                        add_reply(msg_id, reply_text.strip(), st.session_state.current_user)
                        st.success("✅ Reply sent.")
                        st.rerun()
                    else:
                        st.warning("⚠️ Please enter reply before sending.")

    st.markdown("</div>", unsafe_allow_html=True)

    # Question input for normal users
    if st.session_state.current_user not in ADMIN_USERNAMES:
        st.markdown("---")
        st.subheader("💬 Ask a Motivational Question")
        with st.form("ask_question_form", clear_on_submit=True):
            question_text = st.text_area("Your question or request:", max_chars=500, height=100)
            send = st.form_submit_button("Send Question")
            if send:
                if question_text.strip():
                    add_message(event_id, st.session_state.current_user, question_text.strip())
                    st.success("✅ Your question has been submitted.")
                    st.rerun()
                else:
                    st.warning("⚠️ Please enter a valid question.")

    # Admin controls
    if st.session_state.current_user in ADMIN_USERNAMES:
        st.markdown("---")
        if st.button("🛑 Close This Event"):
            close_event(event_id)
            st.success("Event closed successfully.")
            st.session_state.current_event = None
            st.rerun()

    # Leave event for all users
    if st.button("↩️ Leave Event"):
        st.session_state.current_event = None
        st.rerun()


def user_join_event():
    st.header("📢 Join a Live Event")
    live_events = get_live_events()
    event_names = [ev[1] for ev in live_events]

    if not event_names:
        st.info("ℹ️ No live events. Please wait for an admin to create one.")
        return

    selected_event = st.selectbox("Select Event", event_names)
    if st.button("👉 Join Event"):
        st.session_state.current_event = selected_event
        st.success(f"Joined event: {selected_event}")
        st.rerun()


def main():
    st.set_page_config(page_title="Motivation Channel", page_icon="🎯", layout="centered")
    init_db()

    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "current_event" not in st.session_state:
        st.session_state.current_event = None

    if not st.session_state.current_user:
        login()
        return

    # Sidebar
    st.sidebar.title("User Info")
    st.sidebar.write(f"👤 **{st.session_state.current_user}**")
    role = "Admin" if st.session_state.current_user in ADMIN_USERNAMES else "User"
    st.sidebar.write(f"🔑 Role: **{role}**")

    if st.sidebar.button("🚪 Logout", key="logout"):
        st.session_state.current_user = None
        st.session_state.current_event = None
        st.rerun()

    # Admin event creation controls in sidebar
    if role == "Admin":
        st.sidebar.markdown("---")
        st.sidebar.header("🛠 Event Management")
        event_name = st.sidebar.text_input(
            "Create New Event", placeholder="Enter new event name"
        )
        if st.sidebar.button("➕ Create Event"):
            if event_name.strip():
                success = create_event(event_name.strip())
                if success:
                    st.sidebar.success(f"✅ Event '{event_name.strip()}' created!")
                    st.session_state.current_event = event_name.strip()
                    st.rerun()
                else:
                    st.sidebar.error("❌ Event name already exists.")
            else:
                st.sidebar.warning("⚠️ Please enter a valid event name")

    # Show join event or chat depending on state
    if not st.session_state.current_event:
        user_join_event()
    else:
        user_chat()


if __name__ == "__main__":
    main()
