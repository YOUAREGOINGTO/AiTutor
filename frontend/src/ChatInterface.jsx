// src/ChatInterface.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import styles from './ChatInterface.module.css';
import FileChip from './FileChip'; // For displaying files *before* sending

// --- Icons ---
const SendIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
    <path d="M15.854.146a.5.5 0 0 1 .11.54l-5.819 14.547a.75.75 0 0 1-1.329.124l-3.178-4.995L.643 7.184a.75.75 0 0 1 .124-1.33L15.314.037a.5.5 0 0 1 .54.11ZM6.636 10.07l2.761 4.338L14.13 2.576 6.636 10.07Zm6.787-8.201L1.591 6.602l4.339 2.76 7.494-7.493Z"/>
  </svg>
);
const CopyIcon = ({ copied }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
        {copied ? (
            <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
        ) : (
             <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1zM9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zM6.5 0A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
        )}
    </svg>
);
const PaperclipIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
      <path d="M4.5 3a2.5 2.5 0 0 1 5 0v9a1.5 1.5 0 0 1-3 0V5a.5.5 0 0 1 1 0v7a.5.5 0 0 0 1 0V3a1.5 1.5 0 1 0-3 0v9a2.5 2.5 0 0 0 5 0V5a.5.5 0 0 1 1 0v7a3.5 3.5 0 1 1-7 0V3z"/>
    </svg>
);
const DocumentIcon = () => ( // Used for in-message attachment display
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" className={styles.attachmentIconSvg}>
        <path d="M4 0h8a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H4z"/>
        <path d="M4.5 12.5A.5.5 0 0 1 5 12h3a.5.5 0 0 1 0 1H5a.5.5 0 0 1-.5-.5zm0-2A.5.5 0 0 1 5 10h6a.5.5 0 0 1 0 1H5a.5.5 0 0 1-.5-.5zm1.639-3.708a.5.5 0 0 1 .707 0l2 2a.5.5 0 0 1 0 .707l-2 2a.5.5 0 0 1-.707-.707L7.793 8 6.139 6.346a.5.5 0 0 1 0-.707z"/>
    </svg>
);

// --- Constants ---
const BACKEND_STATE_STAGE_KEY = "stage";
const BACKEND_STATE_DISPLAY_SYLLABUS_FLAG_KEY = "display_syllabus_flag";
const BACKEND_STATE_TRANSITION_EXPLAINER_FLAG_KEY = "transition_to_explainer_flag";
const CHAT_API_URL = 'http://127.0.0.1:8001/api/chat/';
const TEMP_UPLOAD_API_URL = 'http://127.0.0.1:8001/api/upload_temp_resource/';
const SESSION_DETAIL_API_URL = (sessionId) => `http://127.0.0.1:8001/api/session/${sessionId}/`;
const STAGE_START = "START";
const STAGE_NEGOTIATING = "NEGOTIATING";
const STAGE_EXPLAINING = "EXPLAINING";
const STAGE_ERROR = "ERROR";
const MAX_FILES_ALLOWED = 10;


// --- Helper Components ---
const CopyButton = ({ textToCopy }) => {
    const [isCopied, setIsCopied] = useState(false);
    const handleCopy = async () => {
        if (!navigator.clipboard) { console.warn('[ChatInterface] Clipboard API not available'); return; }
        try {
            await navigator.clipboard.writeText(textToCopy);
            setIsCopied(true);
            setTimeout(() => setIsCopied(false), 2000);
        } catch (err) { console.error('[ChatInterface] Failed to copy text: ', err); }
    };
    return ( <button onClick={handleCopy} className={`${styles.copyButton} ${isCopied ? styles.copied : ''}`} aria-label={isCopied ? 'Copied' : 'Copy code'} title={isCopied ? 'Copied!' : 'Copy code'}> <CopyIcon copied={isCopied} /> </button> );
};


function ChatInterface({ sessionId, onSessionUpdate }) {
    const [inputValue, setInputValue] = useState('');
    const [visibleChatHistory, setVisibleChatHistory] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [appStage, setAppStage] = useState(STAGE_START);
    const [confirmedSessionId, setConfirmedSessionId] = useState(sessionId);
    const [selectedFiles, setSelectedFiles] = useState([]);

    const chatHistoryRef = useRef(null);
    const textAreaRef = useRef(null);
    const fileInputRef = useRef(null);

    useEffect(() => {
        setConfirmedSessionId(sessionId);
        setSelectedFiles([]);
        const loadSession = async (id) => {
            console.log(`[ChatInterface] Effect: Loading history for session ID: ${id}`);
            setIsLoading(true); setError(null); setVisibleChatHistory([]); setAppStage(STAGE_START); setInputValue('');
            try {
                const response = await axios.get(SESSION_DETAIL_API_URL(id));
                const {
                    history,
                    current_stage,
                    original_resource_filenames = []
                } = response.data;
                
                let formattedHistory = history.map(msg_from_backend => {
                    
                    return {
                        role: msg_from_backend.role,
                        content: msg_from_backend.content,
                        type: msg_from_backend.type // <<< USE THE TYPE FROM BACKEND DIRECTLY
                    };
                });


                if (formattedHistory.length > 0 &&
                    formattedHistory[0].role === 'user' &&
                    original_resource_filenames &&
                    original_resource_filenames.length > 0) {
                    
                    const firstUserMessage = formattedHistory[0];
                    firstUserMessage.type = 'message_with_attachments';
                    firstUserMessage.attachments = original_resource_filenames.map(filename => ({ name: filename }));
                }

                setVisibleChatHistory(formattedHistory);
                setAppStage(current_stage || STAGE_START);
                setConfirmedSessionId(id);
                setError(null);
            } catch (err) {
                console.error("[ChatInterface] Effect: Error loading session history:", err);
                setError(err.response?.data?.error || "Failed to load chat session.");
                setVisibleChatHistory([]); setAppStage(STAGE_ERROR);
            } finally {
                setIsLoading(false);
                textAreaRef.current?.focus();
            }
        };

        if (sessionId) {
            loadSession(sessionId);
        } else {
            setVisibleChatHistory([{ role: 'system', type: 'info', content: "Welcome! I'm excited to help you learn. What topic sparks your curiosity today? If you have any files to share, please attach them now!"}]);
            setAppStage(STAGE_START); setIsLoading(false); setError(null); setInputValue('');
            setConfirmedSessionId(null);
            setSelectedFiles([]);
            textAreaRef.current?.focus();
        }
    }, [sessionId]);

    const adjustTextAreaHeight = useCallback(() => { if (textAreaRef.current) { textAreaRef.current.style.height = 'auto'; const scrollHeight = textAreaRef.current.scrollHeight; textAreaRef.current.style.height = `${scrollHeight}px`; } }, []);
    useEffect(() => { adjustTextAreaHeight(); }, [inputValue, adjustTextAreaHeight]);
    useEffect(() => { if (chatHistoryRef.current) { chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight; } }, [visibleChatHistory]);

    const handleInputChange = (event) => { setInputValue(event.target.value); };
    const handleAttachFileClick = () => { if (fileInputRef.current) { fileInputRef.current.value = null; fileInputRef.current.click(); } };

    const handleFileSelection = (event) => {
        const newFileObjects = Array.from(event.target.files);
        if (newFileObjects.length === 0) return;
        const currentNonErrorFilesCount = selectedFiles.filter(f => f.status !== 'error').length;
        const remainingSlots = MAX_FILES_ALLOWED - currentNonErrorFilesCount;
        if (remainingSlots <= 0) { alert(`You can upload a maximum of ${MAX_FILES_ALLOWED} files.`); return; }
        const filesToQueue = newFileObjects.slice(0, remainingSlots).map(fileObj => ({
            id: `file-${Date.now()}-${Math.random().toString(16).slice(2)}`,
            fileObject: fileObj, name: fileObj.name, status: 'queued',
            progress: 0, serverId: null, originalFilename: fileObj.name, errorMessage: null,
        }));
        if (filesToQueue.length < newFileObjects.length) { alert(`Maximum ${MAX_FILES_ALLOWED} files. Some were not added.`); }
        setSelectedFiles(prevFiles => [...prevFiles, ...filesToQueue]);
    };

    const handleRemoveFile = (fileIdToRemove) => { setSelectedFiles(prevFiles => prevFiles.filter(f => f.id !== fileIdToRemove)); };

    useEffect(() => {
        const processFile = async (fileToProcess) => {
            setSelectedFiles(prev => prev.map(f => f.id === fileToProcess.id ? { ...f, status: 'uploading', progress: 0, errorMessage: null } : f ));
            const formData = new FormData(); formData.append('resource_file', fileToProcess.fileObject);
            try {
                await new Promise(resolve => setTimeout(resolve, 200));
                setSelectedFiles(prev => prev.map(f => f.id === fileToProcess.id ? { ...f, progress: 50, status: 'processing' } : f ));
                const response = await axios.post(TEMP_UPLOAD_API_URL, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
                if (response.data?.success) {
                    setSelectedFiles(prev => prev.map(f => f.id === fileToProcess.id ? { ...f, status: 'completed_temp', serverId: response.data.tempServerId, originalFilename: response.data.originalFilename, progress: 100 } : f ));
                } else {
                    setSelectedFiles(prev => prev.map(f => f.id === fileToProcess.id ? { ...f, status: 'error', errorMessage: response.data?.error || 'Backend failure.' } : f ));
                }
            } catch (err) {
                let detailedErrorMessage = "Upload/Processing failed.";
                if (err.response) { detailedErrorMessage = `Server error ${err.response.status}: ${err.response.data?.error || JSON.stringify(err.response.data) || err.message}`; }
                else if (err.request) { detailedErrorMessage = "No response from server for file. Check network."; }
                else { detailedErrorMessage = err.message || "Client-side error during file processing."; }
                setSelectedFiles(prev => prev.map(f => f.id === fileToProcess.id ? { ...f, status: 'error', errorMessage: detailedErrorMessage } : f ));
            }
        };
        const queuedFile = selectedFiles.find(f => f.status === 'queued');
        if (queuedFile && !isLoading) processFile(queuedFile);
    }, [selectedFiles, isLoading]);

    const handleSendMessage = async () => {
        const trimmedInput = inputValue.trim();
        const pendingFiles = selectedFiles.filter(f => ['queued', 'uploading', 'processing'].includes(f.status));
        const completedTempFiles = selectedFiles.filter(f => f.status === 'completed_temp' && f.serverId);

        if ((!trimmedInput && completedTempFiles.length === 0) || isLoading || appStage === STAGE_ERROR) { return; }
        if (pendingFiles.length > 0) { alert("Please wait for files to finish processing."); return; }

        const filesSentWithThisMessage = [...completedTempFiles];
        if (!confirmedSessionId) setSelectedFiles([]); // Clear pre-send FileChips only for new chat send

        let userMessageForDisplay;
        const userMessageContent = trimmedInput || (filesSentWithThisMessage.length > 0 ? "" : "(Message with attachments)");

        if (!confirmedSessionId && filesSentWithThisMessage.length > 0) {
            userMessageForDisplay = {
                role: 'user', content: userMessageContent, type: 'message_with_attachments',
                attachments: filesSentWithThisMessage.map(f => ({ name: f.originalFilename || f.name }))
            };
        } else {
            userMessageForDisplay = { role: 'user', content: userMessageContent, type: 'message' };
        }
        setVisibleChatHistory(prev => [...prev, userMessageForDisplay]);

        setInputValue(''); setIsLoading(true); setError(null);
        if (textAreaRef.current) textAreaRef.current.style.height = 'auto';

        let messageSendSuccess = false; let receivedSessionId = null;
        try {
            const requestPayload = { user_message: userMessageContent, session_id: confirmedSessionId };
            if (!confirmedSessionId && filesSentWithThisMessage.length > 0) {
                requestPayload.temp_resources = filesSentWithThisMessage.map(f => ({
                    tempServerId: f.serverId, originalFilename: f.originalFilename
                }));
            }
            const response = await axios.post(CHAT_API_URL, requestPayload);
            const { ai_reply, new_state, session_id: returnedSessionId } = response.data;
            receivedSessionId = returnedSessionId;

            const newSystemMessages = [];
            const syllabusDataFromState = new_state?.[BACKEND_STATE_DISPLAY_SYLLABUS_FLAG_KEY]; // This is { content: "...", type: "..." }
            if (new_state?.[BACKEND_STATE_STAGE_KEY]) setAppStage(new_state[BACKEND_STATE_STAGE_KEY]);


            if (syllabusDataFromState && syllabusDataFromState.content) {
                console.log("[ChatInterface] Syllabus data from backend state flag:", syllabusDataFromState);
                newSystemMessages.push({
                    role: 'system', // Or 'model', matching how orchestrator sets it
                    // --- USE THE TYPE FROM THE BACKEND'S STATE FLAG ---
                    type: syllabusDataFromState.type, // <<< THIS IS CRUCIAL
                    content: syllabusDataFromState.content
                });
            
            }
            if (ai_reply) newSystemMessages.push({ role: 'ai', content: ai_reply, type: 'message' });
            if (newSystemMessages.length > 0) setVisibleChatHistory(prev => [...prev, ...newSystemMessages]);
            
            messageSendSuccess = true;
        } catch (err) {
            let errorMsg = "An error occurred.";
            if (err.response) { errorMsg = `Server Error ${err.response.status}: ${err.response.data?.error || JSON.stringify(err.response.data)}`; setAppStage(err.response.data?.new_state?.[BACKEND_STATE_STAGE_KEY] || STAGE_ERROR); }
            else if (err.request) { errorMsg = "Cannot reach server."; setAppStage(STAGE_ERROR); }
            else { errorMsg = `Frontend error: ${err.message}`; setAppStage(STAGE_ERROR); }
            setError(errorMsg);
            setVisibleChatHistory(prev => prev.slice(0, -1));
            if (!confirmedSessionId) setSelectedFiles(filesSentWithThisMessage); // Restore pre-send chips on error for new chat
            messageSendSuccess = false;
        } finally {
             if (messageSendSuccess && receivedSessionId) {
                 setConfirmedSessionId(receivedSessionId);
                 if (onSessionUpdate) onSessionUpdate(receivedSessionId);
             }
             setIsLoading(false);
             textAreaRef.current?.focus();
        }
    };

    const handleKeyPress = (event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleSendMessage(); } };

    const renderMessageContent = useCallback((msg) => {
        // This internal function is only for AI/System messages now, or plain user messages
        // The mapping logic in the main return handles the user message with attachments structure.
        const contentString = (typeof msg.content === 'string' || msg.content === null || typeof msg.content === 'undefined') ? (msg.content || "") : JSON.stringify(msg.content);

        if (msg.type === 'internal_resource_summary' || msg.type === 'internal') return null;

        if (msg.type === 'syllabus_markdown') {
                return (
        <>
            <h4>Syllabus Draft/Update</h4>
            <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                    // Use more generic class names tied to HTML element type
                    h2: ({node, ...props}) => <h2 className={styles.syllabusMarkdownH2} {...props} />,
                    h3: ({node, ...props}) => <h3 className={styles.syllabusMarkdownH3} {...props} />,
                    h4: ({node, ...props}) => <h4 className={styles.syllabusMarkdownH4} {...props} />, // If you want to style H4s from Markdown
                    ul: ({node, ...props}) => <ul {...props} />, 
                    li: ({node, ...props}) => <li {...props} />, 
                    strong: ({node, ...props}) => <strong {...props} />, 
                    hr: ({node, ...props}) => <hr {...props} />,
                    // ... existing code component
                    code(props) {
                        // ... (code component as before)
                        const { children, className, node, inline, ...rest } = props;
                        const rawContent = String(children); const trimmedContent = rawContent.trim();
                        const isContentEffectivelySingleLine = !trimmedContent.includes('\n');
                        if (inline || isContentEffectivelySingleLine) { return <code {...rest} className={styles.inlineCode}>{trimmedContent}</code>; }
                        const codeTextForBlock = rawContent.replace(/\n$/, '');
                        const match = /language-(\w+)/.exec(className || ''); const language = match ? match[1] : null;
                        return (<div className={styles.codeBlockWrapper}>
                            <CopyButton textToCopy={codeTextForBlock} />
                            {language ? <SyntaxHighlighter {...rest} style={vscDarkPlus} language={language} PreTag="div" className={styles.codeBlock} showLineNumbers={false} wrapLongLines={true}>{codeTextForBlock}</SyntaxHighlighter>
                                       : <pre {...rest} className={styles.codeBlockPlain}><code>{codeTextForBlock}</code></pre>}
                        </div>);
                    },
                }}
            >
                {contentString}
            </ReactMarkdown>
        </>
    );
}

        if (msg.type === 'info') { return <div className={styles.infoMessageContent}>{contentString}</div>; }

        // If it's a user message but NOT 'message_with_attachments', it's plain text.
        // (The 'message_with_attachments' case is handled directly in the .map() in the JSX return)
        if (msg.role === 'user' && msg.type !== 'message_with_attachments') {
            return <pre className={styles.preformattedText}>{contentString}</pre>;
        }

        if (msg.role === 'ai' || msg.role === 'model') {
            if (/<[^>]+script|<[^>]+\bon\w+=/i.test(contentString)) { return <pre className={styles.preformattedText}>{contentString}</pre>; }
            return (
                <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                    components={{
                        code(props) {
                            const { children, className, node, inline, ...rest } = props;
                            const rawContent = String(children); const trimmedContent = rawContent.trim();
                            const isContentEffectivelySingleLine = !trimmedContent.includes('\n');
                            if (inline || isContentEffectivelySingleLine) { return <code {...rest} className={styles.inlineCode}>{trimmedContent}</code>; }
                            const codeTextForBlock = rawContent.replace(/\n$/, '');
                            const match = /language-(\w+)/.exec(className || ''); const language = match ? match[1] : null;
                            return (<div className={styles.codeBlockWrapper}>
                                <CopyButton textToCopy={codeTextForBlock} />
                                {language ? <SyntaxHighlighter {...rest} style={vscDarkPlus} language={language} PreTag="div" className={styles.codeBlock} showLineNumbers={false} wrapLongLines={true}>{codeTextForBlock}</SyntaxHighlighter>
                                           : <pre {...rest} className={styles.codeBlockPlain}><code>{codeTextForBlock}</code></pre>}
                            </div>);
                        },
                    }}
                >{contentString}</ReactMarkdown> );
        }
        // Fallback for any other unhandled message type/role combination
        return <pre className={styles.preformattedText}>{contentString}</pre>;
    }, []);

    const getPlaceholderText = () => { /* ... as before ... */ 
        switch (appStage) {
            case STAGE_EXPLAINING: return "Ask about the current topic...";
            case STAGE_NEGOTIATING: case STAGE_START:
                return !confirmedSessionId ? "Describe what you want to learn, or attach files..." : "Describe what you want to learn...";
            case STAGE_ERROR: return "An error occurred. Try starting a new chat.";
            default: return "Type your message...";
        }
    };

    const pendingFileUpload = selectedFiles.some(f => ['queued', 'uploading', 'processing'].includes(f.status));
    const sendButtonDisabled = isLoading || pendingFileUpload ||
                             (!inputValue.trim() && selectedFiles.filter(f => f.status === 'completed_temp').length === 0) ||
                             (appStage === STAGE_ERROR);
    const attachButtonDisabled = isLoading || !!confirmedSessionId || selectedFiles.filter(f => f.status !== 'error').length >= MAX_FILES_ALLOWED;

    return (
        <div className={styles.chatContainer}>
            <div className={styles.chatHistory} ref={chatHistoryRef}>
                {isLoading && visibleChatHistory.length === 0 && ( <div className={styles.loading}>Loading chat history...</div> )}
                
                {visibleChatHistory.map((msg, index) => {
                    const key = `${confirmedSessionId || 'new'}-${index}`;

                    if (msg.role === 'user' && msg.type === 'message_with_attachments' && msg.attachments?.length > 0) {
                        return (
                            <React.Fragment key={key}>
                                <div className={`${styles.message} ${styles.userMessage} ${styles.attachmentBlockWrapper}`}>
                                    <div className={styles.messageAttachmentsContainer}>
                                        {msg.attachments.map((attachment, attachIndex) => (
                                            <div key={attachIndex} className={styles.messageAttachmentChip}>
                                                <span className={styles.attachmentIcon}><DocumentIcon /></span>
                                                <span className={styles.attachmentName}>{attachment.name}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                {(msg.content && msg.content.trim()) && ( // Only render text bubble if there's text
                                    <div className={`${styles.message} ${styles.userMessage}`}>
                                        <div className={styles.messageContent}>
                                            <pre className={styles.preformattedText}>{msg.content}</pre>
                                        </div>
                                    </div>
                                )}
                            </React.Fragment>
                        );
                    } else {
                        // Standard message rendering for AI, System, and plain User messages
                        const messageClasses = [ styles.message, msg.role === 'user' ? styles.userMessage : '', (msg.role === 'ai' || msg.role === 'model') ? styles.aiMessage : '', msg.role === 'system' ? styles.systemMessage : '', msg.type === 'syllabus' ? styles.syllabusMessage : '', msg.type === 'info' ? styles.infoMessage : '' ].filter(Boolean).join(' ');
                        const renderedContent = renderMessageContent(msg); // This will now handle AI/System/plain User
                        return renderedContent ? ( <div key={key} className={messageClasses}><div className={styles.messageContent}>{renderedContent}</div></div> ) : null;
                    }
                })}

                {isLoading && visibleChatHistory.length > 0 && ( <div className={`${styles.message} ${styles.aiMessage}`}> <div className={styles.messageContent}><div className={styles.loadingIndicator}><span>AI is thinking...</span></div></div> </div> )}
            </div>

            {selectedFiles.length > 0 && !confirmedSessionId && (
                <div className={styles.selectedFilesContainer}>
                    {selectedFiles.map((fileState) => (
                        <FileChip
                            key={fileState.id}
                            file={fileState}
                            onRemove={() => handleRemoveFile(fileState.id)}
                        />
                    ))}
                </div>
            )}

            {error && <div className={styles.errorDisplay}>{error}</div>}

            <div className={styles.inputArea}>
                {!confirmedSessionId && (
                    <button
                        onClick={handleAttachFileClick}
                        className={styles.attachButton}
                        disabled={attachButtonDisabled}
                        aria-label="Attach files"
                        title={selectedFiles.filter(f=>f.status !== 'error').length >= MAX_FILES_ALLOWED ? `Maximum ${MAX_FILES_ALLOWED} files` : "Attach files"}
                    >
                        <PaperclipIcon />
                    </button>
                )}
                <input type="file" multiple ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileSelection} accept=".pdf,.txt,.docx,.md,text/markdown" />
                 <textarea
                    ref={textAreaRef}
                    className={styles.inputField}
                    value={inputValue}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyPress}
                    placeholder={getPlaceholderText()}
                    rows={1}
                    disabled={isLoading || appStage === STAGE_ERROR}
                    aria-label="Chat message input"
                 />
                 <button
                    className={styles.sendButton}
                    onClick={handleSendMessage}
                    disabled={sendButtonDisabled}
                    aria-label="Send message"
                 >
                     <SendIcon />
                 </button>
            </div>
        </div>
    );
}

export default ChatInterface;