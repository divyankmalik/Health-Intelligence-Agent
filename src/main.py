# Entry point for HIA (Health Insights Agent) — a Streamlit app that analyzes
# blood test PDFs using AI and supports follow-up chat via RAG.
import streamlit as st
from auth.session_manager import SessionManager
from components.auth_pages import show_login_page
from components.sidebar import show_sidebar
from components.analysis_form import show_analysis_form
from components.footer import show_footer
from config.app_config import APP_NAME, APP_TAGLINE, APP_DESCRIPTION, APP_ICON
from services.ai_service import get_chat_response

# Must be the first Streamlit command
st.set_page_config(
    page_title="HIA - Health Insights Agent", page_icon="🩺", layout="wide"
)

# Initialize session state
SessionManager.init_session()

# Hide all Streamlit form-related elements
st.markdown(
    """
    <style>
        /* Hide form submission helper text */
        div[data-testid="InputInstructions"] > span:nth-child(1) {
            visibility: hidden;
        }
    </style>
""",
    unsafe_allow_html=True,
)


def show_welcome_screen():
    # Shown when the user is logged in but hasn't selected or created a session yet.
    st.markdown(
        f"""
        <div style='text-align: center; padding: 50px;'>
            <h1>{APP_ICON} {APP_NAME}</h1>
            <h3>{APP_DESCRIPTION}</h3>
            <p style='font-size: 1.2em; color: #666;'>{APP_TAGLINE}</p>
            <p>Start by creating a new analysis session</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Center the button using a 2-3-2 column layout
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        if st.button(
            "➕ Create New Analysis Session", use_container_width=True, type="primary"
        ):
            # Creates a row in the chat_sessions Supabase table and stores it in session_state
            success, session = SessionManager.create_chat_session()
            if success:
                st.session_state.current_session = session
                st.rerun()
            else:
                st.error("Failed to create session")


def show_chat_history():
    # Fetch all messages for the active session from Supabase, ordered by created_at.
    # Returns the full list (including system messages) so handle_chat_input can
    # search it for the stored report text.
    success, messages = st.session_state.auth_service.get_session_messages(
        st.session_state.current_session["id"]
    )

    if success:
        for msg in messages:
            # Skip system messages (they contain report text metadata)
            if msg.get("role") == "system":
                continue
            # user messages shown in blue (st.info), AI responses in green (st.success)
            if msg["role"] == "user":
                st.info(msg["content"])
            else:
                st.success(msg["content"])
        return messages
    return []


def handle_chat_input(messages):
    # `messages` is passed in so we can search it for the stored report text
    # without an extra Supabase round-trip.

    # := (walrus operator) — only enters the block if the user actually submitted a question
    if prompt := st.chat_input("Ask a follow-up question about the report..."):

        # Show the question immediately so the UI feels responsive before the AI replies
        st.info(prompt)

        # Persist the user's question to Supabase so it appears in history on next load
        st.session_state.auth_service.save_chat_message(
            st.session_state.current_session["id"], prompt, role="user"
        )

        # --- Two-layer lookup for the original PDF text ---
        # The AI needs this as context to answer questions about the report.

        # Layer 1: session state (fast, in-memory) — available if no page refresh has happened
        context_text = st.session_state.get("current_report_text", "")

        # Layer 2: scan the messages list for the hidden system message that stores the PDF text.
        # Needed after a page refresh because Streamlit wipes session_state on reload.
        if not context_text and messages:
            for msg in messages:
                if msg.get("role") == "system" and "__REPORT_TEXT__" in msg.get(
                    "content", ""
                ):
                    content = msg.get("content", "")

                    # The PDF text is wrapped between __REPORT_TEXT__ and __END_REPORT_TEXT__ markers
                    start_idx = content.find("__REPORT_TEXT__\n") + len(
                        "__REPORT_TEXT__\n"
                    )
                    end_idx = content.find("\n__END_REPORT_TEXT__")

                    if start_idx > len("__REPORT_TEXT__\n") - 1 and end_idx > start_idx:
                        context_text = content[start_idx:end_idx]
                        # Cache it back into session state so subsequent questions don't scan again
                        st.session_state.current_report_text = context_text
                        break

        with st.spinner("Thinking..."):
            # Send question + PDF context + full chat history to the RAG pipeline
            response = get_chat_response(prompt, context_text, messages)

            # Show the AI response in a green box
            st.success(response)

            # Persist the AI response to Supabase
            st.session_state.auth_service.save_chat_message(
                st.session_state.current_session["id"], response, role="assistant"
            )

            # Rerun so show_chat_history() re-fetches and re-renders the full conversation in order
            st.rerun()


def show_user_greeting():
    if st.session_state.user:
        # Get name from user data, fallback to email if name is empty
        display_name = st.session_state.user.get("name") or st.session_state.user.get(
            "email", ""
        )
        st.markdown(
            f"""
            <div style='text-align: right; padding: 1rem; color: #64B5F6; font-size: 1.1em;'>
                👋 Hi, {display_name}
            </div>
        """,
            unsafe_allow_html=True,
        )


def main():
    # Called on every Streamlit rerun (every user interaction).
    # init_session checks timeout, validates the auth token, and creates
    # the AuthService if it doesn't exist yet.
    SessionManager.init_session()

    # Gate: unauthenticated users only see the login/signup page
    if not SessionManager.is_authenticated():
        show_login_page()
        show_footer()
        return

    show_user_greeting()
    show_sidebar()

    if st.session_state.get("current_session"):
        st.title(f"📊 {st.session_state.current_session['title']}")
        messages = show_chat_history()

        if messages:
            # Analysis already done — collapse the form so the chat interface
            # is the primary focus, but still let the user re-analyze.
            with st.expander("New Analysis / Update Report", expanded=False):
                show_analysis_form()

            handle_chat_input(messages)
        else:
            # No messages yet — show the full analysis form to get started
            show_analysis_form()
    else:
        # Logged in but no session selected — prompt to create one
        show_welcome_screen()


if __name__ == "__main__":
    main()
