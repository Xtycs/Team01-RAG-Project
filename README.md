# Local Privacy-First RAG Assistant

## 📌 Project Information
- **Course**: Software Engineering  
- **Homework ID**: Task1 - Project Proposal  
- **Project Title**: Local Privacy-First RAG Assistant  
- **Group Name**: Team 01  
- **Date**: 2025-09-02  

**Members**:  
- 陈凌宇 (1230019420)  
- 解汀阳 (1230019461)  
- 赵英吉 (1230019374)  

---

## 📖 Table of Contents
1. [Team Profile](#team-profile)  
2. [Problem Diagnosis & Project Description](#problem-diagnosis--project-description)  
3. [Plan of Work](#plan-of-work)  
4. [Product Ownership](#product-ownership)  
5. [Success Criteria & Evaluation](#success-criteria--evaluation)  
6. [References](#references)  

---

## 👥 Team Profile
- **Team Leader**: 陈凌宇  
- **Strengths**:  
  - 陈凌宇: design, search, backend coding, organization  
  - 解汀阳: interface & API design, testing  
  - 赵英吉: frontend coding, documentation  

> All members participate in all activities; the above highlights individual strengths.

---

## 🩺 Problem Diagnosis & Project Description
The project focuses on building a **local Retrieval-Augmented Generation (RAG) system** to address challenges in accessing **domain-specific, private knowledge**.

- **Limitations of current methods**:  
  - Keyword-based search lacks semantic relevance.  
  - Online LLMs risk **data leakage** and require constant internet connectivity.  

- **Proposed Solution**:  
  A fully **local RAG system** that deploys all components (document processing, embedding, vector DB, LLM inference) on local hardware.  

- **Key Features**:  
  1. **Full Local Deployment** – No external dependencies, offline availability, optimized for hardware constraints.  
  2. **End-to-End Privacy Protection** – Zero data transmission, compliance with privacy protocols, local-only audit logs.  
  3. **User-Centric Design** – Guided setup wizard, intuitive interface, contextual help, minimal learning curve.  

**Target Users**: students, interns, and professionals requiring **private, offline intelligent Q&A**.

---

## 🗓 Plan of Work
Work is organized around **functional features** instead of technical layers.  

### Week 1 – Requirements Refinement
- Hardware adaptation list (CPU/GPU/storage thresholds).  
- Privacy protocol (design desensitization rules for sensitive data).  

### Week 2–3 – Core Module Development
- Document preprocessing (PDF/Word parsing, text chunking, noise cleaning).  
- Embedding + vector DB (semantic retrieval, local API).  
- Context fusion + LLM generation (answering with citations).  

### Week 4–5 – Integration & Testing
- Frontend UI (upload, query, result display, setup wizard).  
- Frontend-backend integration (closed loop query → retrieval → answer).  
- User testing with 5–8 participants, collect feedback.  

### Week 5 – Optimization
- Simplify guidance steps, refine documentation.  
- Improve performance (optimize HNSW index, dimensionality reduction).  

---

## 📌 Product Ownership
Each member owns **two functional features**:

1. **Document Ingestion & Library Management** – 陈凌宇  
   - PDF/Word parsing, semantic chunking, deduplication, logs  

2. **Semantic Indexing & Retrieval** – 解汀阳  
   - Local embeddings, HNSW/IVF index API, Top-k retrieval  

3. **Citation-Grounded Answering** – 解汀阳  
   - Context fusion, snippet citations, confidence badges  

4. **Privacy Controls & Audit Logging** – 陈凌宇  
   - PII masking, encrypted storage, audit trail  

5. **Setup Wizard & Offline Deployment** – 赵英吉  
   - Hardware probe, one-shot install, docs  

6. **Core UI Flows** – 赵英吉  
   - Upload, ask, cited results with confidence  

---

## ✅ Success Criteria & Evaluation
- **Retrieval Effectiveness**: Recall@5 ≥ 0.80  
- **Latency**: Query P95 < 3.5s on 100k chunks  
- **Citation Fidelity**: ≥ 90% answers with correct citation, hallucination < 10%  
- **Privacy Compliance**: Zero external calls, full audit log coverage  
- **Acceptance**: All features validated via end-to-end test (`Upload → Ask → Cited Result`)  

---

## 📚 References
1. Lewis, P., Perez, E., Piktus, A., et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP*, NeurIPS 2020. [arXiv:2005.11401](https://arxiv.org/abs/2005.11401)  
2. Karpukhin, V., Oguz, B., Min, S., et al. *Dense Passage Retrieval for Open-Domain QA*, EMNLP 2020.  
3. Izacard, G., Grave, E. *Leveraging Passage Retrieval with Generative Models for Open-Domain QA*, EACL 2021.  
4. Guu, K., Lee, K., Tung, Z., et al. *REALM: Retrieval-Augmented LM Pre-Training*, ICML 2020. [arXiv:2002.08909](https://arxiv.org/abs/2002.08909)  
5. Borgeaud, S., Mensch, A., Hoffmann, J., et al. *Improving LMs by Retrieving from Trillions of Tokens (RETRO)*, arXiv 2022.  
6. Asai, A., Wu, Z., Wang, Y., et al. *Self-RAG: Learning to Retrieve, Generate, and Critique Through Self-Reflection*, ICLR 2024. [OpenReview](https://openreview.net/forum?id=hSyW5go0v8)  
7. Dwork, C., Roth, A. *The Algorithmic Foundations of Differential Privacy*, FnT in Theoretical CS, 2014.  

---
