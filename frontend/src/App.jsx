// src/App.jsx
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import ChatInterface from './ChatInterface';
import ChatHistorySidebar from './ChatHistorySidebar';
import DeleteConfirmationModal from './DeleteConfirmationModal';
import AuthModal from './AuthModal'; // Import the auth modal
import './App.css'; // Main layout CSS

// --- API URLs ---
const SESSIONS_API_URL = 'http://127.0.0.1:8001/api/sessions/';
const SESSION_UPDATE_TITLE_API_URL = (sessionId) => `http://127.0.0.1:8001/api/session/${sessionId}/update_title/`;
const SESSION_DELETE_API_URL = (sessionId) => `http://127.0.0.1:8001/api/session/${sessionId}/delete/`;
// *** Placeholder Auth API URLs (Will need actual implementation later) ***
// const LOGIN_API_URL = 'http://127.0.0.1:8000/api/auth/login/';
// const SIGNUP_API_URL = 'http://127.0.0.1:8000/api/auth/signup/';
// const LOGOUT_API_URL = 'http://127.0.0.1:8000/api/auth/logout/';


// --- Helper function to group sessions by time ---
const groupSessionsByTime = (sessions) => {
    const groups = { Today: [], Yesterday: [], 'Previous 7 Days': [], 'Previous 30 Days': [], };
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterdayStart = new Date(todayStart); yesterdayStart.setDate(todayStart.getDate() - 1);
    const sevenDaysAgo = new Date(todayStart); sevenDaysAgo.setDate(todayStart.getDate() - 7);
    const thirtyDaysAgo = new Date(todayStart); thirtyDaysAgo.setDate(todayStart.getDate() - 30);
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

    sessions.forEach(session => {
        if (!session.updated_at) { if (!groups['Older']) groups['Older'] = []; groups['Older'].push(session); return; }
        const sessionDate = new Date(session.updated_at);
        if (sessionDate >= todayStart) { groups.Today.push(session); }
        else if (sessionDate >= yesterdayStart) { groups.Yesterday.push(session); }
        else if (sessionDate >= sevenDaysAgo) { groups['Previous 7 Days'].push(session); }
        else if (sessionDate >= thirtyDaysAgo) { groups['Previous 30 Days'].push(session); }
        else { const monthYear = `${monthNames[sessionDate.getMonth()]} ${sessionDate.getFullYear()}`; if (!groups[monthYear]) { groups[monthYear] = []; } groups[monthYear].push(session); }
    });
    Object.keys(groups).forEach(key => { if (groups[key].length === 0) { delete groups[key]; } });
    const standardKeys = ['Today', 'Yesterday', 'Previous 7 Days', 'Previous 30 Days']; const monthKeys = Object.keys(groups).filter(key => !standardKeys.includes(key) && key !== 'Older').sort((a, b) => { const [monthA, yearA] = a.split(' '); const [monthB, yearB] = b.split(' '); const dateA = new Date(`${monthA} 1, ${yearA}`); const dateB = new Date(`${monthB} 1, ${yearB}`); return dateB - dateA; }); const orderedKeys = [...standardKeys, ...monthKeys, 'Older'].filter(key => groups[key] && groups[key].length > 0); const orderedGroups = {}; orderedKeys.forEach(key => { orderedGroups[key] = groups[key]; });
    return orderedGroups;
};


function App() {
    const [groupedSessions, setGroupedSessions] = useState({});
    const [currentSessionId, setCurrentSessionId] = useState(null);
    const [isLoadingSessions, setIsLoadingSessions] = useState(false);
    const [sessionsError, setSessionsError] = useState(null);
    const [chatInterfaceKey, setChatInterfaceKey] = useState(0);
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    // Delete Modal State
    const [sessionToDeleteId, setSessionToDeleteId] = useState(null);
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    // Authentication State
    const [isAuthenticated, setIsAuthenticated] = useState(false); // Default to logged out
    const [currentUser, setCurrentUser] = useState(null); // e.g., { username: '...' }
    // const [authToken, setAuthToken] = useState(null); // To store auth token later
    const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
    const [authModalMode, setAuthModalMode] = useState('login'); // 'login' or 'signup'

    // Fetch session list (will need modification later for authenticated requests)
    const fetchSessions = useCallback(async () => {
        setIsLoadingSessions(true);
        setSessionsError(null);
        console.log("App: Fetching session list...");
        try {
            // TODO: Add Authorization header if isAuthenticated and authToken exists
            // const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};
            // const response = await axios.get(SESSIONS_API_URL, { headers });
            const response = await axios.get(SESSIONS_API_URL); // Current implementation (unauthenticated)
            const sessionsData = response.data.sessions || [];
            const grouped = groupSessionsByTime(sessionsData);
            setGroupedSessions(grouped);
            console.log("App: Fetched and grouped sessions:", Object.keys(grouped).length, "groups");
        } catch (error) {
            console.error("App: Error fetching sessions:", error);
            // If error is 401/403, potentially logout user or prompt login
            // if (error.response && (error.response.status === 401 || error.response.status === 403)) {
            //     handleLogout(); // Example: force logout on auth error
            // }
            setSessionsError("Failed to load chat history.");
            setGroupedSessions({});
        } finally {
            setIsLoadingSessions(false);
        }
    }, [/* Add authToken here later */]); // Dependency array might need authToken

    // Fetch sessions on initial mount
    useEffect(() => {
        // TODO: Add logic here to check localStorage for token and auto-login/fetch user
        fetchSessions();
    }, [fetchSessions]);

    // --- Session Management Handlers ---
    const handleSelectSession = (sessionId) => {
        console.log(`App: Selecting session ${sessionId}`);
        if (sessionId !== currentSessionId) {
            setCurrentSessionId(sessionId);
            if (isSidebarCollapsed) setIsSidebarCollapsed(false);
            setChatInterfaceKey(prevKey => prevKey + 1);
        }
    };
    const handleNewChat = () => {
        console.log("App: Starting new chat");
        if (currentSessionId !== null) setChatInterfaceKey(prevKey => prevKey + 1);
        setCurrentSessionId(null);
        if (isSidebarCollapsed) setIsSidebarCollapsed(false);
    };
    const handleSessionUpdate = useCallback((updatedSessionId) => {
        console.log(`App: Session update notification received for ID: ${updatedSessionId}`);
        // Simple refresh for now, could optimize later
        fetchSessions();
        // If a new chat just got its ID, make sure it's set as current
        if (currentSessionId === null && updatedSessionId) {
             setCurrentSessionId(updatedSessionId);
        }
     }, [fetchSessions, currentSessionId]); // Add currentSessionId dependency

    const handleRenameSession = useCallback(async (sessionId, newTitle) => {
        console.log(`App: Attempting rename session ${sessionId} to "${newTitle}"`);
        let originalSessionData = null; let originalGroupKey = null; let sessionIndexInGroup = -1;
        // Find session for optimistic update/revert
        for (const [key, sessionsInGroup] of Object.entries(groupedSessions)) { const index = sessionsInGroup.findIndex(s => s.session_id === sessionId); if (index !== -1) { originalSessionData = { ...sessionsInGroup[index] }; originalGroupKey = key; sessionIndexInGroup = index; break; } }
        // Optimistic Update
        if (originalSessionData) { const updatedGroupsOptimistic = { ...groupedSessions }; updatedGroupsOptimistic[originalGroupKey] = [ ...updatedGroupsOptimistic[originalGroupKey].slice(0, sessionIndexInGroup), { ...originalSessionData, title: newTitle }, ...updatedGroupsOptimistic[originalGroupKey].slice(sessionIndexInGroup + 1) ]; setGroupedSessions(updatedGroupsOptimistic); }
        try {
            // TODO: Add Authorization header
            const response = await axios.patch(SESSION_UPDATE_TITLE_API_URL(sessionId), { title: newTitle });
            console.log("App: Session rename successful via API", response.data);
            // Confirm local state using response data (ONLY title, keep original updated_at)
             setGroupedSessions(currentGroups => { const finalGroups = { ...currentGroups }; if (finalGroups[originalGroupKey]) { const group = finalGroups[originalGroupKey]; const finalIndex = group.findIndex(s => s.session_id === sessionId); if (finalIndex !== -1) { finalGroups[originalGroupKey] = [ ...group.slice(0, finalIndex), { ...group[finalIndex], title: response.data.title }, ...group.slice(finalIndex + 1) ]; } } return finalGroups; });
        } catch (error) {
            console.error("App: Error renaming session via API:", error); alert(`Failed to rename session: ${error.response?.data?.error || error.message}`);
            // Revert Optimistic Update
            if (originalSessionData) { console.log("App: Reverting optimistic rename."); const revertedGroups = { ...groupedSessions }; if (revertedGroups[originalGroupKey]) { revertedGroups[originalGroupKey] = [ ...revertedGroups[originalGroupKey].slice(0, sessionIndexInGroup), originalSessionData, ...revertedGroups[originalGroupKey].slice(sessionIndexInGroup + 1) ]; setGroupedSessions(revertedGroups); } else { fetchSessions(); } } else { fetchSessions(); }
        }
    }, [groupedSessions, fetchSessions]);

    // Delete Initiation (opens modal)
    const handleDeleteSession = useCallback((sessionIdToDelete) => {
        console.log(`App: Initiating delete for session ${sessionIdToDelete}`);
        setSessionToDeleteId(sessionIdToDelete);
        setIsDeleteModalOpen(true);
    }, []);

    // Delete Confirmation (called by modal)
    const confirmDeleteHandler = useCallback(async () => {
        if (!sessionToDeleteId) return;
        console.log(`App: Confirming delete for session ${sessionToDeleteId}`);
        const idToDelete = sessionToDeleteId;
        setIsDeleteModalOpen(false); setSessionToDeleteId(null);
        try {
            // TODO: Add Authorization header
            await axios.delete(SESSION_DELETE_API_URL(idToDelete));
            console.log(`App: Session delete successful via API for ${idToDelete}`);
            fetchSessions(); // Refresh list
            if (currentSessionId === idToDelete) {
                console.log("App: Deleted active session, switching to New Chat.");
                setCurrentSessionId(null); setChatInterfaceKey(prevKey => prevKey + 1);
            }
        } catch (error) {
            console.error("App: Error deleting session via API:", error);
            alert(`Failed to delete session: ${error.response?.data?.error || error.message}`);
        }
    }, [sessionToDeleteId, currentSessionId, fetchSessions]);

    // Delete Cancellation (called by modal)
    const cancelDeleteHandler = useCallback(() => {
        setIsDeleteModalOpen(false); setSessionToDeleteId(null);
    }, []);

    // --- Sidebar Toggle ---
    const toggleSidebar = () => { setIsSidebarCollapsed(!isSidebarCollapsed); };

    // --- Authentication Handlers ---
    const openAuthModal = (mode = 'login') => { setAuthModalMode(mode); setIsAuthModalOpen(true); };
    const closeAuthModal = () => { setIsAuthModalOpen(false); };
    const switchAuthModalMode = (newMode) => { setAuthModalMode(newMode); };

    // Simulate successful Auth - Replace with actual API logic
    const handleAuthSuccess = (userData) => {
        console.log("App: Auth successful (simulation)", userData);
        setIsAuthenticated(true);
        setCurrentUser({ username: userData.username }); // Assuming backend returns username
        // setAuthToken(userData.token); // Store token from backend
        // localStorage.setItem('authToken', userData.token); // Persist token
        setIsAuthModalOpen(false);
        fetchSessions(); // Refetch sessions for the logged-in user
    };

    const handleLogout = async () => {
        console.log("App: Logging out (simulation)");
        // TODO: Call actual backend logout endpoint
        // try { await axios.post(LOGOUT_API_URL, {}, { headers: { Authorization: `Bearer ${authToken}` }}); } catch (err) { console.error("Logout failed", err); }

        setIsAuthenticated(false);
        setCurrentUser(null);
        // setAuthToken(null);
        // localStorage.removeItem('authToken');
        setCurrentSessionId(null); // Go to new chat view
        setChatInterfaceKey(prevKey => prevKey + 1);
        setGroupedSessions({}); // Clear session list
        // fetchSessions(); // Optionally fetch public sessions if any
    };

    // Helper to get session title for delete modal
    const getSessionTitleForDelete = () => {
        if (!sessionToDeleteId) return '';
        for (const group of Object.values(groupedSessions)) { const session = group.find(s => s.session_id === sessionToDeleteId); if (session) { return session.title || `Chat ${session.session_id.substring(0, 6)}...`; } }
        return `Chat ${sessionToDeleteId.substring(0, 6)}...`;
    };

    return (
        <div className={`appContainer ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
             <button onClick={toggleSidebar} className="sidebarToggleButton" aria-label={isSidebarCollapsed ? "Open sidebar" : "Close sidebar"} title={isSidebarCollapsed ? "Open sidebar" : "Close sidebar"}>
                 {isSidebarCollapsed ? <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M5.17187 2.0249L11.1469 7.9999L5.17187 13.9749L3.97437 12.7774L8.75187 7.9999L3.97437 3.2224L5.17187 2.0249Z" fill="currentColor"/></svg> : <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M10.8281 13.9751L4.85313 8.00009L10.8281 2.02509L12.0256 3.22259L7.24813 8.00009L12.0256 12.7776L10.8281 13.9751Z" fill="currentColor"/></svg>}
             </button>

            <div className="sidebarContainer">
                <ChatHistorySidebar
                    groupedSessions={groupedSessions}
                    currentSessionId={currentSessionId}
                    onSelectSession={handleSelectSession}
                    onNewChat={handleNewChat}
                    isLoading={isLoadingSessions}
                    error={sessionsError}
                    onRenameSession={handleRenameSession}
                    onDeleteSession={handleDeleteSession} // Triggers modal open
                    // Pass Auth Props
                    isAuthenticated={isAuthenticated}
                    currentUser={currentUser}
                    onLoginClick={() => openAuthModal('login')}
                    onLogout={handleLogout}
                />
            </div>
            <div className="chatInterfaceContainer">
                <ChatInterface
                    key={chatInterfaceKey}
                    sessionId={currentSessionId}
                    onSessionUpdate={handleSessionUpdate}
                    // isAuthenticated={isAuthenticated} // Pass down if ChatInterface needs it
                />
            </div>

            {/* Render Modals */}
            <DeleteConfirmationModal
                isOpen={isDeleteModalOpen}
                onClose={cancelDeleteHandler}
                onConfirm={confirmDeleteHandler}
                sessionTitle={getSessionTitleForDelete()}
            />
             <AuthModal
                isOpen={isAuthModalOpen}
                onClose={closeAuthModal}
                mode={authModalMode}
                onSwitchMode={switchAuthModalMode}
                onAuthSuccess={handleAuthSuccess} // Handles simulated success for now
            />
        </div>
    );
}

export default App;