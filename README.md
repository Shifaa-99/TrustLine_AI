# Trustline AI – Intelligent Customer Support System

## Overview
**Trustline AI** is an intelligent, privacy-aware customer support system designed to handle customer inquiries, complaints, and order-related issues in a structured, transparent, and responsible manner.  
The system combines rule-based logic, state-driven conversation management, and AI-assisted understanding with a **Retrieval-Augmented Generation (RAG)** layer to ensure accurate, grounded, and policy-aligned responses.

Trustline AI is built to support real-world e-commerce and service platforms where trust, data protection, explainability, and operational clarity are essential.

---

## Core Capabilities

### 1. Input Validation
All user inputs (order IDs, phone numbers, images, and free-text messages) are validated to ensure:
- Correct formatting and consistency
- Reduced ambiguity and errors
- Protection against malformed or malicious inputs

---

### 2. Privacy-Preserving Processing
The system follows a **privacy-first design**, ensuring:
- No unnecessary storage of personal or sensitive data
- Controlled handling of identifiers (e.g., phone numbers, order IDs)
- Clear separation between conversational context and stored complaint records

---

### 3. Transparency
Trustline AI operates using a **state-based conversation flow**, which provides:
- Predictable and traceable system behavior
- Clear feedback to users at each interaction step
- Auditable complaint and interaction records

---

### 4. Testability
The system is highly testable due to:
- Modular architecture (chat logic, order management, complaint handling)
- Deterministic state transitions
- Clear separation between logic, UI, and data layers

---

### 5. Explainability
System decisions such as verification steps, complaint creation, and escalation are:
- Rule-driven and state-aware
- Easy to trace and explain
- Suitable for operational review and debugging

---

### 6. Retrieval-Augmented Generation (RAG) for Policy-Aware Answers
Trustline AI integrates a **Retrieval-Augmented Generation (RAG)** layer to ground responses in the organization’s knowledge base (e.g., FAQs, policies, procedures, and support guidelines).

When users ask about **policies, refunds, delivery rules, complaints, or operational procedures**, the chatbot retrieves the most relevant content and uses it to generate accurate, consistent, and policy-aligned responses.  
This approach reduces hallucinations and ensures alignment with official system guidelines.

---

## System Services

### 1. AI Chatbot Service
The chatbot is the primary user-facing component and provides:
- Structured order verification (order ID and phone number)
- Complaint intake and categorization
- Context-aware, state-driven conversations
- Policy and FAQ grounding via RAG for system-related questions
- Safe handling of out-of-scope, abusive, or irrelevant content

---

### 2. Admin Service
The admin interface enables:
- Reviewing and managing customer complaints
- Monitoring system interactions and states
- Ensuring accountability and operational follow-up
- Supporting transparent and auditable customer support workflows

---

## Data Preparation & Processing Pipelines

The system follows a clear and structured pipeline:

1. **Input Collection**
   - User text input
   - Optional images or attachments
   - Order identifiers

2. **Normalization & Validation**
   - Phone number normalization
   - Order ID validation
   - Input sanitization

3. **Contextual Processing**
   - Finite State Machine (FSM) evaluation
   - Conversation context tracking
   - Issue classification and intent detection

4. **Knowledge Indexing (RAG Preparation)**
   - Cleaning and standardizing policy and FAQ documents
   - Chunking content into retrievable segments
   - Building or refreshing the knowledge index

5. **Retrieval & Grounded Response**
   - Retrieving the most relevant knowledge chunks
   - Generating answers grounded in retrieved content
   - Ensuring policy compliance and consistency

6. **Structured Storage**
   - Storing complaint records in normalized formats
   - Maintaining timestamps and metadata
   - Avoiding redundant or unnecessary personal data storage

---

## Ethical & Responsible AI Principles

Trustline AI is built according to responsible AI principles:

- Respecting user privacy and consent  
- Minimizing data retention  
- Avoiding harmful, misleading, or unsafe outputs  
- Ensuring transparency and explainability  
- Grounding policy-related responses using verified knowledge sources  

---

## Disclaimer

Trustline AI is designed to assist with customer support and complaint management.  
It does not replace human judgment, legal advice, or official customer service decisions.  
Final responsibility for actions and resolutions remains with the operating organization.

---

## Maintenance & Extension

Trustline AI is modular by design and can be:

- Extended with additional AI or retrieval models  
- Integrated into existing company or e-commerce systems  
- Adapted to new regulatory, operational, or ethical requirements  

## Evaluation

The system was evaluated using multiple real-world and adversarial scenarios, including:

- Abusive or offensive language scenarios
- Suspicious or ambiguous user behavior
- Privacy-related concerns and data exposure attempts
- Order confusion and mismatched identifiers
- Out-of-context or system-irrelevant content
- Policy-related questions requiring RAG grounding

The evaluation confirmed that Trustline AI:
- Maintains conversation stability
- Preserves user privacy
- Responds safely to misuse or invalid inputs
- Produces grounded and policy-aligned responses

---

## Installation

### System Requirements
- Windows 64-bit (recommended)
- Python 3.9 or higher
- Internet connection (for AI services)

---

### Python Dependencies
 
pip install streamlit openai numpy pypdf pdf2image pytesseract
 
---
 
## Configuration
 
Set the OpenAI API key as an environment variable.
 
### Windows (PowerShell)
 
setx OPENAI_API_KEY "your-api-key"
 
Restart the terminal after setting the variable.
 
---
 
## Running the System
 
### Launch the Web Interface
 
python streamlit run src/app.py
 
The application opens automatically in the browser.


