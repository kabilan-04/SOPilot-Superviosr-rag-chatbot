# SOPilot — Shop-Floor AI Copilot (Kaveri Precision Components, Hosur)

A privacy-first, on-premises RAG (Retrieval-Augmented Generation) copilot built for manufacturing shift supervisors. Designed to deliver fast, grounded answers to maintenance, quality, and safety questions directly on mobile devices (smartphones/tablets) via local Wi-Fi.

---

## 🛠️ Tech Stack & Architecture

- **Backend:** FastAPI (Python 3) binding to `0.0.0.0:8000`
- **Frontend:** Responsive, touch-optimized dark UI (Vanilla HTML5 / CSS3 / JavaScript) in `./static`
- **Embeddings:** `nomic-embed-text` (768 dimensions) via local Ollama
- **LLM:** `llama3.2` (3B parameters) via local Ollama (zero-temperature, strict JSON schema)
- **Vector Search:** In-memory cosine similarity using NumPy with JSON persistence (`vector_store.json`)
- **Document Store:** PDF processing via PyPDF with domain-aware tabular sentence reconstruction

---

## 🚀 Quick Start Guide

### 1. Prerequisites
Ensure Ollama is running and both models are installed:
```bash
ollama pull nomic-embed-text
ollama pull llama3.2
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 2. (Optional) Re-index Documents
All PDFs in `./resources` are already processed into `vector_store.json`. If you add new PDFs or modify chunking:
```bash
python dataprocessor.py
```

### 3. Launch the Server
```bash
python app.py
```
The server will output:
```text
  On this laptop:  http://127.0.0.1:8000
  On your phone:   http://192.168.1.13:8000
  Same Wi-Fi. Allow incoming connections if macOS asks.
```

---

## 📱 Opening on a Phone / Tablet

1. Connect your smartphone/tablet to the **same Wi-Fi network** as your laptop.
2. Open your mobile browser (Safari, Chrome) and navigate to:
   ```
   http://<YOUR-LAPTOP-IP>:8000
   ```
   *(e.g., `http://192.168.1.13:8000`)*
3. Tap on any pre-configured question chip or type a question in the search bar.

---

## 🛡️ Key Shop-Floor Improvements

1. **Document Revision Guard:** Automatically filters out superseded SOP revisions (e.g. `QC-SOP-014 Rev 03`) so operators never receive outdated sampling rules, while allowing historical lookup if explicitly queried.
2. **Safety Interceptor:** Detects unauthorized actions (e.g., tightening bolts, lock removal without sign-off) and injects unmissable warning banners.
3. **Strict Grounding:** Sets `in_documents: false` if a question asks about a part or spec not found in the documents, completely eliminating dangerous torque/dimension hallucinations.

## 5 5 question with output and also provied thescreenshots in the screenshot folder
1.what should I do when CNC-06 displays AL-104?
Answered from documents
Top up with ISO VG 68 oil to the MAX mark, then press RESET. The machine can continue after reset.
📄MNT-MAN-CNC-02 Rev 02, 6. Common Alarms Current



2.How many samples should I inspect for a lot of 200?
Answered from documents
Inspect 5 samples for a lot of 200. Accept if minor defects are 0; reject if minor defects are 1 or more.
📄QC-SOP-014 Rev 04, 4. Sampling Plan Current


3.Who can remove a lock if an employee has left?
Answered from documents
The Shift Supervisor must contact the lock owner by phone, and if the owner cannot be reached, both the Production Manager and the Safety Officer must authorise removal. The machine must be physically inspected to confirm it is safe to re-energise. The removal is recorded on form SF-12 Lock Removal Record, and the lock owner must be informed before they resume work on their next shift.
📄SAF-SOP-003 Rev 05, 6. Removal of a Lock When the Owner Is Absent Current


4.What is the torque for TX-200 turret bolts?
Answered from documents
The torque for the chuck mounting bolts is 110 Nm. The requested turret bolt torque is missing.
📄MNT-MAN-CNC-02 Rev 02, 5. Chuck Mounting Bolt Torque
Observation: SOPilot correctly distinguishes chuck mounting bolts from turret bolts and does not apply the 110 Nm value to the wrong component.





5.What is the overtime policy for the night shift?
Not in the documents
That isn't in the documents I have (quality, maintenance and safety procedures). Ask your supervisor or the relevant department.Observation: SOPilot correctly identifies that the information is unavailable and does not invent an overtime policy.
