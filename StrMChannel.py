import streamlit as st
from collections import defaultdict

# Global event storage shared by all users/sessions during server runtime
events = defaultdict(lambda: {"messages": [], "participants": set(), "live": True})

if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'current_event' not in st.session_state:
    st.session_state.current_event = None

# Admin username constant
ADMIN_USERNAME = "Vikrant Jadhav (Admin)"

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
        elif event_name in events:
            st.warning("Event already exists! Please join it.")
        else:
            events[event_name] = {"messages": [], "participants": set(), "live": True}
            st.session_state.current_event = event_name  # Fix: Auto-join admin to new event
            st.rerun()
    st.markdown("---")

def user_join_event():
    st.header("Join a Live Event")
    # List only live events
    live_events = [ev for ev, data in events.items() if data.get("live", True)]
    if live_events:
        event_name = st.selectbox("Select event to join", live_events)
        if st.button("Join Event"):
            st.session_state.current_event = event_name
            st.rerun()
    else:
        st.info("No live events available. Please wait for the admin to create one.")

def user_chat():
    st.title(f"Event: {st.session_state.current_event}")
    st.write(f"Logged in as: **{st.session_state.current_user}**")
    event = events[st.session_state.current_event]

    # Add current user as participant
    event["participants"].add(st.session_state.current_user)

    # Display questions and replies
    for idx, (username, msg, reply) in enumerate(event["messages"]):
        st.markdown(f"**{username}**: {msg}")
        if reply:
            st.markdown(f"> Reply: **{ADMIN_USERNAME}**: {reply}")
        st.markdown("---")

    if st.session_state.current_user != ADMIN_USERNAME:
        # User can post questions
        new_msg = st.text_input("Ask your motivational question or request:", key='user_msg')
        if st.button("Send Question"):
            if new_msg.strip():
                event["messages"].append((st.session_state.current_user, new_msg.strip(), None))
                st.rerun()
            else:
                st.warning("Please enter a message")
    else:
        # Admin reply functionality
        st.subheader("Admin: Reply to Questions")
        if len(event["messages"]) == 0:
            st.write("No questions have been asked yet.")
        else:
            selected_index = st.selectbox(
                "Select a question to reply",
                range(len(event["messages"])),
                format_func=lambda i: event["messages"][i][1]
            )
            admin_reply = st.text_area("Write your reply here:", key='admin_reply')
            if st.button("Send Reply to Selected Question"):
                if admin_reply.strip():
                    username, question, _ = event["messages"][selected_index]
                    event["messages"][selected_index] = (username, question, admin_reply.strip())
                    st.rerun()
                else:
                    st.warning("Please enter a reply message")

    if st.button("Leave Event"):
        st.session_state.current_event = None
        st.rerun()

def main():
    if st.session_state.current_user is None:
        login()
        return

    st.sidebar.write(f"Logged in as: **{st.session_state.current_user}**")
    if st.sidebar.button("Logout"):
        st.session_state.current_user = None
        st.session_state.current_event = None
        st.rerun()

    # Only admin can create events
    if st.session_state.current_user == ADMIN_USERNAME:
        admin_create_event()

    if st.session_state.current_event is None:
        user_join_event()
    else:
        user_chat()

if __name__ == "__main__":
    main()
