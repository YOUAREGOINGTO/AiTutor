# AI Tutor Project


A personalized AI learning assistant that **helps** to accelerate individual learning.
---

**Table of Contents**
*   [What is AI Tutor?](#what-is-ai-tutor)
*   [Why Use This AI Tutor?](#why-use-this-ai-tutor)
*   [Features](#features)
*   [How It Works (The Gist)](#how-it-works-the-gist)
*   [Getting Started](#getting-started)
    *   [Prerequisites](#prerequisites)
    *   [Installation](#installation)
    *   [Running the Application](#running-the-application)
    *   [Stopping the Application](#stopping-the-application)
*   [A Deeper Dive: How AI Tutor Works](#a-deeper-dive-how-ai-tutor-works)
    *   [Core Components](#core-components)
    *   [Effective Use Cases & Tips](#effective-use-cases--tips)
*   [Future Improvements](#future-improvements)
*   [Contributing](#contributing)
*   [License](#license)

---

## What is AI Tutor?
This project is an AI powered tutor designed to provide a personalized learning experience. You can define what you want to learn, provide resources (like documents or books), and the AI will help generate a structured syllabus and interact with you in a specific persona to teach you the material.

## Why Use This AI Tutor?

Traditional Large Language Models (LLMs) are incredibly knowledgeable but can sometimes lack depth on specific topics unless guided precisely. They also tend to have a fixed interaction style once a session begins. This AI Tutor aims to address these points by:
1.  **Focused Learning:** Creating a detailed syllabus based on your input and resources, ensuring the AI stays on track and provides in-depth explanations.
2.  **Adaptive Persona:** Allowing you to define the teaching style (e.g., Socratic, first-principles, like a famous figure) for a more engaging and effective learning experience.
    *(Currently, the persona is set per chat session, with future ideas for dynamic  updates.)*

## Features
*   Personalized syllabus generation based on user goals and optional resources.
*   Customizable teaching persona for the AI Explainer Agent.
*   Interactive conversation manager to clarify learning objectives.
*   Backend API built with Django and a frontend interface with React.
*   Proper rendering of code and math formulas in explanations.
*   SQLite database for easy setup.
*   Designed for topics requiring deep thinking and understanding.

## How It Works (The Gist)

The AI Tutor operates through a workflow involving several key steps:
1.  **Conversation Manager:** Talks with you to understand *what* you want to learn and *why* you want to learn.It **takes** summaries of resources you **provide** and **negotiates** the syllabus with you.You **can** modify it after the syllabus **is generated**.
2.  **Syllabus Generator:** Based on your conversation and resources, it creates a structured learning plan.
3.  **Persona Prompt Generator:** Helps define the "personality" and teaching style of the Explainer Agent. You guide this by describing how you want to be taught. This is the single most important step.
4.  **Explainer Agent:** This is the AI that actually teaches you, following the generated syllabus and adopting the defined persona.

You can start a new chat to redefine the syllabus or persona if needed.

## Getting Started

### Prerequisites
Before you begin, ensure you have the following installed:
*   **Git:** [Download Git]
*   **Python 3.10+:** [Download Python]
    *   *Important:* During Python installation, ensure "Add Python to PATH" is checked.
*   **Node.js (LTS):** [Download Node.js]
    *   npm (Node Package Manager) is included. Ensure "Add to PATH" is checked during installation.

### Installation
Follow these steps to set up the project on your Windows machine using Command Prompt.

**PART 1: CLONE THE PROJECT**

1.  Open Command Prompt.
2.  Navigate to where you want to store the project (e.g., your user's Documents folder):
    ```cmd
    cd %USERPROFILE%\Documents
    ```
    Or, to create and navigate to a new directory:
    ```cmd
    mkdir MyProjects && cd MyProjects
    ```
3.  Clone the repository (replace `<repository_url>` with your actual GitHub URL):
    ```cmd
    git clone <repository_url> 
    
4.  Navigate into the cloned project's root directory :
    ```cmd
    cd AiTutor
    ```
   

**PART 2: BACKEND SETUP (Django with SQLite)**

5.  Navigate into the backend directory:
    ```cmd
    cd backend
    ```
6.  Create a Python virtual environment:
    ```cmd
    python -m venv venv
    ```
7.  Activate the virtual environment:
    ```cmd
    .\venv\Scripts\activate
    ```
    (You should see `(venv)` at the start of your prompt.)
8.  Install Python dependencies:
    ```cmd
    pip install -r requirements.txt
    ```
9.  Create the `.env` file for backend environment variables by copying the example:
    ```cmd
    copy .env.example .env
    ```
10. **MANUAL STEP: Configure Environment Variables**
    Open `backend\.env` in a text editor (like Notepad, VS Code, etc.).
    ```cmd
    notepad .env
    ```
    You **MUST** fill in your actual values for:
    *   `DJANGO_SECRET_KEY="your_very_strong_random_secret_key_here"` (Optional for local development; required and must be unique/secret for production environments)
    *   `GEMINI_API_KEY="your_google_gemini_api_key_here"` (Get this from Google AI Studio)
    Save and close the file.
11. Create the SQLite database and apply migrations:
    ```cmd
    python manage.py makemigrations api
    python manage.py migrate
    ```
12. Create a Django superuser for accessing the admin panel (`/admin`):
    ```cmd
    python manage.py createsuperuser
    ```
    (This allows access to the Django admin panel, where you can, for example, view/copy the Explainer Agent's system prompt)
    
13. (Optional but Recommended) Create media subdirectories if they are not automatically handled by your `settings.py`:
    ```cmd
    IF NOT EXIST "media" mkdir "media"
    IF NOT EXIST "media\uploaded_resources" mkdir "media\uploaded_resources"
    IF NOT EXIST "media\temp_chat_uploads" mkdir "media\temp_chat_uploads"
    ```
    The backend setup is mostly complete. Keep this terminal open (with `venv` activated) to run the backend server later.

**PART 3: FRONTEND SETUP (React)**

14. Open a **NEW, SEPARATE** Command Prompt.
15. Navigate into the project's root directory (e.g., `AiTutor`):
    ```cmd
    cd %USERPROFILE%\Documents\AiTutor
    ```
    (Adjust path if you cloned it elsewhere.)
16. Navigate into the frontend directory:
    ```cmd
    cd frontend
    ```
17. Install Node.js dependencies:
    ```cmd
    npm install
    ```
    The frontend setup is complete. Keep this terminal open to run the frontend server.

### Running the Application

18. **In the FIRST Command Prompt (Backend):**
    *   Ensure you are in the `AiTutor\backend` directory.
    *   Ensure the virtual environment is still active (you should see `(venv)`). If not, reactivate: `.\venv\Scripts\activate`
    *   Start the Django development server using Uvicorn:
        ```cmd
        uvicorn tutor_project.asgi:application --reload --port 8001
        ```
    You should see output indicating the server is running on `http://127.0.0.1:8001/`.

19. **In the SECOND Command Prompt (Frontend):**
    *   Ensure you are in the `AiTutor\frontend` directory.
    *   Start the React development server:
        ```cmd
        npm run dev
        ```
    You should see output indicating the server is running, usually on `http://localhost:3001/` (the terminal will often say: "Local: http://localhost:3001/").

20. Open your web browser and navigate to the frontend URL (e.g., `http://localhost:3001`).

### Stopping the Application
*   In each Command Prompt window (backend and frontend), press `CTRL+C`.
*   Confirm if asked (usually by pressing 'Y' then Enter).
*   To deactivate the Python virtual environment in the backend terminal (optional, as it deactivates on close):
    (Run this while in the `backend` directory with `venv` active)
    ```cmd
    deactivate
    ```
21. Change the folder  addresses in AI Tutor.bat and run_backend.bat to open this project in one click.
Move AI Tutor.bat to your desired **shortcut** folder location. If you click on **it**, the project **will be** opened, **provided** you have configured the **addresses** properly.
**Batch File Configuration:**

To use the provided `.bat` scripts for one-click startup, you'll need to update a few path variables within them:

*   **In `AI Tutor.bat`:**
    *   `set BACKEND_DIR="your_path_to_project_root\backend"`
    *   `set FRONTEND_DIR="your_path_to_project_root\frontend"`
    *   `set DESKTOP_DIR="%USERPROFILE%\Desktop"` (Usually fine as is, or change if you want the shortcut elsewhere)

*   **In `run_backend.bat`:**
    *   `VENV_ACTIVATE_SCRIPT="your_path_to_project_root\backend\venv\Scripts\activate.bat"`
    *   `BACKEND_DIR="your_path_to_project_root\backend"`
    *   `UVICORN_EXE="your_path_to_project_root\backend\venv\Scripts\uvicorn.exe"`

Replace `"your_path_to_project_root"` with the actual absolute path to where you cloned the `AiTutor` project.

22. The project **includes rate limiting**, configured in backend/api/async_rate_limiter.py. If you **want** to use your personal paid-tier API key **without these limits**, **set the relevant rate limit values to 0 or a very high number (or disable it, depending on implementation)**.

23. This project uses DSpy for prompting.** This approach is advantageous if you intend to switch LLM providers, as DSpy's features, such as prompt optimizers, allow for tailoring prompts to specific models, while its abstractions simplify working with different model APIs


---

## A Deeper Dive: How AI Tutor Works


LLMs have vast knowledge, but making them act as effective, specialized tutors requires addressing a few challenges:
1.  **Depth vs. Breadth:** LLMs often need precise guidance to provide in-depth knowledge on specific topics rather than general overviews.
2.  **Static Prompts:** Once a system prompt (which defines the AI's behavior, knowledge base, and persona) is set, it's typically fixed for that interaction.

This project tackles these issues through a structured workflow:

### Core Components

1.  **Conversation Manager (`Convo Manager`)**
    *   **Role:** Interacts with the user to understand their learning goals: *what* they want to learn, *why* (optional), and how (teaching style preferences. The "how" is **further refined** by the Persona Prompt Generator).
    *   **Resource Handling:** If resources are provided, it generates an initial summary.
    *   **Control Flow:** Manages the conversation flow, asking clarifying questions (temperature can be adjusted to reduce chattiness) and producing tags  (e.g., generate , modify , finalize , persona) to trigger subsequent agents like the Syllabus Generator and Persona Generator.

2.  **Syllabus Generator**
    *   **Input:** User's learning objectives (from Convo Manager) and any provided resources.
    *   **Process:**
        *   **No Resources:** Uses a specific prompt to generate a syllabus from scratch.
        *   **With Resources:** For large resources, it truncates text (e.g., to 100,000 chars per resource) and creates a "Dynamic Summary" (considering user history) before generating the syllabus.
        *   *(Note: Performance with heavy resources can be enhanced with more powerful models or paid tiers by tweaking code in orchestrator & Dynamic Resource Generation.)*
    *   **Output:** A structured syllabus, which the user can then ask to modify.

3.  **Persona Prompt Generator**
    *   **Trigger:** Activates after the syllabus is finalized.
    *   **Goal:** Defines the teaching style and "personality" of the Explainer Agent. This is a critical step for an effective learning experience.
    *   **User Input:** The user describes how they want to be taught.
        *   **Effective Answers:** Focus on pedagogical approaches (e.g., First Principle Thinking, Socratic method), emulate learning styles of great thinkers (past/present) or even fictional characters. Aim for a serious, efficient teaching style, not overly pleasing. Mentioning "search capabilities" or other tool use can be integrated if using other platforms like Google AI Studio with grounding.
        *   **Example:** "Teach me with Socratic questioning, focusing on first principles. **Be** serious and ensure I understand the fundamentals before moving on. You have search capabilities to verify facts(Helpful for Tool Calling)."
    *   **Output:** A system prompt for the Explainer Agent, generated by `PersonaPromptBodyPredictSignature` based on chat history and the user's persona description.
    *   *(Note: A good persona prompt is key. A generic one often leads to a subpar learning experience.)*

4.  **Explainer Agent**
    *   **Input:** The system prompt (syllabus + persona) generated previously.
    *   **Role:** Greets the user and begins teaching according to the syllabus and defined persona.
    *   **Features:** Renders code and mathematical formulas correctly.
    *   **Portability:** The system prompt can be copied from the admin panel **to be used** in other LLM interfaces like Google AI Studio

### Effective Use Cases & Tips

*   **Ideal Topics (based on experience):**
    *   Subjects requiring deep conceptual understanding where visual/audio aids are not primary (e.g., learning music theory concepts is okay, but learning an instrument is not ideal for this text-based version).and also not optimal for Topics where you need extreme precision from a preferred resource.
    *   Examples: Increasing cognitive ability, learning Chess & Go strategies, understanding brain control concepts, developing a competitive spirit.
    *  **Technical Topics:** Revising classic machine learning, exploring advanced Reinforcement Learning (e.g., using Barto & Sutton as a resource and AI Studio(can handle large files) for syllabus creation) and  understanding codebases.
*   **Performance:** Generally strong for conceptual/philosophical topics. For highly technical subjects, see "Improvements" below.
*   **Resource Limitation:** Currently, resources can only be provided at the start of a conversation.

---

## Future Improvements

**Technical Improvements:**
1.  **RAG for Explainer Agent:** Implementing Retrieval Augmented Generation (RAG) for the Explainer Agent could significantly improve performance for technical topics by grounding explanations in specific documents.
    *   *Challenge:* Self-hosting effective RAG models can be difficult. My testing indicates that smaller models (e.g., 1B parameters) often yield lower accuracy (frequently below 50% for relevant tasks), while larger, more accurate models (e.g., 7B+) demand significantly more computational resources.
**Other Improvements:**
1.  **Prompt Engineering:**
    *   Some prompts (e.g., `FormatSyllabusXMLToMarkdown`) are quite long and could be refined or made optional.
    *   The `Convo Manager`'s questioning style could be more adaptable.
    *   The `Persona Prompt Generator` could be more "agentic" (multi-step, iterative refinement) rather than a single-step generation.
2.  **UI/UX Enhancements:**
    *   Displaying the current system prompt (syllabus + persona) clearly to the user.
    *   Visual cues for transitions between stages (Convo > Syllabus > Persona > Explainer).
    *   General UI polish.

---

## Contributing

We welcome contributions! Please feel free to fork the repository, make your changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

Ensure your code adheres to the existing style.

---

## License
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.