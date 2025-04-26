// src/DeleteConfirmationModal.jsx
import React, { useEffect, useRef } from 'react';
import styles from './DeleteConfirmationModal.module.css';

function DeleteConfirmationModal({ isOpen, onClose, onConfirm, sessionTitle }) {
    const modalRef = useRef(null);

    // Handle closing with Escape key
    useEffect(() => {
        const handleKeyDown = (event) => {
            if (event.key === 'Escape') {
                onClose();
            }
        };
        if (isOpen) {
            document.addEventListener('keydown', handleKeyDown);
            // Optional: Focus the cancel button on open
            const cancelButton = modalRef.current?.querySelector(`.${styles.cancelButton}`);
            cancelButton?.focus();
        } else {
            document.removeEventListener('keydown', handleKeyDown);
        }
        // Cleanup listener on unmount or when isOpen changes
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [isOpen, onClose]);

    // Handle closing when clicking outside the modal content
    const handleOverlayClick = (event) => {
        if (modalRef.current && !modalRef.current.contains(event.target)) {
            onClose();
        }
    };

    if (!isOpen) {
        return null; // Don't render anything if not open
    }

    return (
        <div className={styles.modalOverlay} onClick={handleOverlayClick} role="presentation">
            <div
                ref={modalRef}
                className={styles.modalContent}
                role="dialog"
                aria-modal="true"
                aria-labelledby="delete-modal-title"
                aria-describedby="delete-modal-description"
            >
                <h2 id="delete-modal-title" className={styles.modalTitle}>Delete chat?</h2>
                <p id="delete-modal-description" className={styles.modalDescription}>
                    This will delete{' '}
                    <strong>{sessionTitle || 'this chat'}</strong>.
                </p>
                {/* Optional: Add extra warning text if needed */}
                {/* <p className={styles.modalWarning}>Any memories saved during this chat will be forgotten.</p> */}
                <div className={styles.modalActions}>
                    <button onClick={onClose} className={styles.cancelButton}>
                        Cancel
                    </button>
                    <button onClick={onConfirm} className={styles.deleteButton}>
                        Delete
                    </button>
                </div>
            </div>
        </div>
    );
}

export default DeleteConfirmationModal;