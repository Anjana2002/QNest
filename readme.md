# QNest - AI-Powered Question Paper Generator
![Alt Text](QNest/static/images/logo.ico)

QNest is an AI-powered web application designed to generate university-level question papers using study materials, previous question papers, and customizable templates. Built using **Django** for the backend and powered by **Ollama** for AI-driven question generation, QNest streamlines the exam creation process for educators.

## 🚀 Features
- **Custom Templates**: Define templates specifying exam title, course details, section structure, question count, and marks distribution.
- **AI-Powered Generation**: Uses advanced language models like **Mistral** for generating contextually relevant questions.
- **Study Material Analysis**: Extracts content from uploaded PDFs to generate questions.
- **Previous Paper Reference**: Prevents question repetition by referencing past papers.
- **Download & Print**: Supports direct question paper downloads in PDF format and printing.
- **User Authentication**: Secure login and template management for individual users.

---

## 🛠️ Tech Stack
- **Backend**: Django, Python
- **AI Model**: Ollama (Mistral )
- **Frontend**: HTML, CSS, JavaScript


---

##  Installation Guide

Follow these steps to set up and run **QNest** locally.
### 🛠️ Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/qnest.git
   cd qnest