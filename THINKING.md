# THINKING.md

# SOPilot: Manufacturing Shop-Floor AI Copilot

## 1. Understand the user

### Who the user is

The primary user is Rajesh Murugan, a shop-floor shift supervisor responsible for coordinating approximately 15–20 machinists and machine operators across rotating eight-hour shifts.
He oversees daily production activities, monitors machine performance, ensures product quality, and makes sure that workplace safety procedures are followed. His role requires him to make frequent decisions while balancing production targets, equipment availability, quality requirements, and employee safety.


### What he is trying to achieve

Rajesh needs to:

-  Reduce downtime and maintain line productivity and OEE.
-  Make sure inspection and sampling procedures follow the latest approved quality documents.
-  Ensure that procedures such as Lockout/Tagout (LOTO) are followed correctly.
-  Find reliable answers to machine alarms, operating procedures, and quality questions without leaving the shop floor.
-  Give operators clear instructions and coordinate work across the bay.

### Frustrations and constraints

The current way of finding information is slow and inconvenient. SOPs and machine manuals may be stored in physical binders in the Quality office or as PDFs on an office server. Walking away from the production area to find one instruction can cost 15–25 minutes.

There is also a risk that old document revisions remain in circulation. An operator could follow an outdated sampling procedure without knowing that a newer revision has changed the required sample count or quarantine process.

The environment creates additional usability challenges:

- The shop floor is noisy, with reported noise levels above 80 dB.
- Cutting-oil mist and work gloves make small touch targets and desktop-style interfaces inconvenient.
- Supervisors are often in a hurry and may enter short queries rather than carefully written prompts.
- Incorrect technical guidance can cause defective products, equipment damage, or safety incidents.

### Assumptions

The proposed copilot assumes that supervisors have access to a smartphone or rugged tablet connected to the plant's internal Wi-Fi. It is designed to run locally, without requiring public-cloud access or an external internet connection. The first version uses English queries, technical terms, machine codes, and quick suggestion buttons.

These are design assumptions from the project, not confirmed facts about every supervisor or plant.

---

## 2. User journey

### Scenario: Alarm AL-104 on CNC-06

1. **A machine stops.** At 10:15 AM, CNC-06 stops during a cutting operation and displays alarm AL-104. The operator alerts Rajesh.
2. **The supervisor opens SOPilot.** Rajesh uses the shortcut on his phone to open the copilot over the plant's local Wi-Fi.
3. **He submits a short query.** He taps the suggested question, “Alarm AL-104 on CNC-06. What do I do?”, or enters a short query such as `AL-104 TX-200`.
4. **The copilot retrieves relevant instructions.** The system searches the local document index and uses the retrieved manual content to formulate an answer.
5. **The answer identifies its source.** In the documented example, the copilot explains that AL-104 indicates a low way-lube oil level, specifies ISO VG 68 oil, and directs the user to top up to the MAX mark and press RESET. It cites `MNT-MAN-CNC-02 Rev 02`, section 6, Common Alarms.
6. **The supervisor acts.** Rajesh directs the operator to top up the reservoir, checks the sight glass, and resets the machine. In the scenario, the machine restarts at 10:18 AM.

The important part of this journey is not simply that the AI answers a question. It helps the supervisor find a relevant instruction quickly and shows where the answer came from.

### What could go wrong

- **An old revision is retrieved:** The system could return QC-SOP-014 Rev 03 instead of Rev 04. That could result in an incorrect sample count and a quality or audit failure.
- **The AI makes an unsafe inference:** A manual may specify 110 Nm for chuck mounting bolts but say nothing about turret bolts. Reusing the chuck value for turret bolts would be an unsafe assumption.
- **A safety instruction is incomplete:** A response about removing an unattended personal lock could omit the required Production Manager and Safety Officer dual sign-off and Form SF-12.
- **The network connection drops:** The phone may lose Wi-Fi coverage behind electrical shielding or storage racks. The interface should show a retry state rather than freeze.
- **The query is too short or unclear:** A one-character input or vague greeting could retrieve unrelated document content.
- **The question is outside the documents:** A complete question about an overtime policy, for example, should not cause the system to invent a policy or document reference.

---

## 3. AI challenge (conversation excerpts and reflection)

A simulated critique was carried out with an AI acting as a skeptical Manufacturing Product Manager and Plant Head. The following excerpts capture the main challenges raised in that critique.

### Challenge 1: The interaction is too demanding

> **Skeptical PM:** “Shop-floor supervisors do not write complete, polite sentences on mobile keyboards. Their hands are greasy, the lighting is harsh, and they are in a rush. If your tool expects multi-sentence prompting, nobody will use it after Day 2.”

**Reflection:** This challenged the assumption that users would type detailed questions. On the shop floor, speed and low interaction effort matter more than conversational polish. A useful interface should support short queries and common tasks without requiring typing every time.

### Challenge 2: Old document revisions are dangerous

> **Skeptical PM:** “Having both Rev 03 and Rev 04 in the document folder is a trap. In real life, factories have duplicate files all over the place. If your vector search treats them equally based on cosine similarity, you WILL serve outdated rules to the floor.”

**Reflection:** Similarity alone is not enough to decide which procedure is authoritative. Document status and revision lifecycle must be considered before retrieved content is given to the language model. This is especially important when a newer revision changes a quality or safety instruction.

### Challenge 3: A partial match can still be dangerous

> **Skeptical PM:** “You need a hard distinction between 'information not found' and 'dangerous partial match'. If someone asks for a bolt torque and the manual doesn't have it, a standard LLM will say 'I found 110 Nm for chuck bolts' and an operator will use 110 Nm anyway. You must actively warn them.”

**Reflection:** This highlighted that a technically related result is not necessarily a valid answer. The system must not transfer a value from one component or operation to another. When the requested specification is absent, it should say so clearly and direct the user to the appropriate responsible team.

### What changed after the critique

The project incorporated the following responses:

- Quick suggestion chips were added so common questions can be submitted with one tap.
- A Document Revision Guard filters superseded documents from normal retrieval.
- A safety interceptor warns users when a requested mechanical parameter is not explicitly documented.
- Input clarification and out-of-scope handling distinguish incomplete queries from complete questions that are not covered by the plant documents.

The critique also suggested voice dictation. That suggestion was not selected for Phase 1. The project rationale was that a noisy machine bay could cause speech recognition to misinterpret technical codes such as `AL-104`. Touch-based suggestions were considered more reliable for the first version.

---

## 4. The improvement you added, and why you chose it

### Selected improvement: Document Revision Guard

The most important improvement is the Document Revision Guard.

**Problem:** A normal retrieval-augmented generation (RAG) system may retrieve an old document if its wording is similar to the user's question. In the example from this project, both QC-SOP-014 Rev 03 and Rev 04 may exist in the document collection, but Rev 04 contains the current sampling and quarantine requirements.

**What was added:**

1. Documents are classified in the document catalogue with a lifecycle status such as `current` or `superseded`.
2. The `search_chunks()` function checks document status before vector matching and excludes superseded documents by default.
3. If a user explicitly asks about an older revision, `query_wants_old_revision()` can relax the filter and the response displays a `Superseded` badge.
4. Safety interception remains in place for undocumented torque or other mechanical specifications, so revision handling does not become a substitute for safety validation.

**Why I chose it:**

I chose this improvement because it addresses a high-impact failure that ordinary similarity search does not solve. In a manufacturing environment, a fluent answer based on an obsolete SOP can be more harmful than no answer at all. Filtering outdated revisions before retrieval reduces the chance that the copilot will present an obsolete procedure as current.

It also makes the system's behaviour easier to explain: current documents are used for normal questions, while old revisions are only surfaced when the user specifically asks for historical information and are clearly labelled.

### Other supporting improvements

- **Input clarification:** Very short inputs and generic greetings are intercepted before embedding, reducing irrelevant retrieval.
- **Out-of-scope detection:** Complete questions about topics absent from the document set are labelled `Not in the documents`, without fabricated document citations.
- **Safety interception:** Undocumented torque or tightening values trigger a caution rather than an inferred specification.
- **Mobile viewport improvements:** The header and input footer remain fixed while the message thread scrolls, making the interface easier to use on a phone.
- **Quick suggestion chips:** Common shift questions can be submitted with one tap.

---

## 5. Final reflection

Building SOPilot required thinking beyond whether an LLM could answer questions. The central design challenge was making the answer dependable enough for a manufacturing environment, where an incorrect instruction can affect product quality, equipment, or worker safety.

The biggest challenge was **controlling what the AI is allowed to answer when the documents are incomplete, outdated, or only partially relevant**. A standard semantic search can find text that looks similar without understanding whether it is the current approved instruction or whether a specification applies to the exact component being asked about.

I handled this by adding controls around retrieval and response generation rather than relying only on the language model:

- Filter superseded revisions before selecting document chunks.
- Require answers to be grounded in retrieved document content.
- Validate returned section labels against the retrieved text.
- Distinguish incomplete questions from complete but out-of-scope questions.
- Intercept safety-sensitive requests when the requested value is not explicitly documented.
- Show source information and warnings so the supervisor can judge the response.

The critique also changed how I thought about usability. The supervisor is working in a noisy, time-sensitive environment, so a mobile-first interface with fixed controls and quick suggestions is more practical than expecting long prompts or relying on voice input in Phase 1.

**Final takeaway:** SOPilot should be treated as a document-grounded support tool for supervisors, not as an authority that replaces approved procedures, maintenance expertise, or safety responsibilities. Its value comes from helping people find the right documented instruction quickly while being clear when the available documents do not support an answer.
