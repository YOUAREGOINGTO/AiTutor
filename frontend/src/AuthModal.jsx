// src/AuthModal.jsx
import React from 'react';
import styles from './AuthModal.module.css';
import LoginForm from './LoginForm'; // We'll create this next
import SignupForm from './SignupForm'; // We'll create this next

// Close Icon SVG
const CloseIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M18.364 5.63604C18.7565 6.02856 18.7565 6.66173 18.364 7.05425L13.4142 12L18.364 16.9457C18.7565 17.3383 18.7565 17.9714 18.364 18.364C17.9714 18.7565 17.3383 18.7565 16.9457 18.364L12 13.4142L7.05425 18.364C6.66173 18.7565 6.02856 18.7565 5.63604 18.364C5.24351 17.9714 5.24351 17.3383 5.63604 16.9457L10.5858 12L5.63604 7.05425C5.24351 6.66173 5.24351 6.02856 5.63604 5.63604C6.02856 5.24351 6.66173 5.24351 7.05425 5.63604L12 10.5858L16.9457 5.63604C17.3383 5.24351 17.9714 5.24351 18.364 5.63604Z" fill="currentColor"/>
    </svg>
);


function AuthModal({ isOpen, onClose, mode, onSwitchMode, onAuthSuccess }) {

    if (!isOpen) return null;

    const handleOverlayClick = (e) => {
        // Close if clicking directly on the overlay, not the content
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    const handleAuthSuccess = (userData) => {
        console.log(`${mode} successful:`, userData); // Simulate
        onAuthSuccess(userData); // Pass data up to App.jsx
        onClose(); // Close modal on success
    };

    return (
        <div className={styles.modalOverlay} onClick={handleOverlayClick} role="presentation">
            <div className={styles.modalContent} role="dialog" aria-modal="true">
                <button onClick={onClose} className={styles.closeButton} aria-label="Close dialog">
                    <CloseIcon />
                </button>

                {mode === 'login' ? (
                    <>
                        <h2 className={styles.modalTitle}>Welcome back</h2>
                        <LoginForm
                            onSwitchMode={() => onSwitchMode('signup')}
                            onLoginSuccess={handleAuthSuccess} // Simulate success
                        />
                    </>
                ) : (
                    <>
                        <h2 className={styles.modalTitle}>Create your account</h2>
                        <SignupForm
                            onSwitchMode={() => onSwitchMode('login')}
                            onSignupSuccess={handleAuthSuccess} // Simulate success
                        />
                    </>
                )}
            </div>
        </div>
    );
}

export default AuthModal;