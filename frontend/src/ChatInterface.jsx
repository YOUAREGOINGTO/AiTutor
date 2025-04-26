// src/ChatInterface.jsx
// --- Imports ---
import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'; // Or your preferred theme
import styles from './ChatInterface.module.css';

// --- Send Icon Component ---
const SendIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
    <path d="M15.854.146a.5.5 0 0 1 .11.54l-5.819 14.547a.75.75 0 0 1-1.329.124l-3.178-4.995L.643 7.184a.75.75 0 0 1 .124-1.33L15.314.037a.5.5 0 0 1 .54.11ZM6.636 10.07l2.761 4.338L14.13 2.576 6.636 10.07Zm6.787-8.201L1.591 6.602l4.339 2.76 7.494-7.493Z"/>
  </svg>
);

// --- Copy Icon Component ---
const CopyIcon = ({ copied }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
        {copied ? (
            <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
        ) : (
             <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1zM9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zM6.5 0A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
        )}
    </svg>
);

// --- Copy Button Component ---
const CopyButton = ({ textToCopy }) => {
    const [isCopied, setIsCopied] = useState(false);
    const handleCopy = async () => {
        if (!navigator.clipboard) { console.error('Clipboard API not available'); return; }
        try {
            await navigator.clipboard.writeText(textToCopy);
            setIsCopied(true);
            setTimeout(() => setIsCopied(false), 2000);
        } catch (err) { console.error('Failed to copy text: ', err); }
    };
    return ( <button onClick={handleCopy} className={`${styles.copyButton} ${isCopied ? styles.copied : ''}`} aria-label={isCopied ? 'Copied' : 'Copy code'} title={isCopied ? 'Copied!' : 'Copy code'}> <CopyIcon copied={isCopied} /> </button> );
};


// --- API URLs & State/Stage Constants ---
const CHAT_API_URL = 'http://127.0.0.1:8001/api/chat/';
const SESSION_DETAIL_API_URL = (sessionId) => `http://127.0.0.1:8001/api/session/${sessionId}/`;
const STATE_STAGE = "stage";
const STATE_DISPLAY_SYLLABUS = "display_syllabus";
const STATE_TRANSITION_EXPLAINER = "transition_to_explainer";
const STAGE_START = "START";
const STAGE_NEGOTIATING = "NEGOTIATING";
const STAGE_EXPLAINING = "EXPLAINING";
const STAGE_ERROR = "ERROR";

// --- Component Definition ---
function ChatInterface({ sessionId, onSessionUpdate }) {
    const [inputValue, setInputValue] = useState('');
    const [visibleChatHistory, setVisibleChatHistory] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [appStage, setAppStage] = useState(STAGE_START);
    // Internal state to track the session ID confirmed by the last interaction
    const [confirmedSessionId, setConfirmedSessionId] = useState(sessionId);

    const chatHistoryRef = useRef(null);
    const textAreaRef = useRef(null);

    // --- Effect to Load Session History ---
    useEffect(() => {
        // Sync internal confirmed ID when the prop changes
        setConfirmedSessionId(sessionId);

        const loadSession = async (id) => {
            console.log(`ChatInterface: Loading history for session ID: ${id}`);
            setIsLoading(true); setError(null); setVisibleChatHistory([]); setAppStage(STAGE_START); setInputValue('');
            try {
                const response = await axios.get(SESSION_DETAIL_API_URL(id));
                console.log("ChatInterface: Received session details:", response.data);
                const { history, current_stage } = response.data;
                // Ensure loaded history has the 'type' field correctly set from backend
                const formattedHistory = history.map(msg => ({
                    role: msg.role,
                    content: msg.content,
                    type: msg.type || (msg.role === 'user' ? 'message' : null)
                }));
                setVisibleChatHistory(formattedHistory);
                setAppStage(current_stage || STAGE_START);
                setConfirmedSessionId(id); // Update internal ID on successful load
                setError(null);
            } catch (err) {
                console.error("Error loading session history:", err);
                setError(err.response?.data?.error || "Failed to load chat session.");
                setVisibleChatHistory([]);
                setAppStage(STAGE_ERROR);
            } finally {
                setIsLoading(false);
                textAreaRef.current?.focus();
            }
        };

        if (sessionId) {
            loadSession(sessionId);
        } else {
            // Handle "New Chat" state (prop sessionId is null)
            console.log("ChatInterface: sessionId prop is null, setting up for new chat.");
            setVisibleChatHistory([{ role: 'system', type: 'info', content: "Welcome! Tell me what you'd like to learn today." }]);
            setAppStage(STAGE_START);
            setIsLoading(false);
            setError(null);
            setInputValue('');
            setConfirmedSessionId(null); // Reset internal ID
            textAreaRef.current?.focus();
        }

    }, [sessionId]); // Dependency: only run when sessionId prop changes

    // --- Auto-resize Textarea & Scroll ---
    const adjustTextAreaHeight = useCallback(() => { if (textAreaRef.current) { textAreaRef.current.style.height = 'auto'; const scrollHeight = textAreaRef.current.scrollHeight; textAreaRef.current.style.height = `${scrollHeight}px`; } }, []);
    useEffect(() => { adjustTextAreaHeight(); }, [inputValue, adjustTextAreaHeight]);
    useEffect(() => { if (chatHistoryRef.current) { chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight; } }, [visibleChatHistory]);

    // --- Input Change Handler ---
    const handleInputChange = (event) => { setInputValue(event.target.value); };

    // --- Send Message to Backend ---
    const handleSendMessage = async () => {
        const trimmedInput = inputValue.trim();
        // Use the internal confirmedSessionId for the check after welcome message
        const isMissingSessionIdAfterWelcomeCheck = (!confirmedSessionId && visibleChatHistory.length > 1);

        // Block sending if input empty, loading, or missing session ID after first exchange
        if (!trimmedInput || isLoading || isMissingSessionIdAfterWelcomeCheck) {
            if (isMissingSessionIdAfterWelcomeCheck) console.warn("Send blocked: Missing confirmed Session ID after welcome.");
            if (isLoading) console.warn("Send blocked: Already loading.");
            if (!trimmedInput) console.warn("Send blocked: Input empty.");
            return;
        }

        const userMessage = { role: 'user', content: trimmedInput, type: 'message' };
        setVisibleChatHistory(prev => [...prev, userMessage]); // Optimistic update

        const requestData = {
            user_message: trimmedInput,
            session_id: confirmedSessionId // Send the internally confirmed ID (null for first message)
        };

        setInputValue('');
        setIsLoading(true); // Start loading for API call
        setError(null);
        if (textAreaRef.current) { textAreaRef.current.style.height = 'auto'; }

        let messageSendSuccess = false;
        let receivedSessionId = null;

        try {
            console.log(`ChatInterface: Sending message (Confirmed Session ID: ${confirmedSessionId || '(None - New Session)'})`);
            const response = await axios.post(CHAT_API_URL, requestData);
            console.log("ChatInterface: Received response from backend:", response.data);

            const { ai_reply, new_state, session_id: returnedSessionId } = response.data;
            receivedSessionId = returnedSessionId; // Store ID from response

            if (new_state && new_state[STATE_STAGE]) {
                setAppStage(new_state[STATE_STAGE]);
            }

            // Process response messages
            const newVisibleMessages = [];
            const syllabusToDisplay = new_state?.[STATE_DISPLAY_SYLLABUS];
            const transitionOccurred = new_state?.[STATE_TRANSITION_EXPLAINER];
            if (syllabusToDisplay) newVisibleMessages.push({ role: 'system', type: 'syllabus', content: typeof syllabusToDisplay === 'string' ? syllabusToDisplay : JSON.stringify(syllabusToDisplay) });
            if (transitionOccurred) {
                // Simple check to avoid adding duplicate transitions if signal repeats
                const lastMsgIndex = visibleChatHistory.length -1; // Check history *before* adding user message
                const lastMsg = lastMsgIndex >= 0 ? visibleChatHistory[lastMsgIndex] : null;
                if (!(lastMsg?.type === 'info' && lastMsg?.content.includes("Starting Learning Session"))) {
                     newVisibleMessages.push({ role: 'system', type: 'info', content: "--- Starting Learning Session ---" });
                }
            }
            if (ai_reply) newVisibleMessages.push({ role: 'ai', content: typeof ai_reply === 'string' ? ai_reply : JSON.stringify(ai_reply) });

            if (newVisibleMessages.length > 0) {
                setVisibleChatHistory(prev => [...prev, ...newVisibleMessages]);
            }

            messageSendSuccess = true; // Mark as success

        } catch (err) {
            console.error("Error sending message:", err);
            let errorMsg = "An error occurred.";
            if (err.response) { errorMsg = `Server Error: ${err.response.status}`; if (err.response.data?.error) errorMsg += ` - ${err.response.data.error}`; else if (err.response.data?.ai_reply?.startsWith("[")) errorMsg = `AI Error: ${err.response.data.ai_reply}`; setAppStage(err.response.data?.new_state?.[STATE_STAGE] || STAGE_ERROR); }
            else if (err.request) { errorMsg = "Cannot reach server."; setAppStage(STAGE_ERROR); }
            else { errorMsg = `Frontend error: ${err.message}`; setAppStage(STAGE_ERROR); }
            setError(errorMsg);
            // Remove the optimistic user message on error
             setVisibleChatHistory(prev => {
                if (prev.length > 0 && prev[prev.length - 1].role === 'user') {
                    return prev.slice(0, -1);
                }
                return prev; // Return unmodified if last wasn't user
            });
            messageSendSuccess = false;
        } finally {
             // After API call attempt (success or failure)
             if (messageSendSuccess && receivedSessionId) {
                 // Update internal confirmed ID *immediately* on success
                 setConfirmedSessionId(receivedSessionId);
                 console.log(`ChatInterface: Confirmed session ID set internally to: ${receivedSessionId}`);
                 // Notify parent
                 if (onSessionUpdate) {
                    console.log(`ChatInterface: Notifying parent of update for session: ${receivedSessionId}`);
                    onSessionUpdate(receivedSessionId);
                 }
             }
            // Set loading false after potential parent notification
             setIsLoading(false);
             console.log(`ChatInterface: setIsLoading(false)`);
             textAreaRef.current?.focus();
        }
    };

    // --- Handle Enter Key Press ---
    const handleKeyPress = (event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleSendMessage(); } };

    // --- Render Message Content (REVISED LOGIC - Prioritize Type) ---
    const renderMessageContent = useCallback((msg) => {
        if (!msg || msg.content === null || typeof msg.content === 'undefined') {
            console.warn("Attempted to render invalid message:", msg);
            return null; // Don't render invalid messages
        }
        const contentString = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);

        // --- Priority 1: Check for Specific Message Types ---
        // Render syllabus based on type 'syllabus', regardless of role
        if (msg.type === 'internal') { // <--- THIS WAS THE KEY ADDITION
            console.log("Hiding internal command message.");
            return null; // Return null to render nothing
        }

        if (msg.type === 'syllabus') {
            console.log("Rendering message as syllabus:", msg.content?.substring(0, 50));
            const syllabusText = contentString.replace(/<\/?syllabus>/gi, '').trim();
            const lines = syllabusText.split('\n').filter(line => line.trim() !== '');
            return (
                <div className={styles.syllabusParsedContent}>
                    <h4>Syllabus Draft/Update</h4>
                    {lines.map((line, index) => {
                        line = line.trim();
                        if (line.toLowerCase().startsWith('phase')) return <p key={index} className={styles.syllabusPhase}>{line}</p>;
                        if (line.toLowerCase().startsWith('topic:')) return <p key={index} className={styles.syllabusTopicTitle}>{line}</p>;
                        if (line.toLowerCase().match(/^(keywords:|objective:|focus:)/i)) {
                            const parts = line.split(':'); const label = parts[0].trim(); const value = parts.slice(1).join(':').trim();
                            return ( <p key={index} className={styles.syllabusTopicDetail}><span className={styles.syllabusDetailLabel}>{label}:</span> {value}</p> );
                        }
                        return <p key={index} className={styles.syllabusOtherLine}>{line}</p>;
                    })}
                </div>
            );
        }
        // Render info messages based on type 'info'
        if (msg.type === 'info') {
            console.log("Rendering message as info:", msg.content);
            return <div className={styles.infoMessageContent}>{contentString}</div>;
        }

        // --- Priority 2: Check Roles (if type wasn't special) ---
        if (msg.role === 'user') {
            console.log("Rendering message as user:", msg.content?.substring(0, 50));
            return <pre className={styles.preformattedText}>{contentString}</pre>;
        }

        // Render AI/Model responses using Markdown
        // Covers 'ai' (from live response) and 'model' (from loaded history)
        if (msg.role === 'ai' || msg.role === 'model') {
            console.log("Rendering message as ai/model (Markdown):", msg.content?.substring(0, 50));
            // Basic check for potentially harmful HTML
            const potentialUnsafeContent = /<[^>]+script|<[^>]+\bon\w+=/i.test(contentString);
            if (potentialUnsafeContent) {
                 console.warn("Potential unsafe HTML detected in AI/Model message, rendering as preformatted text.");
                 return <pre className={styles.preformattedText}>{contentString}</pre>;
            }
            // Use ReactMarkdown for rendering
            return (
                <ReactMarkdown
                    components={{
                        // Custom renderer for code blocks (``` ```)
                        code(props) {
                            const { children, className, node, inline, ...rest } = props;
                            const match = /language-(\w+)/.exec(className || '');
                            const language = match ? match[1] : null;
                            const codeText = String(children).replace(/\n$/, ''); // Remove trailing newline

                            // Render inline code (`code`)
                            if (inline) {
                                return <code {...rest} className={styles.inlineCode}>{children}</code>;
                            }

                            // Render block code (``` ```)
                            return (
                                <div className={styles.codeBlockWrapper}>
                                    <CopyButton textToCopy={codeText} />
                                    {language ? ( // Use SyntaxHighlighter if language is detected
                                        <SyntaxHighlighter {...rest} style={vscDarkPlus} language={language} PreTag="div" className={styles.codeBlock} showLineNumbers={false} wrapLongLines={true}>
                                            {codeText}
                                        </SyntaxHighlighter>
                                    ) : ( // Fallback for code blocks without a language tag
                                         <pre {...rest} className={styles.codeBlockPlain}><code>{children}</code></pre>
                                    )}
                                </div>
                            );
                        },
                        // Add other custom renderers if needed (e.g., p, ul, ol, li)
                    }}
                    // Add remarkPlugins here if needed (e.g., remark-gfm for tables)
                >
                    {contentString}
                </ReactMarkdown>
            );
        }

        // --- Fallback for unknown roles or unhandled system messages ---
        console.warn(`Rendering message with unknown role/type combination: Role=${msg.role}, Type=${msg.type}. Content:`, msg.content?.substring(0, 50));
        return <pre className={styles.preformattedText}>{contentString}</pre>;
     }, []); // Empty dependency array: function created once

    // --- Placeholder Text Logic ---
    const getPlaceholderText = () => {
        switch (appStage) {
            case STAGE_EXPLAINING: return "Ask about the current topic...";
            case STAGE_NEGOTIATING: case STAGE_START: return "Describe what you want to learn...";
            case STAGE_ERROR: return "An error occurred. Try starting a new chat.";
            default: return "Type your message...";
        }
    };

    // --- Determine if input should be disabled ---
    // Use the internal confirmedSessionId for the check
    const isMissingSessionIdAfterWelcomeInternal = (!confirmedSessionId && visibleChatHistory.length > 1);
    const isInputDisabled = isLoading || appStage === STAGE_ERROR || isMissingSessionIdAfterWelcomeInternal;

    // --- Render Component JSX ---
    return (
        <div className={styles.chatContainer}>
            {/* Chat History Area */}
            <div className={styles.chatHistory} ref={chatHistoryRef}>
                {/* Loading indicator for initial history fetch */}
                {isLoading && visibleChatHistory.length === 0 && ( <div className={styles.loading}>Loading chat history...</div> )}
                {/* Render messages */}
                {visibleChatHistory.map((msg, index) => {
                     // Determine classes based on role and type
                     const messageClasses = [
                         styles.message,
                         // Role-based classes for general alignment/background
                         msg.role === 'user' ? styles.userMessage : '',
                         (msg.role === 'ai' || msg.role === 'model') ? styles.aiMessage : '', // Group AI/Model visually
                         msg.role === 'system' ? styles.systemMessage : '',
                         // Type-based classes for specific styling overrides
                         msg.type === 'syllabus' ? styles.syllabusMessage : '',
                         msg.type === 'info' ? styles.infoMessage : ''
                     ].filter(Boolean).join(' ');

                    // Get the rendered content using the memoized function
                    const renderedContent = renderMessageContent(msg);

                    // Render the message container only if there's valid content
                    // Use confirmedSessionId in the key for better stability across renders/loads
                    return renderedContent ? (
                         <div key={`${confirmedSessionId || 'new'}-${index}`} className={messageClasses}>
                             <div className={styles.messageContent}>{renderedContent}</div>
                         </div>
                     ) : null; // Don't render if renderMessageContent returned null
                })}
                {/* Loading indicator for AI response (when history exists) */}
                {isLoading && visibleChatHistory.length > 0 && ( <div className={`${styles.message} ${styles.aiMessage}`}> <div className={styles.messageContent}><div className={styles.loadingIndicator}><span>AI is thinking...</span></div></div> </div> )}
            </div>

            {/* Error Display */}
            {error && <div className={styles.errorDisplay}>{error}</div>}

            {/* Input Area */}
            <div className={styles.inputArea}>
                 <textarea
                    ref={textAreaRef}
                    className={styles.inputField}
                    value={inputValue}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyPress}
                    placeholder={getPlaceholderText()}
                    rows={1}
                    disabled={isInputDisabled} // Use derived disabled state
                    aria-label="Chat message input"
                 />
                 <button
                    className={styles.sendButton}
                    onClick={handleSendMessage}
                    // Also disable if input is just whitespace
                    disabled={isInputDisabled || !inputValue.trim()}
                    aria-label="Send message"
                 >
                     <SendIcon />
                 </button>
            </div>
        </div>
    );
}

export default ChatInterface;