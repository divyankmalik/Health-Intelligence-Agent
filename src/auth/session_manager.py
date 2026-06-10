import streamlit as st
from datetime import datetime, timedelta
from config.app_config import SESSION_TIMEOUT_MINUTES
import json

# SessionManager is the single place that owns login state.
# It sits between main.py and AuthService — main.py calls SessionManager,
# SessionManager calls AuthService, AuthService talks to Supabase.
class SessionManager:
    @staticmethod
    def init_session():
        """Initialize or validate session.

        Called on every Streamlit rerun (every user interaction), so every
        check here runs multiple times per minute — keep it fast.
        """
        # 'session_initialized' acts as a one-time flag so the storage restore
        # and AuthService creation only happen on the very first load, not every rerun
        if 'session_initialized' not in st.session_state:
            st.session_state.session_initialized = True
            # Inject localStorage JS and let AuthService try to restore tokens from Supabase
            SessionManager._restore_from_storage()

        # AuthService holds the Supabase client — create it if it doesn't exist yet
        if 'auth_service' not in st.session_state:
            from auth.auth_service import AuthService
            st.session_state.auth_service = AuthService()

        # Auto-logout after SESSION_TIMEOUT_MINUTES of inactivity (default: 30 min)
        if 'last_activity' in st.session_state:
            idle_time = datetime.now() - st.session_state.last_activity
            if idle_time > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
                SessionManager.clear_session_state()
                st.error("Session expired. Please log in again.")
                st.rerun()

        # Stamp the current time so the idle clock resets on every interaction
        st.session_state.last_activity = datetime.now()

        # If a user object exists in state, verify the Supabase token is still valid.
        # Catches expired tokens or tokens revoked from another device.
        if 'user' in st.session_state:
            user_data = st.session_state.auth_service.validate_session_token()
            if not user_data:
                SessionManager.clear_session_state()
                st.error("Invalid session. Please log in again.")
                st.rerun()
    
    @staticmethod
    def _restore_from_storage():
        """Restore session from persistent storage."""
        try:
            # Step 1: inject the JS functions (saveAuthData, clearAuthData, etc.)
            # into the page so they're available for later calls
            SessionManager._inject_storage_script()

            # Step 2: the actual token restoration happens inside
            # AuthService.try_restore_session(), which reads the Supabase client's
            # cached session and syncs it back into st.session_state

        except Exception:
            pass  # Never crash the app over a failed restore — user just has to log in again
    
    @staticmethod
    def _inject_storage_script():
        """Inject JavaScript for persistent storage management.

        Streamlit wipes st.session_state on hard refresh, so we mirror auth
        tokens to localStorage and restore them via AuthService.try_restore_session().
        """
        storage_script = """
        <script>
        // Check if user data exists in localStorage on page load
        window.addEventListener('DOMContentLoaded', function() {
            const storedAuth = localStorage.getItem('hia_auth');
            if (storedAuth) {
                try {
                    const authData = JSON.parse(storedAuth);
                    // Set a flag that Python can check
                    window.hia_auth_data = authData;
                } catch (e) {
                    localStorage.removeItem('hia_auth');
                }
            }
        });
        
        // Function to save auth data
        window.saveAuthData = function(authData) {
            localStorage.setItem('hia_auth', JSON.stringify(authData));
        };
        
        // Function to clear auth data
        window.clearAuthData = function() {
            localStorage.removeItem('hia_auth');
        };
        
        // Function to get auth data
        window.getAuthData = function() {
            const stored = localStorage.getItem('hia_auth');
            return stored ? JSON.parse(stored) : null;
        };
        </script>
        """
        st.markdown(storage_script, unsafe_allow_html=True)

    @staticmethod
    def clear_session_state():
        """Clear all session state data."""
        # Wipe localStorage in the browser first so tokens don't get restored on next load
        SessionManager._clear_persistent_storage()

        # Delete every key in st.session_state except 'session_initialized'.
        # We keep that flag so _restore_from_storage() doesn't run again
        # on the very next rerun after logout.
        keys_to_keep = ['session_initialized']
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
    
    @staticmethod
    def _clear_persistent_storage():
        """Clear persistent storage."""
        # Calls the clearAuthData() JS function injected by _inject_storage_script().
        # The typeof guard prevents a JS error if the function hasn't been injected yet.
        clear_script = """
        <script>
        if (typeof window.clearAuthData === 'function') {
            window.clearAuthData();
        }
        </script>
        """
        st.markdown(clear_script, unsafe_allow_html=True)

    @staticmethod
    def _save_to_persistent_storage(user_data, auth_token):
        """Save authentication data to persistent storage."""
        # Bundle user info + token + timestamp into one JSON object for localStorage
        auth_data = {
            'user': user_data,
            'auth_token': auth_token,
            'timestamp': datetime.now().isoformat()  # stored for potential expiry checks
        }

        # json.dumps serializes the Python dict into a JS-safe JSON string.
        # Double braces {{ }} are Python f-string escapes for literal { } in the JS.
        save_script = f"""
        <script>
        if (typeof window.saveAuthData === 'function') {{
            window.saveAuthData({json.dumps(auth_data)});
        }}
        </script>
        """
        st.markdown(save_script, unsafe_allow_html=True)

    @staticmethod
    def is_authenticated():
        # 'user' is only set in session_state after a successful login or token restore
        return bool(st.session_state.get('user'))

    @staticmethod
    def create_chat_session():
        """Create a new chat session row in Supabase and return it."""
        if not SessionManager.is_authenticated():
            return False, "Not authenticated"
        # Delegates to AuthService which inserts into the chat_sessions table
        return st.session_state.auth_service.create_session(
            st.session_state.user['id']
        )

    @staticmethod
    def get_user_sessions():
        """Fetch all chat sessions for the logged-in user, newest first."""
        if not SessionManager.is_authenticated():
            return False, []
        return st.session_state.auth_service.get_user_sessions(
            st.session_state.user['id']
        )

    @staticmethod
    def delete_session(session_id):
        """Delete a session and all its messages from Supabase."""
        if not SessionManager.is_authenticated():
            return False, "Not authenticated"
        return st.session_state.auth_service.delete_session(session_id)

    @staticmethod
    def logout():
        """Sign out from Supabase and wipe all local state."""
        if 'auth_service' in st.session_state:
            # Revokes the token on the Supabase side
            st.session_state.auth_service.sign_out()
        # Wipe st.session_state and localStorage
        SessionManager.clear_session_state()

    @staticmethod
    def login(email, password):
        """Authenticate with Supabase and store the session locally."""
        # Create AuthService if it doesn't exist (e.g. first visit)
        if 'auth_service' not in st.session_state:
            from auth.auth_service import AuthService
            st.session_state.auth_service = AuthService()

        success, user_data = st.session_state.auth_service.sign_in(email, password)

        # On success, mirror the token to localStorage so it survives a page refresh
        if success and 'auth_token' in st.session_state:
            SessionManager._save_to_persistent_storage(
                user_data,
                st.session_state.auth_token
            )

        return success, user_data
