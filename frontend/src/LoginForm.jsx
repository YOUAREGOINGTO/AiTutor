// src/LoginForm.jsx
import React, { useState } from 'react';
import styles from './AuthModal.module.css'; // Reuse modal styles for form elements

function LoginForm({ onSwitchMode, onLoginSuccess }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        // --- Placeholder for actual API call ---
        console.log("Attempting login with:", { email, password });
        await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate network delay

        // Simulate success/failure
        if (email === 'test' && password === 'password') {
             // Simulate successful login - App.jsx will handle actual state
            onLoginSuccess({ email: email, /* include token/other data later */ });
        } else {
            setError('Invalid email or password.');
            setIsLoading(false);
        }
        // In real implementation, handle API errors, set isLoading false in catch block etc.
        // --- End Placeholder ---
    };

    return (
        <form onSubmit={handleSubmit} className={styles.authForm}>
            {error && <p className={styles.errorMessage}>{error}</p>}
            <div className={styles.inputGroup}>
                <label htmlFor="login-email">Email</label>
                <input
                    type="text"
                    id="login-email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                />
            </div>
            <div className={styles.inputGroup}>
                <label htmlFor="login-password">Password</label>
                <input
                    type="password"
                    id="login-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={isLoading}
                />
            </div>
            <button type="submit" className={styles.submitButton} disabled={isLoading}>
                {isLoading ? 'Logging in...' : 'Log in'}
            </button>
            <p className={styles.switchModeText}>
                Don't have an account?{' '}
                <button type="button" onClick={onSwitchMode} className={styles.switchModeButton}>
                    Sign up
                </button>
            </p>
        </form>
    );
}

export default LoginForm;