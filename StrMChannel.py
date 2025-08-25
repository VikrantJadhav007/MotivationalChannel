import streamlit as st
import sqlite3
from sqlite3 import Connection
from typing import List, Tuple

DB_PATH = 'motivation_channel.db'

ADMIN_USERNAME = "Vikrant Jadhav (Admin)"

# Database helper functions

def get_db() -> Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Create events table
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            live INTEGER DEFAULT 1
        )
    ''')
    # Create messages table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            username TEXT,
            message TEXT,
            reply TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(event_id) REFERENCES events(id)
        )
    ''')
    conn.commit()
    conn.close()

def create_event(event_name: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO events (name, live) VALUES (?, 1)', (event_name,))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_live_events() -> List[Tuple[int, str]]:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, name FROM events WHERE live=1 ORDER BY id DESC')
    events = c.fetchall()
    conn.close()
    return events

def get_event_id_by_name(event_name: str) -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM events WHERE name=?', (event_name,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def add_message(event_id: int, username: str, message: str):
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO messages (event_id, username, message) VALUES (?, ?, ?)', (event_id, username, message))
    conn.commit()
    conn.close()

def get_messages(event_id: int) -> List[Tuple[int, str, str, str]]:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, username, message, reply FROM messages WHERE event_id=? ORDER BY timestamp ASC', (event_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_reply(message_id: int, reply: str):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE messages SET reply=? WHERE id=?', (reply, message_id))
    conn.commit()
    conn.close()

def close_event(event_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE events SET live=0 WHERE id=?', (event_id,))
    conn.commit()
    conn.close()

# Streamlit UI functions

def login():
    st.title("Motivational Channel Login")
    username = st.text_input("Enter your username")
    if st.button("Login"):
        if username:
            st.session_state.current_user = username.strip()
            st.rerun()
        else:
            st.warning("Please enter a username")

def admin_create_event():
    st.header("Create a New Event (Admin Only)")
    event_name = st.text_input("Event Name to Create")
    if st.button("Create Event"):
        if not event_name:
            st.warning("Please enter event name")
        else:
            success = create_event(event_name)
            if success:
                st.success(f"Event '{event_name}' created and is live.")
                # Auto join admin to the created event
                st.session_state.current_event = event_name
                st.rerun()
            else:
                st.error("Event name already exists! Choose another.")

def user_join_event():
    st.header("Join a Live Event")
    live_events = get_live_events()
    event_names = [ev[1] for ev in live_events]
    if event_names:
        event_name = st.selectbox("Select event to join", event_names)
        if st.button("Join Event"):
            st.session_state.current_event = event_name
            st.rerun()
    else:
        st.info("No live events available. Please wait for admin to create one.")

def user_chat():
    st.title(f"Event: {st.session_state.current_event}")
    st.write(f"Logged in as: **{st.session_state.current_user}**")

    # Auto-refresh every 5 seconds to fetch new messages
    #st.autorefresh(interval=5 * 1000, key="datarefresh")

    event_id = get_event_id_by_name(st.session_state.current_event)
    if event_id is None:
        st.error("Event not found.")
        if st.button("Back to event selection"):
            st.session_state.current_event = None
        return

    messages = get_messages(event_id)

    # Manual refresh button
    if st.button("Refresh messages"):
        st.rerun()

    # Display messages and replies
    for idx, (msg_id, username, message, reply) in enumerate(messages):
        st.markdown(f"**{username}**: {message}")
        if reply:
            st.markdown(f"> Reply: **{ADMIN_USERNAME}**: {reply}")
        st.markdown("---")

    if st.session_state.current_user != ADMIN_USERNAME:
        new_msg = st.text_input("Ask your motivational question or request:", key='user_msg')
        if st.button("Send Question"):
            if new_msg.strip():
                add_message(event_id, st.session_state.current_user, new_msg.strip())
                st.rerun()
            else:
                st.warning("Please enter a message")
    else:
        st.subheader("Admin: Reply to Questions")
        if not messages:
            st.write("No questions have been asked yet.")
        else:
            selected_index = st.selectbox(
                "Select a question to reply",
                range(len(messages)),
                format_func=lambda i: messages[i][2]
            )
            admin_reply = st.text_area("Write your reply here:", key='admin_reply')
            if st.button("Send Reply to Selected Question"):
                if admin_reply.strip():
                    msg_id = messages[selected_index][0]
                    add_reply(msg_id, admin_reply.strip())
                    st.rerun()
                else:
                    st.warning("Please enter a reply message")

        # Option to close event
        if st.button("Close This Event"):
            close_event(event_id)
            st.success("Event closed.")
            st.session_state.current_event = None
            st.rerun()

    if st.button("Leave Event"):
        st.session_state.current_event = None
        st.rerun()

def main():
    init_db()

    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'current_event' not in st.session_state:
        st.session_state.current_event = None

    if st.session_state.current_user is None:
        login()
        return

    st.sidebar.write(f"Logged in as: **{st.session_state.current_user}**")
    if st.sidebar.button("Logout"):
        st.session_state.current_user = None
        st.session_state.current_event = None
        st.rerun()

    if st.session_state.current_user == ADMIN_USERNAME:
        admin_create_event()

    if st.session_state.current_event is None:
        user_join_event()
    else:
        user_chat()

if __name__ == "__main__":
    main()
