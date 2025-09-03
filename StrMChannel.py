import streamlit as st
import sqlite3
from sqlite3 import Connection
from typing import List, Tuple, Optional
import re

DB_PATH = "motivation_channel.db"

ADMIN_USERNAMES = ["Pradeep Parmar (Admin)", "Vikrant Jadhav (Admin)"]

# ---------- Database Helper Functions ----------

def get_db() -> Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Users: name and unique valid mobile
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL UNIQUE
        )
        """
    )
    # Courses for motivational content
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE
        )
        """
    )
    # User interests in courses (unique user-course pair)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_course_interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, course_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(course_id) REFERENCES courses(id)
        )
        """
    )
    # Events linked optionally to courses (course_id nullable)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            course_id INTEGER,
            live INTEGER DEFAULT 1,
            FOREIGN KEY(course_id) REFERENCES courses(id)
        )
        """
    )
    # Messages linked to events
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            reply TEXT,
            reply_by TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(event_id) REFERENCES events(id)
        )
        """
    )
    conn.commit()
    conn.close()

def is_valid_mobile(mobile: str) -> bool:
    return bool(re.fullmatch(r"\d{10}", mobile))

def add_user(name: str, mobile: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (name, mobile) VALUES (?, ?)", (name.strip(), mobile.strip()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_mobile(mobile: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name FROM users WHERE mobile=?", (mobile.strip(),))
    user = c.fetchone()
    conn.close()
    return user

def add_course(title: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO courses (title) VALUES (?)", (title.strip(),))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def remove_course(course_id: int) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM user_course_interests WHERE course_id=?", (course_id,))
        c.execute("DELETE FROM events WHERE course_id=?", (course_id,))
        c.execute("DELETE FROM courses WHERE id=?", (course_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_all_courses() -> List[Tuple[int, str]]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, title FROM courses ORDER BY title ASC")
    courses = c.fetchall()
    conn.close()
    return courses

def count_interest_for_course(course_id: int) -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM user_course_interests WHERE course_id=?", (course_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def add_user_interest(user_id: int, course_id: int) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO user_course_interests (user_id, course_id) VALUES (?, ?)", (user_id, course_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_interests_for_course(course_id: int) -> List[Tuple[str, str]]:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """
        SELECT u.name, u.mobile FROM user_course_interests i
        JOIN users u ON i.user_id = u.id
        WHERE i.course_id=?
        ORDER BY i.timestamp DESC
        """,
        (course_id,),
    )
    users = c.fetchall()
    conn.close()
    return users

def create_event(event_name: str, course_id: Optional[int] = None) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO events (name, course_id, live) VALUES (?, ?, 1)", (event_name.strip(), course_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_live_events() -> List[Tuple[int, str, Optional[int]]]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, course_id FROM events WHERE live=1 ORDER BY id DESC")
    events = c.fetchall()
    conn.close()
    return events

def get_live_events_for_user(user_id: int) -> List[Tuple[int, str, Optional[int]]]:
    conn = get_db()
    c = conn.cursor()
    # Retrieve events linked to user interested courses OR events with no course (general)
    c.execute(
        """
        SELECT DISTINCT e.id, e.name, e.course_id FROM events e
        LEFT JOIN user_course_interests i ON e.course_id = i.course_id
        WHERE e.live=1 AND (i.user_id=? OR e.course_id IS NULL)
        ORDER BY e.id DESC
        """,
        (user_id,),
    )
    events = c.fetchall()
    conn.close()
    return events

def get_event_id_by_name(event_name: str) -> Optional[int]:
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
    st.title("🎯 Motivational Channel Registration/Login")
    st.markdown("Please enter your name and mobile number to proceed.")
    name = st.text_input("Name", placeholder="Your full name")
    mobile = st.text_input("Mobile Number", placeholder="10 digit mobile number")
    login_button = st.button("🔑 Register / Login")
    if login_button:
        if not name.strip():
            st.warning("⚠️ Name cannot be empty")
            return
        if not is_valid_mobile(mobile.strip()):
            st.warning("⚠️ Please enter a valid 10-digit mobile number")
            return
        user = get_user_by_mobile(mobile.strip())
        if user:
            user_id, user_name = user
            if user_name != name.strip():
                st.warning("⚠️ Mobile already registered with a different name.")
                return
        else:
            success = add_user(name.strip(), mobile.strip())
            if not success:
                st.error("❌ Registration failed. Mobile number might be already registered.")
                return
        st.session_state.current_user = name.strip()
        st.session_state.current_mobile = mobile.strip()
        st.rerun()

def show_sidebar():
    st.sidebar.title("User Info")
    st.sidebar.write(f"👤 **{st.session_state.current_user}**")
    st.sidebar.write(f"📱 {st.session_state.current_mobile}")
    is_admin = st.session_state.current_user in ADMIN_USERNAMES
    role = "Admin" if is_admin else "User"
    st.sidebar.write(f"🔑 Role: **{role}**")

    if st.sidebar.button("🚪 Logout", key="logout"):
        st.session_state.clear()
        st.rerun()

    if is_admin:
        admin_course_management()
        admin_event_creation()

def admin_course_management():
    st.sidebar.markdown("---")
    st.sidebar.header("🛠 Course Management")

    new_course = st.sidebar.text_input("Add New Course", placeholder="Course title", key="new_course")
    if st.sidebar.button("➕ Add Course"):
        if new_course.strip():
            success = add_course(new_course.strip())
            if success:
                st.sidebar.success(f"✅ Course '{new_course.strip()}' added!")
                st.rerun()
            else:
                st.sidebar.error("❌ Course already exists.")
        else:
            st.sidebar.warning("⚠️ Please enter a valid course title")

    courses = get_all_courses()
    if courses:
        st.sidebar.markdown("### Manage Courses & Interests")
        for course_id, title in courses:
            interest_count = count_interest_for_course(course_id)
            col1, col2, col3 = st.sidebar.columns([3, 1, 1])
            col1.write(title)
            if col2.button(f"{interest_count}", key=f"user_count_{course_id}"):
                st.session_state.clicked_course_id = course_id
                st.session_state.show_interest_modal = True
                st.rerun()
            if col3.button("❌ Remove", key=f"remove_{course_id}"):
                st.session_state.course_to_remove = course_id
                st.rerun()

def admin_event_creation():
    st.sidebar.markdown("---")
    st.sidebar.header("🚀 Create New Event")

    event_name = st.sidebar.text_input("Event Name", placeholder="New event name", key="new_event")
    courses = get_all_courses()
    course_options = ["None (General Event)"] + [c[1] for c in courses]
    selected_course_title = st.sidebar.selectbox("Link Event to Course (optional)", course_options, key="event_course_select")

    if st.sidebar.button("➕ Create Event"):
        if not event_name.strip():
            st.sidebar.warning("⚠️ Please enter an event name")
        else:
            course_id = None
            if selected_course_title != "None (General Event)":
                course_id = next((cid for cid, title in courses if title == selected_course_title), None)
            success = create_event(event_name.strip(), course_id)
            if success:
                st.sidebar.success(f"✅ Event '{event_name.strip()}' created!")
                st.rerun()
            else:
                st.sidebar.error("❌ Event name already exists.")

def show_interest_modal():
    if "show_interest_modal" in st.session_state and st.session_state.show_interest_modal:
        course_id = st.session_state.clicked_course_id
        courses = get_all_courses()
        course_title = next((t for cid, t in courses if cid == course_id), "Unknown Course")
        users = get_interests_for_course(course_id)

        st.markdown("---")
        st.markdown(f"### Users Interested in '{course_title}'")
        if users:
            for uname, umobile in users:
                st.write(f"- {uname} 📱 {umobile}")
        else:
            st.info("No users have shown interest in this course yet.")

        if st.button("Close"):
            st.session_state.show_interest_modal = False
            st.rerun()

def confirm_remove_course():
    if "course_to_remove" in st.session_state:
        course_id = st.session_state.course_to_remove
        courses = get_all_courses()
        course_title = next((t for cid, t in courses if cid == course_id), None)
        if course_title:
            st.sidebar.warning(f"Are you sure you want to remove course '{course_title}'? This will delete related interests and events too.")
            col_yes, col_no = st.sidebar.columns(2)
            if col_yes.button("✔ Confirm Remove", key="confirm_remove_yes"):
                success = remove_course(course_id)
                if success:
                    st.sidebar.success(f"Removed course '{course_title}'.")
                else:
                    st.sidebar.error("Failed to remove course.")
                del st.session_state.course_to_remove
                st.rerun()
            if col_no.button("✖ Cancel Remove", key="confirm_remove_no"):
                del st.session_state.course_to_remove
                st.rerun()

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

    if st.session_state.current_user not in ADMIN_USERNAMES:
        st.markdown("---")
        st.subheader("💬 Ask a Motivational Question")
        new_question_col, refresh_col = st.columns([4, 1])

        with new_question_col:
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

        with refresh_col:
            if st.button("🔄 Refresh Chat"):
                st.rerun()

    if st.session_state.current_user in ADMIN_USERNAMES:
        st.markdown("---")
        admin_col1, admin_col2 = st.columns([1, 1])
        with admin_col1:
            if st.button("🛑 Close This Event"):
                close_event(event_id)
                st.success("Event closed successfully.")
                st.session_state.current_event = None
                st.rerun()
        with admin_col2:
            if st.button("🔄 Refresh Chat"):
                st.rerun()

    st.markdown("---")
    if st.button("↩️ Leave Event"):
        st.session_state.current_event = None
        st.rerun()

def user_show_courses_and_interest():
    st.header("📚 Motivational Courses")
    courses = get_all_courses()
    if not courses:
        st.info("ℹ️ No motivational courses added yet. Please check later.")
        return

    user = get_user_by_mobile(st.session_state.current_mobile)
    if not user:
        st.error("User not found in DB. Please logout and login again.")
        return
    user_id = user[0]

    course_titles = [c[1] for c in courses]
    selected_course = st.selectbox("Select a course to show interest", course_titles)
    if selected_course:
        course_id = [c[0] for c in courses if c[1] == selected_course][0]
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "SELECT 1 FROM user_course_interests WHERE user_id=? AND course_id=?",
            (user_id, course_id),
        )
        already_interested = c.fetchone() is not None
        conn.close()

        if already_interested:
            st.success(f"✅ You have already shown interest in '{selected_course}'.")
        else:
            if st.button(f"🌟 Show Interest in '{selected_course}'"):
                success = add_user_interest(user_id, course_id)
                if success:
                    st.success(f"🎉 Interest shown for course '{selected_course}'.")
                else:
                    st.warning(f"⚠️ Could not show interest. Maybe already registered.")

def user_join_event():
    st.header("📢 Join a Live Event")

    user = get_user_by_mobile(st.session_state.current_mobile)
    if not user:
        st.error("User not found. Please logout and login again.")
        return
    user_id = user[0]

    live_events = get_live_events_for_user(user_id)
    if not live_events:
        st.info("ℹ️ No live events available for your interests or general. Please wait for admin to create one.")
        return
    event_names = [ev[1] for ev in live_events]

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
    if "current_mobile" not in st.session_state:
        st.session_state.current_mobile = None

    if not st.session_state.current_user:
        login()
        return

    show_sidebar()

    if st.session_state.get("show_interest_modal", False):
        show_interest_modal()

    confirm_remove_course()

    if not st.session_state.current_event:
        if st.session_state.current_user in ADMIN_USERNAMES:
            st.write("### Admin Dashboard")
            st.write("Use the sidebar to manage courses, create events, view user interests.")
            user_join_event()  # Admin can join all events
        else:
            user_show_courses_and_interest()
            st.markdown("---")
            user_join_event()
    else:
        user_chat()

if __name__ == "__main__":
    main()
