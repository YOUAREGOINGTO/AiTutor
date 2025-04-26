// src/ChatHistorySidebar.jsx
import React, { useState, useRef, useEffect } from 'react';
import styles from './ChatHistorySidebar.module.css';

// --- Icons (Using inline SVGs for better control) ---
const EditIcon = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M13.94 5L19 10.06L9.062 20a2.25 2.25 0 0 1-.999.58l-5.11 1.388a0.752 0.752 0 0 1-.94-.941l1.388-5.11a2.25 2.25 0 0 1 .58-.999L13.938 5zm7.09-2.026a2.498 2.498 0 0 0-3.535 0l-1.061 1.06L21.5 9.1l1.06-1.06a2.5 2.5 0 0 0 0-3.536z" fill="currentColor"></path></svg>;
const DeleteIcon = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M15 3.75H9V2.25a.75.75 0 0 1 .75-.75h4.5a.75.75 0 0 1 .75.75V3.75z" fill="currentColor"></path><path d="M4.5 4.5H19.5V18a3.75 3.75 0 0 1-3.75 3.75H8.25A3.75 3.75 0 0 1 4.5 18V4.5z" fill="currentColor"></path></svg>;
const NewChatIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" clipRule="evenodd" d="M12 3.75a1 1 0 0 1 1 1v7.25h7.25a1 1 0 1 1 0 2H13v7.25a1 1 0 1 1-2 0V14H3.75a1 1 0 1 1 0-2H11V4.75a1 1 0 0 1 1-1z" fill="currentColor"></path></svg>;
const LoginIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M10.75 3.75a.75.75 0 0 0-1.5 0v11.19l-4.47-4.47a.75.75 0 0 0-1.06 1.06l5.75 5.75a.75.75 0 0 0 1.06 0l5.75-5.75a.75.75 0 1 0-1.06-1.06l-4.47 4.47V3.75z" fill="currentColor"></path><path d="M16.75 15a.75.75 0 0 0 .75.75v3c0 .966-.784 1.75-1.75 1.75H8.25a1.75 1.75 0 0 1-1.75-1.75v-3a.75.75 0 0 0-1.5 0v3A3.25 3.25 0 0 0 8.25 22.5h7.5A3.25 3.25 0 0 0 19.25 18.75v-3a.75.75 0 0 0-.75-.75z" fill="currentColor"></path></svg>; // Login Arrow In
const LogoutIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M10.75 3.75a.75.75 0 0 0-1.5 0v11.19l-4.47-4.47a.75.75 0 1 0-1.06 1.06l5.75 5.75a.75.75 0 0 0 1.06 0l5.75-5.75a.75.75 0 0 0-1.06-1.06l-4.47 4.47V3.75z" transform="rotate(180 12 12)" fill="currentColor"></path><path d="M16.75 15a.75.75 0 0 0 .75.75v3c0 .966-.784 1.75-1.75 1.75H8.25a1.75 1.75 0 0 1-1.75-1.75v-3a.75.75 0 0 0-1.5 0v3A3.25 3.25 0 0 0 8.25 22.5h7.5A3.25 3.25 0 0 0 19.25 18.75v-3a.75.75 0 0 0-.75-.75z" transform="rotate(180 12 12)" fill="currentColor"></path></svg>; // Logout Arrow Out
const UserIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" clipRule="evenodd" d="M12 2.25c-5.376 0-9.75 4.374-9.75 9.75s4.374 9.75 9.75 9.75 9.75-4.374 9.75-9.75S17.376 2.25 12 2.25zM12 6a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm-7 10.845c0-2.749 4.477-4.065 7-4.065s7 1.316 7 4.065C19 18.396 15.832 20 12 20s-7-1.604-7-3.155z" fill="currentColor"></path></svg>;

// --- Date Formatter ---
const formatDate = (isoString) => {
    if (!isoString) return ''; const date = new Date(isoString); const now = new Date(); const diffHours = (now - date) / (1000 * 60 * 60);
    if (diffHours < 24 && now.getDate() === date.getDate()) { return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }); }
    else if (diffHours < 168) { return date.toLocaleDateString([], { weekday: 'long' }); }
    else { return date.toLocaleDateString([], { month: 'short', day: 'numeric' }); }
};

function ChatHistorySidebar({
    groupedSessions,
    currentSessionId,
    onSelectSession,
    onNewChat,
    isLoading,
    error,
    onRenameSession,
    onDeleteSession,
    isAuthenticated,
    currentUser,
    onLoginClick,
    onLogout
}) {
    const [editingSessionId, setEditingSessionId] = useState(null);
    const [editValue, setEditValue] = useState("");
    const editInputRef = useRef(null);

    useEffect(() => { if (editingSessionId && editInputRef.current) { editInputRef.current.focus(); editInputRef.current.select(); } }, [editingSessionId]);

    // --- Edit Handling ---
    const handleStartEdit = (e, session) => { e.stopPropagation(); setEditingSessionId(session.session_id); setEditValue(session.title || ""); };
    const handleCancelEdit = (e) => { e?.stopPropagation(); setEditingSessionId(null); setEditValue(""); };
    const handleConfirmEdit = (e) => {
        e?.stopPropagation();
        if (editingSessionId && editValue.trim()) {
             const sessionBeingEdited = Object.values(groupedSessions).flat().find(s => s.session_id === editingSessionId);
             if (sessionBeingEdited && sessionBeingEdited.title !== editValue.trim()) {
                 onRenameSession(editingSessionId, editValue.trim());
             }
        }
        setEditingSessionId(null); setEditValue("");
    };
    const handleEditInputChange = (e) => { setEditValue(e.target.value); };
    const handleEditKeyDown = (e) => { if (e.key === 'Enter') { handleConfirmEdit(e); } else if (e.key === 'Escape') { handleCancelEdit(e); } };

    // --- Delete Handling (Triggers modal via App.jsx) ---
    const handleDeleteClick = (e, sessionId) => {
        e.stopPropagation();
        onDeleteSession(sessionId); // Call parent handler to open modal
    };

    return (
        <div className={styles.sidebar}>
            {/* New Chat Button */}
            <button onClick={onNewChat} className={styles.newChatButton}>
                <NewChatIcon /> New Chat
            </button>

            {/* Session List */}
            <div className={styles.sessionList}>
                {isLoading && <div className={styles.loading}>Loading chats...</div>}
                {error && <div className={styles.error}>{error}</div>}
                {!isLoading && !error && Object.keys(groupedSessions).length === 0 && (
                    <div className={styles.empty}>No past chats found.</div>
                )}
                {!isLoading && !error && Object.entries(groupedSessions).map(([groupName, sessionsInGroup]) => (
                    <div key={groupName} className={styles.sessionGroup}>
                        <h4 className={styles.groupHeader}>{groupName}</h4>
                        {sessionsInGroup.map((session) => (
                            <div
                                key={session.session_id}
                                className={`${styles.sessionItem} ${session.session_id === currentSessionId ? styles.active : ''} ${editingSessionId === session.session_id ? styles.editing : ''}`}
                                onClick={(e) => { if (editingSessionId !== session.session_id) { onSelectSession(session.session_id); } else { e.stopPropagation();} }}
                                role="button" tabIndex={0}
                                onKeyDown={(e) => { if (!editingSessionId && (e.key === 'Enter' || e.key === ' ')) onSelectSession(session.session_id); }}
                            >
                                {editingSessionId === session.session_id ? (
                                    <input ref={editInputRef} type="text" className={styles.editInput} value={editValue} onChange={handleEditInputChange} onKeyDown={handleEditKeyDown} onBlur={handleConfirmEdit} onClick={(e) => e.stopPropagation()} aria-label="Rename chat title"/>
                                ) : (
                                    <>
                                        <span className={styles.sessionTitle}>
                                            {session.title || `Chat ${session.session_id.substring(0, 6)}...`}
                                        </span>
                                        <div className={styles.sessionItemActionsWrapper}>
                                             <button onClick={(e) => handleStartEdit(e, session)} className={styles.actionButton} aria-label="Rename chat" title="Rename chat"><EditIcon /></button>
                                             <button onClick={(e) => handleDeleteClick(e, session.session_id)} className={`${styles.actionButton} ${styles.deleteButton}`} aria-label="Delete chat" title="Delete chat"><DeleteIcon /></button>
                                        </div>
                                    </>
                                )}
                            </div>
                        ))}
                    </div>
                ))}
            </div>

            {/* Auth Section at the Bottom */}
            <div className={styles.sidebarFooter}>
                {isAuthenticated && currentUser ? (
                    // Logged In View: User info and Logout button
                    <button onClick={onLogout} className={styles.footerButton} title={`Log out ${currentUser.username}`}>
                        <span className={styles.userIconWrapper}><UserIcon /></span>
                        <span className={styles.footerButtonText}>{currentUser.username}</span>
                        <span className={styles.logoutIconWrapper}><LogoutIcon/></span>
                    </button>
                ) : (
                    // Logged Out View: Login button
                    <button onClick={onLoginClick} className={styles.footerButton}>
                        <span className={styles.loginIconWrapper}><LoginIcon /></span>
                        <span className={styles.footerButtonText}>Login</span>
                    </button>
                )}
            </div>
        </div>
    );
}

export default ChatHistorySidebar;