import React from 'react';
import styles from './FileChip.module.css';

// --- Icons ---
// Generic File Icon (can be enhanced later for specific types)
const FileIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
        <path d="M6 2h8l6 6v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm0 2v16h12V9h-5V4H6zm2 10h8v2H8v-2z" />
    </svg>
);

// Close Icon for removing the chip
const CloseIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
        <path d="M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8 2.146 2.854Z" />
    </svg>
);

// Spinner Icon for processing/uploading (simple animated SVG or use a library)
const SpinnerIcon = () => (
    <svg className={styles.spinnerAnimation} width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
        <path d="M12 2.99988V5.99988M12 18V21M21 12H18M6 12H3M18.364 5.63574L16.2427 7.75701M7.75739 16.2426L5.63607 18.3639M18.364 18.3639L16.2427 16.2426M7.75739 7.75701L5.63607 5.63574" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
);

// Completed Icon
const CompletedIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
        <path d="M9.00004 16.1698L4.83004 11.9998L3.41004 13.4098L9.00004 18.9998L21.0000 6.99984L19.5900 5.58984L9.00004 16.1698Z" />
    </svg>
);

// Error Icon
const ErrorIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
    </svg>
);


function getFileDisplayType(fileObject) {
    if (!fileObject || !fileObject.name) return 'File';
    const name = fileObject.name.toLowerCase();
    if (name.endsWith('.pdf')) return 'PDF';
    if (name.endsWith('.txt')) return 'Text';
    if (name.endsWith('.md')) return 'Markdown';
    if (name.endsWith('.docx')) return 'Document';
    return 'File'; // Fallback
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}


function FileChip({ file, onRemove }) {
    if (!file || !file.fileObject) return null; // Ensure file and fileObject exist

    const { name, status, progress, errorMessage, fileObject } = file;

    const renderStatusIndicator = () => {
        switch (status) {
            case 'queued':
                return <div className={styles.statusIconWrapper} title="Queued for upload"><FileIcon /></div>;
            case 'uploading':
                return (
                    <div className={styles.statusIconWrapper} title={`Uploading: ${progress}%`}>
                        <SpinnerIcon />
                        {/* Optional: Show progress text if design allows */}
                        {/* <span className={styles.progressText}>{progress}%</span> */}
                    </div>
                );
            case 'processing':
                return <div className={styles.statusIconWrapper} title="Processing on server"><SpinnerIcon /></div>;
            case 'completed':
                return <div className={styles.statusIconWrapper} title="Successfully processed"><CompletedIcon /></div>;
            case 'error':
                return <div className={styles.statusIconWrapper} title={`Error: ${errorMessage || 'Unknown error'}`}><ErrorIcon /></div>;
            default:
                return <div className={styles.statusIconWrapper}><FileIcon /></div>;
        }
    };

    return (
        <div
            className={`${styles.fileChip} ${styles[status] || styles.queued}`}
            title={status === 'error' ? `Error: ${errorMessage || 'Failed to process'}` : name}
        >
            <div className={styles.statusIndicator}>
                {renderStatusIndicator()}
            </div>

            <div className={styles.fileInfo}>
                <span className={styles.fileName}>
                    {name.length > 20 ? `${name.substring(0, 18)}...` : name}
                </span>
                <span className={styles.fileMeta}>
                    {getFileDisplayType(fileObject)} • {formatFileSize(fileObject.size)}
                </span>
            </div>

            <button
                onClick={() => onRemove(file.id)}
                className={styles.removeButton}
                aria-label={`Remove ${name}`}
                title={`Remove ${name}`}
                disabled={status === 'uploading' || status === 'processing'} // Prevent removal during active operations
            >
                <CloseIcon />
            </button>
        </div>
    );
}

export default FileChip;