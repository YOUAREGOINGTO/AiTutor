import dspy
class FormatSyllabusXMLToMarkdown(dspy.Signature):
    """"
    You are an expert data transformation AI. Your sole function is to convert learning syllabus content, which may be provided in XML format or as pre-formatted text, into clean, hierarchically structured, and well-formatted Markdown. Given the detailed examples and structure, a low temperature (e.g., 0.3) is appropriate for consistent output.

    **Key Conversion Rules:**

    1.  **Output Format:** The output MUST be exclusively Markdown. Do not include any introductory text, explanations, or conversational wrappers around the Markdown content.
    2.  **Maximum Heading Level:** The highest-level heading in the Markdown output (typically for "Phases" or main sections) MUST be `##`. Do NOT use `#` (H1) for any titles.
    3.  **Hierarchical Structure & Title Formatting:**
        *   **Main Sections (e.g., Phases, Modules) - Output as `## Title`:**
            *   **From XML:** If the input is `<phase><title>Actual Title</title></phase>`, convert to `## Actual Title`.
                *   Example: `<phase><title>Foundations of AI</title></phase>` becomes `## Foundations of AI`.
                *   Example: `<phase><title>Phase 1 - Getting Started</title></phase>` becomes `## Phase 1 - Getting Started`.
            *   **From Text Input (e.g., lines starting with `# Phase:`, `## Module:`, or just `# Title`):**
                *   If the input line is like `# Phase: Advanced Topics` (where "Advanced Topics" is descriptive and not just "Phase X"), convert to `## Phase: Advanced Topics`. The prefix ("Phase:", "Module:", etc.) is kept.
                *   If the input line is like `# Module 1 Concepts` (where there's no explicit "Module:" prefix but the title itself indicates it), convert to `## Module 1 Concepts`.
                *   **Avoid Redundancy:** If the input line is like `# Phase: Phase 1` or `## Module: Module A`, simplify the output to `## Phase 1` or `## Module A` respectively. The goal is to avoid `## Phase: Phase 1`.
            *   **Implicitly Defined Sections (by `---` separator without title):** Number them sequentially, e.g., `## Phase 1`, `## Phase 2`.
        *   **Sub-Sections (e.g., Lessons, Topics, Units) - Output as `### Title`:** (Apply similar logic)
            *   **From XML:** `<lesson><topic>Actual Topic</topic></lesson>` becomes `### Actual Topic`.
            *   **From Text Input (e.g., `## Lesson:`, `### Unit:`, or just `## Topic Name`):**
                *   If input is `## Lesson: Understanding Functions` (descriptive title), convert to `### Lesson: Understanding Functions`.
                *   If input is `### Unit Details` (no prefix), convert to `### Unit Details`.
                *   **Avoid Redundancy:** If input is `## Lesson: Lesson 3` or `### Topic: Topic B`, simplify to `### Lesson 3` or `### Topic B`.
            *   **Initial Items:** If lesson-like items appear at the very beginning of a text input *before* any main section (`##`) or separator, list them directly using `###` headings.
    4.  **Lesson/Topic Content (e.g., Keywords, Objective, Focus, Key Ideas, Goal, Core Content):**
        *   For XML elements like `<keywords>...</keywords>`, `<objective>...</objective>`, `<focus>...</focus>`:
            *   Format as:
                `**Keywords:** [Content of keywords tag]`
                `**Objective:** [Content of objective tag]`
                `**Focus:** [Content of focus tag]`
        *   For text input lines like `- **Keywords:** ...` or `**Objective:** ...`:
            *   Preserve the bolded label and its content:
                `**Keywords:** [Content following label]`
                `**Objective:** [Content following label]`
        *   **If a specific content element (like keywords, objective, etc.) is NOT provided for a lesson/topic, completely omit that line from the Markdown output for that lesson/topic.** For example, if there's no `<keywords>` tag or "Keywords:" line, do not print "**Keywords:**" at all.
    5.  **Error and Extraneous Text Handling:** Ignore any error messages (e.g., "Error displaying syllabus...", "BEEPBOOPFIZZ!"), comments, or other non-syllabus text present in the input. Focus solely on extracting and formatting the syllabus structure.
    6.  **Adaptability to Naming:** Be prepared for variations in XML tag names (e.g., `<module>` for `<phase>`, `<unit>` for `<lesson>`) or text labels (e.g., "Module:", "Unit:", "Key Ideas:", "Goal:"). Apply the hierarchical and content formatting rules consistently based on the detected structure. Maintain logical grouping as presented in the input.

    Your task is to process the provided input and generate only the corresponding Markdown.
    Input (Default Expected Format):
    <syllabus>
    <syllabus>
    <phase>
        <title>Phase 1: Foundations and Introduction</title>
        <lesson>
        <topic>Introduction to Neural Networks and Representation Learning</topic>
        <keywords>Representation Learning, NLP, Neural Networks, Sequence Models</keywords>
        <objective>Understand the role of representation learning in NLP and the need for advanced sequence models beyond traditional methods.</objective>
        <focus>Review fundamental concepts of learning representations for sequential data, particularly in the context of natural language processing.</focus>
        </lesson>
        <lesson>
        <topic>Mathematical and Computational Building Blocks</topic>
        <keywords>One-Hot Encoding, Dot Product, Matrix Multiplication, Embeddings</keywords>
        <objective>Become familiar with essential mathematical operations and data encoding techniques fundamental to modern neural network architectures.</objective>
        <focus>Focus on how basic linear algebra and encoding schemes like one-hot and embeddings are used to process data for sequence models.</focus>
        </lesson>
        <lesson>
        <topic>Comparing Transformers to Previous Architectures</topic>
        <keywords>Transformers, RNNs, CNNs, Sequential Processing, Parallel Processing</keywords>
        <objective>Identify the limitations of sequential models (RNNs) and convolutional models (CNNs) when handling long-range dependencies, motivating the need for the Transformer architecture.</objective>
        <focus>Understand the core architectural differences and processing paradigms (sequential vs. parallel) that distinguish Transformers from RNNs and CNNs across various tasks (Language, Vision, Multimodal).</focus>
        </lesson>
    </phase>
    <phase>
        <title>Phase 2: The Attention Mechanism</title>
        <lesson>
        <topic>Understanding Attention in Sequence Models</topic>
        <keywords>Attention, Sequence Modeling, Masking, Dependencies</keywords>
        <objective>Grasp the fundamental concept of attention and how it allows models to weigh the importance of different parts of the input sequence.</objective>
        <focus>Explore how attention mechanisms address the limitations of fixed-context models and capture dependencies, including the role of masking.</focus>
        </lesson>
        <lesson>
        <topic>Self-Attention: The Core Idea</topic>
        <keywords>Self-Attention, Queries, Keys, Values, Scaled Dot-Product Attention</keywords>
        <objective>Learn the mechanics of self-attention, including the roles of queries, keys, and values, and how it enables parallel processing and capturing internal dependencies within a single sequence.</objective>
        <focus>Deep dive into the scaled dot-product self-attention calculation and its significance for the Transformer architecture.</focus>
        </lesson>
        <lesson>
        <topic>Multi-Head and Cross-Attention</topic>
        <keywords>Multi-Head Attention, Cross-Attention, Attention Heads</keywords>
        <objective>Understand how Multi-Head Attention enhances the model's ability to capture diverse relationships and how Cross-Attention facilitates interaction between different sequences (e.g., encoder-decoder).</objective>
        <focus>Examine the benefits of using multiple attention heads and the application of cross-attention in sequence-to-sequence tasks.</focus>
        </lesson>
    </phase>
    <phase>
        <title>Phase 3: Transformer Architecture and Applications</title>
        <lesson>
        <topic>Positional Encoding and Embeddings</topic>
        <keywords>Positional Encoding, Embeddings, Sequence Order</keywords>
        <objective>Understand how embeddings represent tokens and how positional encoding injects information about the position of tokens in the sequence, crucial since attention is permutation-invariant.</objective>
        <focus>Explore different methods for positional encoding and their integration with token embeddings.</focus>
        </lesson>
        <lesson>
        <topic>The Encoder-Decoder Structure</topic>
        <keywords>Encoder-Decoder, Transformer Architecture, Feed-Forward Networks, Residual Connections, Layer Normalization</keywords>
        <objective>Learn the overall architecture of the Transformer model, including the stack of encoder and decoder layers and their internal components (attention, feed-forward networks, skip connections, normalization).</objective>
        <focus>Examine the flow of information through the complete Encoder-Decoder pipeline in a Transformer.</focus>
        </lesson>
        <lesson>
        <topic>Implementation Details and Model Variations</topic>
        <keywords>Tokenization, Implementation, GPT, BERT, Parameter Distribution</keywords>
        <objective>Gain insight into practical aspects like tokenization and understand how the Transformer architecture is adapted in prominent models like BERT and GPT, including parameter distribution.</objective>
        <focus>Discuss practical considerations for implementing and working with Transformer models and analyze variations like encoder-only (BERT) and decoder-only (GPT) architectures.</focus>
        </lesson>
    </phase>
    <phase>
        <title>Phase 4: Analysis and Future Directions</title>
        <lesson>
        <topic>Analysis of Transformer Properties</topic>
        <keywords>Advantages, Disadvantages, Time Complexity, Parallelism, Long-Range Dependencies</keywords>
        <objective>Evaluate the key advantages (parallelism, handling long dependencies) and disadvantages (computational cost, memory) of the Transformer architecture.</objective>
        <focus>Analyze the computational complexity of Transformers compared to RNNs and CNNs, focusing on efficiency gains and limitations.</focus>
        </lesson>
        <lesson>
        <topic>Applications and Future Trends</topic>
        <keywords>NLP Applications, Vision Applications, Multimodal, Future Directions, Efficiency</keywords>
        <objective>Explore the wide range of applications where Transformers have been successful and discuss current research directions and potential future developments.</objective>
        <focus>Survey the impact of Transformers beyond NLP and look at efforts to improve their efficiency and capabilities.</focus>
        </lesson>
    </phase>
    </syllabus>
    </syllabus>

    Output:
    ## Phase 1: Foundations and Introduction

    ### Topic: Introduction to Neural Networks and Representation Learning

    **Keywords:** Representation Learning, NLP, Neural Networks, Sequence Models

    **Objective:** Understand the role of representation learning in NLP and the need for advanced sequence models beyond traditional methods.

    **Focus:** Review fundamental concepts of learning representations for sequential data, particularly in the context of natural language processing.

    ### Topic: Mathematical and Computational Building Blocks

    **Keywords:** One-Hot Encoding, Dot Product, Matrix Multiplication, Embeddings

    **Objective:** Become familiar with essential mathematical operations and data encoding techniques fundamental to modern neural network architectures.

    **Focus:** Focus on how basic linear algebra and encoding schemes like one-hot and embeddings are used to process data for sequence models.

    ### Topic: Comparing Transformers to Previous Architectures

    **Keywords:** Transformers, RNNs, CNNs, Sequential Processing, Parallel Processing

    **Objective:** Identify the limitations of sequential models (RNNs) and convolutional models (CNNs) when handling long-range dependencies, motivating the need for the Transformer architecture.

    **Focus:** Understand the core architectural differences and processing paradigms (sequential vs. parallel) that distinguish Transformers from RNNs and CNNs across various tasks (Language, Vision, Multimodal).

    ## Phase 2: The Attention Mechanism

    ### Topic: Understanding Attention in Sequence Models

    **Keywords:** Attention, Sequence Modeling, Masking, Dependencies

    **Objective:** Grasp the fundamental concept of attention and how it allows models to weigh the importance of different parts of the input sequence.

    **Focus:** Explore how attention mechanisms address the limitations of fixed-context models and capture dependencies, including the role of masking.

    ### Topic: Self-Attention: The Core Idea

    **Keywords:** Self-Attention, Queries, Keys, Values, Scaled Dot-Product Attention

    **Objective:** Learn the mechanics of self-attention, including the roles of queries, keys, and values, and how it enables parallel processing and capturing internal dependencies within a single sequence.

    **Focus:** Deep dive into the scaled dot-product self-attention calculation and its significance for the Transformer architecture.

    ### Topic: Multi-Head and Cross-Attention

    **Keywords:** Multi-Head Attention, Cross-Attention, Attention Heads

    **Objective:** Understand how Multi-Head Attention enhances the model's ability to capture diverse relationships and how Cross-Attention facilitates interaction between different sequences (e.g., encoder-decoder).

    **Focus:** Examine the benefits of using multiple attention heads and the application of cross-attention in sequence-to-sequence tasks.

    ## Phase 3: Transformer Architecture and Applications

    ### Topic: Positional Encoding and Embeddings

    **Keywords:** Positional Encoding, Embeddings, Sequence Order

    **Objective:** Understand how embeddings represent tokens and how positional encoding injects information about the position of tokens in the sequence, crucial since attention is permutation-invariant.

    **Focus:** Explore different methods for positional encoding and their integration with token embeddings.

    ### Topic: The Encoder-Decoder Structure

    **Keywords:** Encoder-Decoder, Transformer Architecture, Feed-Forward Networks, Residual Connections, Layer Normalization

    **Objective:** Learn the overall architecture of the Transformer model, including the stack of encoder and decoder layers and their internal components (attention, feed-forward networks, skip connections, normalization).

    **Focus:** Examine the flow of information through the complete Encoder-Decoder pipeline in a Transformer.

    ### Topic: Implementation Details and Model Variations

    **Keywords:** Tokenization, Implementation, GPT, BERT, Parameter Distribution

    **Objective:** Gain insight into practical aspects like tokenization and understand how the Transformer architecture is adapted in prominent models like BERT and GPT, including parameter distribution.

    **Focus:** Discuss practical considerations for implementing and working with Transformer models and analyze variations like encoder-only (BERT) and decoder-only (GPT) architectures.

    ## Phase 4: Analysis and Future Directions

    ### Topic: Analysis of Transformer Properties

    **Keywords:** Advantages, Disadvantages, Time Complexity, Parallelism, Long-Range Dependencies

    **Objective:** Evaluate the key advantages (parallelism, handling long dependencies) and disadvantages (computational cost, memory) of the Transformer architecture.

    **Focus:** Analyze the computational complexity of Transformers compared to RNNs and CNNs, focusing on efficiency gains and limitations.

    ### Topic: Applications and Future Trends

    **Keywords:** NLP Applications, Vision Applications, Multimodal, Future Directions, Efficiency

    **Objective:** Explore the wide range of applications where Transformers have been successful and discuss current research directions and potential future developments.

    **Focus:** Survey the impact of Transformers beyond NLP and look at efforts to improve their efficiency and capabilities.
    Input(Description There wouldn't be Phases or anything. but based on heirarchy create the markdown properly and also omit errors if any):
    Error displaying syllabus: This page contains the following errors:error on line 1 at column 1: Start tag expected, '<' not foundBelow is a rendering of the page up to the first error.

    # Phase: Introduction to Sequence Transduction and the Transformer
    ## Lesson: Limitations of Recurrent and Convolutional Models
    - **Keywords:** Sequence Transduction, RNN, CNN, Recurrence, Convolution, Parallelization, Sequential Computation
    - **Objective:** Understand the challenges faced by traditional sequence transduction models like RNNs and CNNs, particularly regarding sequential computation and parallelization.
    - **Focus:** This lesson focuses on the inherent sequential nature of recurrent models and the path length issues in convolutional models that limit their efficiency and ability to learn long-range dependencies, motivating the need for a new architecture.
    ## Lesson: Introducing the Transformer Architecture
    - **Keywords:** Transformer, Attention Mechanism, Self-Attention, Sequence Transduction, Parallelization
    - **Objective:** Learn about the Transformer, a novel network architecture that replaces recurrence and convolutions entirely with attention mechanisms.
    - **Focus:** This lesson introduces the core idea of the Transformer: relying solely on attention to draw global dependencies, enabling significantly more parallelization and faster training compared to previous models.
    ---
    # Phase: Core Components of the Transformer
    ## Lesson: Encoder-Decoder Structure
    - **Keywords:** Encoder, Decoder, Stack, Sub-layer, Residual Connection, Layer Normalization
    - **Objective:** Describe the overall encoder-decoder structure of the Transformer and the composition of its stacked layers.
    - **Focus:** This lesson details how the Transformer utilizes an encoder-decoder framework with stacks of identical layers, each featuring sub-layers, residual connections, and layer normalization, as depicted in Figure 1.
    ## Lesson: Attention Function and Scaled Dot-Product Attention
    - **Keywords:** Attention Function, Query, Key, Value, Weighted Sum, Scaled Dot-Product Attention, Softmax, Compatibility Function
    - **Objective:** Explain the fundamental concept of an attention function and the specific implementation used in the Transformer: Scaled Dot-Product Attention.
    - **Focus:** This lesson covers the definition of attention as mapping queries and key-value pairs to a weighted sum of values, focusing on the Scaled Dot-Product Attention formula and the role of scaling by 1/sqrt(dk).
    ## Lesson: Multi-Head Attention
    - **Keywords:** Multi-Head Attention, Linear Projection, Parallel Attention, Representation Subspaces, Concatentation
    - **Objective:** Understand how Multi-Head Attention enhances the model's ability to attend to information from different representation subspaces.
    - **Focus:** This lesson explains the mechanism of Multi-Head Attention, involving projecting queries, keys, and values multiple times in parallel and concatenating the results, highlighting its benefit over single-head attention.
    ## Lesson: Applications of Attention within the Transformer
    - **Keywords:** Encoder-Decoder Attention, Encoder Self-Attention, Decoder Self-Attention, Masking, Auto-regressive
    - **Objective:** Identify the three distinct ways Multi-Head Attention is utilized in the Transformer's encoder and decoder stacks.
    - **Focus:** This lesson details the specific applications: encoder-decoder attention for connecting encoder/decoder outputs, encoder self-attention for processing input sequence dependencies, and masked decoder self-attention for preserving the auto-regressive property.
    ---
    # Phase: Supporting Mechanisms and Training
    ## Lesson: Position-wise Feed-Forward Networks, Embeddings, and Softmax
    - **Keywords:** Feed-Forward Network, ReLU, Embeddings, Softmax, Shared Weights
    - **Objective:** Describe the role of the position-wise feed-forward networks and how input/output tokens are processed using embeddings and a final softmax layer.
    - **Focus:** This lesson covers the independent feed-forward network applied to each position and the standard use of learned embeddings for token representation, including the sharing of weights between embedding layers and the pre-softmax transformation.
    ## Lesson: Positional Encoding
    - **Keywords:** Positional Encoding, Sine, Cosine, Sequence Order, Relative Position, Learned Embeddings
    - **Objective:** Explain why positional encoding is necessary in the Transformer and how the sinusoidal positional encoding is implemented.
    - **Focus:** This lesson focuses on the need to inject positional information due to the absence of recurrence/convolution and describes the use of sine and cosine functions at different frequencies, discussing its potential for extrapolating to longer sequences.
    ## Lesson: Efficiency Analysis: Why Self-Attention?
    - **Keywords:** Computational Complexity, Sequential Operations, Maximum Path Length, Parallelization, Long-Range Dependencies
    - **Objective:** Compare the efficiency of self-attention layers against recurrent and convolutional layers based on computational complexity, sequential operations, and path length.
    - **Focus:** This lesson uses the analysis from the paper (Table 1) to highlight the advantages of self-attention, particularly its constant number of sequential operations and path length, making it highly parallelizable and effective for capturing long-range dependencies.
    ---
    # Phase: Implementation, Results, and Impact
    ## Lesson: Training Setup and Regularization
    - **Keywords:** Training Data, Batching, Optimizer, Learning Rate Schedule, Warmup Steps, Residual Dropout, Label Smoothing
    - **Objective:** Summarize the training methodology, including data preparation, optimizer configuration, learning rate scheduling, and regularization techniques used.
    - **Focus:** This lesson details the practical aspects of training the Transformer, covering the datasets used, batching strategy, the Adam optimizer with a specific learning rate schedule and warmup, and the application of dropout and label smoothing.
    ## Lesson: Machine Translation Performance
    - **Keywords:** Machine Translation, BLEU Score, WMT 2014, State-of-the-Art, Training Cost, Benchmarks
    - **Objective:** Evaluate the Transformer's performance on machine translation tasks based on reported BLEU scores and training costs compared to existing models.
    - **Focus:** This lesson presents the key results from the paper (Table 2), demonstrating that the Transformer achieves new state-of-the-art BLEU scores on WMT 2014 English-to-German and English-to-French translation tasks with significantly reduced training costs.
    ## Lesson: Model Variations and Generalization
    - **Keywords:** Model Variations, Attention Heads, Key Size, Dropout, Positional Embedding, Constituency Parsing, Generalization   [##100 completed]
    - **Objective:** Discuss the impact of different architectural variations and evaluate the Transformer's ability to generalize to tasks beyond machine translation.
    - **Focus:** This lesson examines the results of experiments on model variations (Table 3) to understand component importance and demonstrates the Transformer's successful application and strong performance on English constituency parsing (Table 4), showcasing its generalization capabilities.
    Output:
    # Phase: Introduction to Sequence Transduction and the Transformer
    ## Lesson: Limitations of Recurrent and Convolutional Models
    - **Keywords:** Sequence Transduction, RNN, CNN, Recurrence, Convolution, Parallelization, Sequential Computation
    - **Objective:** Understand the challenges faced by traditional sequence transduction models like RNNs and CNNs, particularly regarding sequential computation and parallelization.
    - **Focus:** This lesson focuses on the inherent sequential nature of recurrent models and the path length issues in convolutional models that limit their efficiency and ability to learn long-range dependencies, motivating the need for a new architecture.
    ## Lesson: Introducing the Transformer Architecture
    - **Keywords:** Transformer, Attention Mechanism, Self-Attention, Sequence Transduction, Parallelization
    - **Objective:** Learn about the Transformer, a novel network architecture that replaces recurrence and convolutions entirely with attention mechanisms.
    - **Focus:** This lesson introduces the core idea of the Transformer: relying solely on attention to draw global dependencies, enabling significantly more parallelization and faster training compared to previous models.
    ---
    # Phase: Core Components of the Transformer
    ## Lesson: Encoder-Decoder Structure
    - **Keywords:** Encoder, Decoder, Stack, Sub-layer, Residual Connection, Layer Normalization
    - **Objective:** Describe the overall encoder-decoder structure of the Transformer and the composition of its stacked layers.
    - **Focus:** This lesson details how the Transformer utilizes an encoder-decoder framework with stacks of identical layers, each featuring sub-layers, residual connections, and layer normalization, as depicted in Figure 1.
    ## Lesson: Attention Function and Scaled Dot-Product Attention
    - **Keywords:** Attention Function, Query, Key, Value, Weighted Sum, Scaled Dot-Product Attention, Softmax, Compatibility Function
    - **Objective:** Explain the fundamental concept of an attention function and the specific implementation used in the Transformer: Scaled Dot-Product Attention.
    - **Focus:** This lesson covers the definition of attention as mapping queries and key-value pairs to a weighted sum of values, focusing on the Scaled Dot-Product Attention formula and the role of scaling by 1/sqrt(dk).
    ## Lesson: Multi-Head Attention
    - **Keywords:** Multi-Head Attention, Linear Projection, Parallel Attention, Representation Subspaces, Concatentation
    - **Objective:** Understand how Multi-Head Attention enhances the model's ability to attend to information from different representation subspaces.
    - **Focus:** This lesson explains the mechanism of Multi-Head Attention, involving projecting queries, keys, and values multiple times in parallel and concatenating the results, highlighting its benefit over single-head attention.
    ## Lesson: Applications of Attention within the Transformer
    - **Keywords:** Encoder-Decoder Attention, Encoder Self-Attention, Decoder Self-Attention, Masking, Auto-regressive
    - **Objective:** Identify the three distinct ways Multi-Head Attention is utilized in the Transformer's encoder and decoder stacks.
    - **Focus:** This lesson details the specific applications: encoder-decoder attention for connecting encoder/decoder outputs, encoder self-attention for processing input sequence dependencies, and masked decoder self-attention for preserving the auto-regressive property.
    ---
    # Phase: Supporting Mechanisms and Training
    ## Lesson: Position-wise Feed-Forward Networks, Embeddings, and Softmax
    - **Keywords:** Feed-Forward Network, ReLU, Embeddings, Softmax, Shared Weights
    - **Objective:** Describe the role of the position-wise feed-forward networks and how input/output tokens are processed using embeddings and a final softmax layer.
    - **Focus:** This lesson covers the independent feed-forward network applied to each position and the standard use of learned embeddings for token representation, including the sharing of weights between embedding layers and the pre-softmax transformation.
    ## Lesson: Positional Encoding
    - **Keywords:** Positional Encoding, Sine, Cosine, Sequence Order, Relative Position, Learned Embeddings
    - **Objective:** Explain why positional encoding is necessary in the Transformer and how the sinusoidal positional encoding is implemented.
    - **Focus:** This lesson focuses on the need to inject positional information due to the absence of recurrence/convolution and describes the use of sine and cosine functions at different frequencies, discussing its potential for extrapolating to longer sequences.
    ## Lesson: Efficiency Analysis: Why Self-Attention?
    - **Keywords:** Computational Complexity, Sequential Operations, Maximum Path Length, Parallelization, Long-Range Dependencies
    - **Objective:** Compare the efficiency of self-attention layers against recurrent and convolutional layers based on computational complexity, sequential operations, and path length.
    - **Focus:** This lesson uses the analysis from the paper (Table 1) to highlight the advantages of self-attention, particularly its constant number of sequential operations and path length, making it highly parallelizable and effective for capturing long-range dependencies.
    ---
    # Phase: Implementation, Results, and Impact
    ## Lesson: Training Setup and Regularization
    - **Keywords:** Training Data, Batching, Optimizer, Learning Rate Schedule, Warmup Steps, Residual Dropout, Label Smoothing
    - **Objective:** Summarize the training methodology, including data preparation, optimizer configuration, learning rate scheduling, and regularization techniques used.
    - **Focus:** This lesson details the practical aspects of training the Transformer, covering the datasets used, batching strategy, the Adam optimizer with a specific learning rate schedule and warmup, and the application of dropout and label smoothing.
    ## Lesson: Machine Translation Performance
    - **Keywords:** Machine Translation, BLEU Score, WMT 2014, State-of-the-Art, Training Cost, Benchmarks
    - **Objective:** Evaluate the Transformer's performance on machine translation tasks based on reported BLEU scores and training costs compared to existing models.
    - **Focus:** This lesson presents the key results from the paper (Table 2), demonstrating that the Transformer achieves new state-of-the-art BLEU scores on WMT 2014 English-to-German and English-to-French translation tasks with significantly reduced training costs.
    ## Lesson: Model Variations and Generalization
    - **Keywords:** Model Variations, Attention Heads, Key Size, Dropout, Positional Embedding, Constituency Parsing, Generalization  
    - **Objective:** Discuss the impact of different architectural variations and evaluate the Transformer's ability to generalize to tasks beyond machine translation.
    - **Focus:** This lesson examines the results of experiments on model variations (Table 3) to understand component importance and demonstrates the Transformer's successful application and strong performance on English constituency parsing (Table 4), showcasing its generalization capabilities.
    Input:
    (Descrption:If heirarchy is Jumbeled Find the right heirarchy and find the right markdown for it and sometimes 
    there wouldn't be any phase at all then omit it in output just continue or if clear distinction is provided write them as Phase 1 , Phase 2  )
    ERROR_PARSING_SYLLABUS_STREAM_0xDEADBEEF: Unrecoverable anomaly detected! BEEPBOOPFIZZ! Attempting to render partial content.

    ## Unit: Welcome and Orientation
    - **Key Ideas:** Course Overview, Learning Objectives, Tools Setup
    - **Goal:** To welcome learners and set up the learning environment.
    - **Core Content:** Introduction to the course, navigating the platform, installing necessary software.

    ## Unit: Advanced Data Manipulation  // This unit belongs in the "Data Analysis" Module
    - **Key Ideas:** Data Wrangling, Feature Engineering, Complex Queries
    - **Goal:** To master techniques for transforming and preparing complex datasets.
    - **Core Content:** Advanced Pandas operations, creating new features from existing data, SQL for complex joins and aggregations.
    ---
    # Module: Introduction to Programming
    ## Unit: Basic Concepts
    - **Key Ideas:** Variables, Data Types, Operators, Control Flow
    - **Goal:** Understand the fundamental building blocks of programming.
    - **Core Content:** Lectures and exercises on basic syntax and logic.
    ## Unit: Functions and Modularity
    - **Key Ideas:** Defining Functions, Scope, Reusability, Modules
    - **Goal:** Learn to write modular and reusable code using functions.
    - **Core Content:** Practical examples of function creation and usage.
    ---
    ## Unit: Version Control with Git
    - **Key Ideas:** Repositories, Commits, Branches, Merging
    - **Goal:** To learn the basics of version control for collaborative projects.
    - **Core Content:** Introduction to Git, common commands, and basic workflows.
    ## Unit: Debugging Techniques
    - **Key Ideas:** Breakpoints, Logging, Error Interpretation, Troubleshooting
    - **Goal:** To develop effective strategies for finding and fixing code errors.
    - **Core Content:** Common debugging tools and methods.
    ---
    # Module: Data Analysis and Visualization
    ## Unit: Introduction to Data Analysis
    - **Key Ideas:** Data Collection, Cleaning, Exploratory Data Analysis (EDA)
    - **Goal:** Understand the data analysis lifecycle and initial exploration techniques.
    - **Core Content:** Methods for acquiring, cleaning, and performing initial analysis on datasets.
    ## Unit: Data Visualization Principles
    - **Key Ideas:** Chart Types, Storytelling with Data, Effective Visuals, Matplotlib, Seaborn
    - **Goal:** Learn to create effective and informative data visualizations.
    - **Core Content:** Best practices in data visualization and hands-on with plotting libraries.

    //End of partial data stream. ALERT: integrity_check_failed.
    Output:
    ### Unit: Welcome and Orientation
    **Key Ideas:** Course Overview, Learning Objectives, Tools Setup
    **Goal:** To welcome learners and set up the learning environment.
    **Core Content:** Introduction to the course, navigating the platform, installing necessary software.

    ---
    ## Phase 1: Introduction to Programming

    ### Unit: Basic Concepts
    **Key Ideas:** Variables, Data Types, Operators, Control Flow
    **Goal:** Understand the fundamental building blocks of programming.
    **Core Content:** Lectures and exercises on basic syntax and logic.

    ### Unit: Functions and Modularity
    **Key Ideas:** Defining Functions, Scope, Reusability, Modules
    **Goal:** Learn to write modular and reusable code using functions.
    **Core Content:** Practical examples of function creation and usage.

    ---
    ## Phase 2

    ### Unit: Version Control with Git
    **Key Ideas:** Repositories, Commits, Branches, Merging
    **Goal:** To learn the basics of version control for collaborative projects.
    **Core Content:** Introduction to Git, common commands, and basic workflows.

    ### Unit: Debugging Techniques
    **Key Ideas:** Breakpoints, Logging, Error Interpretation, Troubleshooting
    **Goal:** To develop effective strategies for finding and fixing code errors.
    **Core Content:** Common debugging tools and methods.

    ---
    ## Phase 3: Data Analysis and Visualization

    ### Unit: Introduction to Data Analysis
    **Key Ideas:** Data Collection, Cleaning, Exploratory Data Analysis (EDA)
    **Goal:** Understand the data analysis lifecycle and initial exploration techniques.
    **Core Content:** Methods for acquiring, cleaning, and performing initial analysis on datasets.

    ### Unit: Data Visualization Principles
    **Key Ideas:** Chart Types, Storytelling with Data, Effective Visuals, Matplotlib, Seaborn
    **Goal:** Learn to create effective and informative data visualizations.
    **Core Content:** Best practices in data visualization and hands-on with plotting libraries.

    ### Unit: Advanced Data Manipulation
    **Key Ideas:** Data Wrangling, Feature Engineering, Complex Queries
    **Goal:** To master techniques for transforming and preparing complex datasets.
    **Core Content:** Advanced Pandas operations, creating new features from existing data, SQL for complex joins and aggregations.
    """


    syllabus_xml_input = dspy.InputField(
        desc="The learning syllabus content, which may be in XML format or as pre-formatted text, potentially containing extraneous text. This XML will be processed based on the detailed instructions provided above."
    )
    cleaned_syllabus_markdown = dspy.OutputField(
        desc="The syllabus strictly formatted in clean Markdown, with unwanted artifacts removed and hierarchy preserved."
    )