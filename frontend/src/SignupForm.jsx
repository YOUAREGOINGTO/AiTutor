// src/SignupForm.jsx
import React, { useState } from 'react';
import styles from './AuthModal.module.css'; // Reuse modal styles

function SignupForm({ onSwitchMode, onSignupSuccess }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError('Passwords do not match.');
            return;
        }
        if (!apiKey.trim()) {
             setError('Google AI API Key is required.');
             return;
        }

        setIsLoading(true);

        // --- Placeholder for actual API call ---
        console.log("Attempting signup with:", { email, password, apiKey });
        await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate network delay

        // Simulate success
        onSignupSuccess({ email: email, /* include token/other data later */ });

        // Simulate failure example (uncomment to test)
        // setError('Username already exists.');
        // setIsLoading(false);

        // In real implementation, handle API errors, set isLoading false in catch block etc.
        // --- End Placeholder ---
    };

    return (
        <form onSubmit={handleSubmit} className={styles.authForm}>
            {error && <p className={styles.errorMessage}>{error}</p>}
            <div className={styles.inputGroup}>
                <label htmlFor="signup-email">Email</label>
                <input
                    type="text"
                    id="signup-email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                />
            </div>
             <div className={styles.inputGroup}>
                <label htmlFor="signup-password">Password</label>
                <input
                    type="password"
                    id="signup-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8} // Example validation
                    disabled={isLoading}
                />
            </div>
            <div className={styles.inputGroup}>
                <label htmlFor="signup-confirm-password">Confirm Password</label>
                <input
                    type="password"
                    id="signup-confirm-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    disabled={isLoading}
                />
            </div>
             <div className={styles.inputGroup}>
                <label htmlFor="signup-api-key">Google AI API Key</label>
                <input
                    type="password" // Use password type to obscure key
                    id="signup-api-key"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    required
                    disabled={isLoading}
                    placeholder="Enter your Gemini API Key"
                    aria-describedby="api-key-description"
                />
                 <p id="api-key-description" className={styles.apiKeyDescription}>
                    Needed for AI features. Get yours from{' '}
                    <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer">
                        Google AI Studio
                    </a>.
                 </p>
            </div>
            <button type="submit" className={styles.submitButton} disabled={isLoading}>
                {isLoading ? 'Creating account...' : 'Sign up'}
            </button>
            <p className={styles.switchModeText}>
                Already have an account?{' '}
                <button type="button" onClick={onSwitchMode} className={styles.switchModeButton}>
                    Log in
                </button>
            </p>
        </form>
    );
}

export default SignupForm;