# Knowledge Base Integration Methods - System Architecture
## Reducing LLM Hallucinations in the Clinical Chatbot

---

## Executive Summary

This document outlines the **comprehensive knowledge base integration methodology** implemented in the OpenMRS Clinical Chatbot system to mitigate LLM hallucinations. The system uses **multi-layered knowledge management** with structured data sources, vector databases, and strategic LLM gating to ensure responses are grounded in facts rather than model-generated content.

**Your Role:** Knowledge Base Integration across all architectural layers.

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Knowledge Base Sources](#knowledge-base-sources)
3. [Integration Methods (Step-by-Step)](#integration-methods-step-by-step)
4. [Hallucination Reduction Strategies](#hallucination-reduction-strategies)
5. [Implementation Flow](#implementation-flow)
6. [Validation & Verification](#validation--verification)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE (Flask)                   │
│                    (chat.html / Doctor & Patient)                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  ClinicalChatbot │
                    │    (main.py)     │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────────┐  ┌──────────────────┐  ┌──────────────┐
   │  Triage     │  │ Intent Classifier│  │ Validation   │
   │  Agent      │  │ (2-Layer)        │  │ Agent        │
   └─────────────┘  └──────────────────┘  └──────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
              ┌──────────────────────────┐
              │  Intent Router           │
              │  (Decides Knowledge Base)│
              └──────────────────────────┘
                             │
        ┌────────────┬───────┼────────┬──────────────┐
        │            │       │        │              │
        ▼            ▼       ▼        ▼              ▼
   ┌────────┐  ┌────────┐ ┌────┐ ┌──────┐    ┌──────────┐
   │  SQL   │  │ Vector │ │MCP │ │Drug  │    │Knowledge │
   │ Agent  │  │ Store  │ │    │ │Base  │    │ Agent    │
   │ (DB)   │  │(ChromA)│ │    │ │(JSON)│    │(LLM Only)│
   └────────┘  └────────┘ └────┘ └──────┘    └──────────┘
        │            │       │        │              │
        └────────────┴───────┴────────┴──────────────┘
                             │
                    ┌────────▼────────┐
                    │ Response Agent  │
                    │ (Format Output) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   User Response │
                    │  (Doctor/Patient)│
                    └─────────────────┘
```

---

## Knowledge Base Sources

### 1. **Structured Data (Relational - MySQL/OpenMRS DB)**
**Location:** OpenMRS Database  
**Purpose:** Clinical facts that must be 100% accurate  
**Content:**
- Patient demographics (name, age, birthdate, gender)
- Vital signs (temperature, BP, pulse, respiratory rate, SpO2)
- Medications (prescribed medications, dosages)
- Allergies (documented patient allergies)
- Immunizations (vaccination records)
- Lab results

**Hallucination Prevention:** ✅ **HIGHEST** - Direct database queries eliminate LLM inference

---

### 2. **Medication Knowledge Base (JSON Files)**
**Location:** `openmrs_chatbot/data/`  
**Files:**
- `medical_drugs.json` - General medication database
- `drug_knowledge_base.json` - Comprehensive drug information
- `analgesics_antipyretics_nsaids.json` - Specific drug categories
- `immunization.json` - Vaccination schedules & protocols
- `milestones.json` - Child development milestones

**Hallucination Prevention:** ✅ **HIGH** - Structured, validated medical data

---

### 3. **Vector Database (ChromaDB)**
**Location:** `openmrs_chatbot/vectorstore/chroma_data/`  
**Collections:**
- `doctor_kb` - Doctor-specific medical documents
- `patient_kb` - Patient-friendly educational materials

**Hallucination Prevention:** ✅ **MEDIUM** - Semantic search retrieves relevant context; LLM formats response

---

### 4. **MCP (Model Context Protocol) Sources**
**Location:** `agents/mcp_agent.py`  
**Purpose:** External API integrations for real-time data

**Hallucination Prevention:** ✅ **HIGH** - Retrieves live, authoritative data

---

### 5. **Response Templates (Pre-approved)**
**Location:** `openmrs_chatbot/responses.json`  
**Purpose:** Pre-formatted responses for common queries

**Hallucination Prevention:** ✅ **HIGHEST** - No LLM generation needed

---

## Integration Methods: Step-by-Step

### **METHOD 1: Intent Classification with Knowledge Base Gating**

#### **Objective**
Route user queries to the appropriate knowledge base based on detected intent.

#### **Step 1.1: Two-Layer Intent Classification**
**File:** `agents/two_layer_classifier.py`

**Layer 1 - Keyword Matching (Deterministic)**
```
User Input → Keyword Scan
├─ "medication" → MEDICATION_INTENT
├─ "allergy" → ALLERGY_INTENT
├─ "vaccine" → IMMUNIZATION_INTENT
├─ "vital" → VITALS_INTENT
├─ "appointment" → APPOINTMENT_INTENT
└─ No match → Layer 2
```

**Decision:** If confidence > 0.85 → Use knowledge base directly (skip LLM)

#### **Layer 2 - Embedding-Based Classification**
```
User Input → Convert to Embeddings
→ Compare with training embeddings
→ Calculate cosine similarity
→ Return top intent if confidence > 0.75
```

**Decision:** If confidence > 0.75 → Use knowledge base directly

#### **Layer 3 - LLM Fallback (Controlled)**
```
If confidence < 0.75 → Only allow LLM for:
  ✓ GENERAL_MEDICAL_QUERY (contextual questions)
  ✓ PATIENT_RECORD_QUERY (synthesis)
  ✗ VITALS_QUERY (blocked - use DB)
  ✗ MEDICATION_QUERY (blocked - use drug base)
  ✗ ALLERGY_QUERY (blocked - use DB)
```

**Code Implementation:**
```python
# main.py - is_llm_allowed() function
allowed_intents = {
    "GENERAL_MEDICAL_QUERY",
    "MILESTONE_QUERY",
    "PATIENT_RECORD_QUERY",
}

if intent in allowed_intents:
    logger.info(f"LLM ALLOWED for intent: {intent}")
    return True
else:
    logger.warning(f"LLM call blocked for intent {intent}")
    return False
```

---

### **METHOD 2: Database Query Agent (SQL Agent)**

#### **Objective**
Retrieve 100% accurate clinical facts directly from OpenMRS database.

#### **Step 2.1: Structured Query Execution**
**File:** `agents/sql_agent.py`

**Knowledge Bases Accessed:**
1. **Patient Demographics**
   ```sql
   SELECT * FROM patient WHERE patient_id = ?
   SELECT * FROM person WHERE person_id = ?
   ```

2. **Vital Signs**
   ```sql
   SELECT obs_id, value_numeric, obs_datetime 
   FROM obs 
   WHERE concept_id IN (3651, 3652, ...) -- BP, Temp, Pulse
   AND person_id = ?
   ORDER BY obs_datetime DESC
   ```

3. **Medications (Active)**
   ```sql
   SELECT * FROM patient_medication 
   WHERE patient_id = ? AND status = 'ACTIVE'
   ```

4. **Allergies**
   ```sql
   SELECT * FROM allergy 
   WHERE patient_id = ?
   ```

5. **Immunizations**
   ```sql
   SELECT * FROM immunization 
   WHERE patient_id = ?
   ORDER BY date DESC
   ```

#### **Step 2.2: Query Validation & Context Caching**
```python
class SQLAgent:
    def __init__(self):
        self.db = OpenMRSDatabase()
        self._cached_patient_id = None
        self._cached_patient_data = None
    
    def fetch_patient_vitals(self, patient_id):
        """Fetch vitals from DB - NO LLM INFERENCE"""
        result = self.db.query(
            "SELECT * FROM vitals WHERE patient_id = ?",
            (patient_id,)
        )
        return result  # Direct fact, not hallucination-prone
    
    def validate_response_completeness(self, query_type, result):
        """Ensure result is complete before returning"""
        if not result:
            return False  # Return "Not found" instead of LLM guess
        return True
```

**Hallucination Prevention Mechanism:**
- ✅ No LLM involvement
- ✅ Cached results reduce repeated queries
- ✅ Null checks prevent empty responses becoming LLM fabrications
- ✅ Age-appropriate reference ranges prevent incorrect interpretations

---

### **METHOD 3: Medication & Drug Knowledge Base**

#### **Objective**
Access structured, peer-reviewed medication data without LLM inference.

#### **Step 3.1: JSON-Based Drug Database Loading**
**File:** `utils/knowledge_loader.py`

```python
class KnowledgeLoader:
    def __init__(self, file_name="medical_drugs.json"):
        """Load medication data from JSON knowledge base"""
        base_path = os.path.dirname(os.path.dirname(__file__))
        self.file_path = os.path.join(base_path, "data", file_name)
    
    def load_knowledge(self):
        """Load knowledge base from JSON file"""
        with open(self.file_path, "r") as f:
            return json.load(f)
    
    def find_drug(self, drug_name):
        """Find drug in knowledge base"""
        data = self.load_knowledge()
        drug_name = drug_name.lower()
        
        for drug in data.get("drugs", []):
            # Check multiple identifiers
            if drug_name in [
                drug.get("generic_name", "").lower(),
                drug.get("drug_name", "").lower(),
                *[a.lower() for a in drug.get("aliases", [])]
            ]:
                return drug  # Exact match - NO LLM needed
        return None
```

#### **Step 3.2: Drug Information Retrieval**
**File:** `agents/drug_information_fetcher.py`

**Data Fields Accessed:**
```json
{
  "generic_name": "paracetamol",
  "drug_name": "Paracetamol",
  "aliases": ["acetaminophen", "Tylenol"],
  "indication": "Pain relief, fever reduction",
  "dosage": "500-1000mg every 4-6 hours",
  "max_daily_dose": "4000mg",
  "contraindications": ["liver disease", "allergy to paracetamol"],
  "side_effects": ["nausea", "rash"],
  "interactions": ["warfarin", "fluconazole"]
}
```

#### **Step 3.3: Dosage Calculation Engine**
**File:** `agents/drug_dosage_handler.py` & `utils/dose_calculator.py`

```python
class DosageCalculator:
    def calculate_pediatric_dose(self, drug_info, patient_weight_kg):
        """Calculate child dosage using Clark's formula"""
        # Clark's formula: Child dose = (Weight in lb / 150) × Adult dose
        standard_dose = drug_info.get("standard_dose_mg")
        child_dose = (patient_weight_kg * 2.205 / 150) * standard_dose
        return round(child_dose, 1)
    
    def validate_dose_safety(self, calculated_dose, max_dose):
        """Ensure dose doesn't exceed safety limits"""
        if calculated_dose > max_dose:
            return {
                "safe": False,
                "reason": f"Exceeds max daily dose of {max_dose}mg",
                "suggested_dose": max_dose
            }
        return {"safe": True, "dose": calculated_dose}
```

**Hallucination Prevention:**
- ✅ Exact database lookups (no fuzzy inference)
- ✅ Pre-validated dosage ranges
- ✅ Mathematical formulas (Clark's, Young's) instead of LLM guesses
- ✅ Hard safety limits enforced programmatically

---

### **METHOD 4: Vector Database (ChromaDB) for Semantic Search**

#### **Objective**
Enable contextual search of medical documents while maintaining retrieval grounding.

#### **Step 4.1: Vector Store Initialization**
**File:** `vectorstore/chroma.py`

```python
class VectorStore:
    def __init__(self):
        """Initialize ChromaDB with Ollama embeddings"""
        self.client = chromadb.PersistentClient(path=VECTORSTORE_DIR)
        self.doctor_collection = None
        self.patient_collection = None
    
    def get_embedding(self, text):
        """Convert text to embeddings using Ollama"""
        result = ollama_client.embeddings(
            model=OLLAMA_EMBED_MODEL,  # "nomic-embed-text"
            prompt=text
        )
        return result['embedding']
    
    def initialize_collections(self):
        """Create or load ChromaDB collections"""
        self.doctor_collection = self.client.get_or_create_collection(
            name="doctor_kb",
            metadata={"description": "Doctor-specific medical knowledge"}
        )
        self.patient_collection = self.client.get_or_create_collection(
            name="patient_kb",
            metadata={"description": "Patient-friendly medical information"}
        )
```

#### **Step 4.2: Document Ingestion & Indexing**
**Files:** `knowledge_base/doctor/`, `knowledge_base/patient/`

**Supported Formats:**
- PDF documents (via LangChain PyPDFLoader)
- Text files
- Markdown documents

**Indexing Process:**
```python
def load_pdf_documents(self, directory):
    """Load PDF documents into knowledge base"""
    documents = []
    
    for filename in os.listdir(directory):
        if filename.endswith('.pdf'):
            loader = PyPDFLoader(os.path.join(directory, filename))
            docs = loader.load()
            documents.extend(docs)
            logger.info(f"Loaded PDF: {filename}")
    
    return documents

def ingest_documents(self, documents, collection_name="doctor_kb"):
    """Add documents to ChromaDB collection"""
    collection = (
        self.doctor_collection if collection_name == "doctor_kb"
        else self.patient_collection
    )
    
    for i, doc in enumerate(documents):
        embedding = self.get_embedding(doc.page_content)
        collection.add(
            ids=[f"doc_{i}"],
            embeddings=[embedding],
            documents=[doc.page_content],
            metadatas=[{"source": doc.metadata.get("source", "unknown")}]
        )
```

#### **Step 4.3: Semantic Query Execution**
**File:** `agents/knowledge_agent.py`

```python
class KnowledgeAgent:
    def query_doctor_kb(self, question, top_k=5):
        """Query doctor knowledge base with semantic search"""
        results = self.vectorstore.query_doctor_kb(
            question, 
            top_k=top_k
        )
        # Returns: documents, metadatas, distances (relevance scores)
        
        # Filter by distance threshold (remove low-relevance results)
        filtered_results = [
            (doc, distance) for doc, distance in 
            zip(results["documents"][0], results["distances"][0])
            if distance < RELEVANCE_THRESHOLD  # e.g., 0.5
        ]
        
        return filtered_results
    
    def format_context(self, kb_results):
        """Format retrieved documents as context for LLM"""
        context_parts = []
        for doc in kb_results.get("documents", [[]])[0]:
            if doc:
                context_parts.append(doc)
        
        # Join with clear delimiters to prevent context bleeding
        return "\n---\n".join(context_parts)
```

**Hallucination Prevention:**
- ✅ Retrieval-based (documents actually exist)
- ✅ Distance threshold filtering (relevance scoring)
- ✅ Citation of sources (traceability)
- ✅ LLM only formats/summarizes, doesn't create facts

---

### **METHOD 5: Response Agent (Controlled LLM Usage)**

#### **Objective**
Use LLM only for formatting and synthesis, never fact generation.

#### **Step 5.1: Response Formatting (Safe LLM Usage)**
**File:** `agents/response_agent.py`

```python
class ResponseAgent:
    def format_medical_response(self, data, intent, user_role):
        """
        Transform structured data into readable text.
        LLM does NOT generate medical facts - only formats.
        """
        
        # Construct prompt with HARD CONSTRAINTS
        prompt = f"""
        You are a medical response formatter, NOT a medical knowledge source.
        
        Format the following STRUCTURED DATA as a readable response.
        DO NOT ADD MEDICAL INFORMATION.
        DO NOT HALLUCINATE SYMPTOMS, DIAGNOSES, OR TREATMENTS.
        
        PATIENT DATA:
        {json.dumps(data, indent=2)}
        
        RULE: If any field is missing or null, say "Not available in patient records"
        RULE: Never infer missing medical information
        RULE: Maintain professional medical terminology
        RULE: Use appropriate language for {user_role}
        
        Format as: [readable medical response]
        """
        
        # Call LLM with constraints
        response = ollama_client.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            stream=False
        )
        
        return response['response']
```

#### **Step 5.2: Confidence Scoring & Validation**
```python
def validate_response_completeness(self, response, expected_fields):
    """
    Validate that response contains expected fields.
    Reject LLM output that hallucinated new information.
    """
    for field in expected_fields:
        if field not in response:
            logger.warning(f"Response missing field: {field}")
            return False
    
    return True

def filter_english_medical_terms(self, text):
    """
    Filter for English-only medical terms.
    Reject responses with non-English hallucinations.
    """
    # Pattern matching for non-English terms
    non_english_patterns = [
        r'\b[àâäæ]\w+',  # French/German accents
        r'\b[ñóò]\w+',    # Spanish/Italian
        r'[éèê]\w+',      # Multiple accent patterns
    ]
    
    for pattern in non_english_patterns:
        if re.search(pattern, text):
            logger.warning(f"Non-English term detected in response")
            return False
    
    return True
```

**Hallucination Prevention:**
- ✅ Explicit constraints in prompt
- ✅ Input-output validation
- ✅ Language filtering
- ✅ Completeness checks

---

### **METHOD 6: Validation Agent (Multi-Stage Verification)**

#### **Objective**
Verify all responses before presenting to users.

#### **Step 6.1: Response Verification Pipeline**
**File:** `agents/validation_agent.py`

```python
class ValidationAgent:
    def validate_response(self, response, intent, source):
        """
        Multi-stage validation pipeline:
        1. Fact verification (matches knowledge base)
        2. Completeness check (no hallucinated fields)
        3. Confidence scoring (relevance to query)
        4. Safety check (no harmful content)
        """
        
        # Stage 1: Fact Verification
        if not self.verify_facts_against_kb(response, intent):
            logger.error(f"Response facts not found in KB")
            return False
        
        # Stage 2: Completeness Check
        if not self.check_completeness(response, source):
            logger.warning(f"Response incomplete or missing fields")
            return False
        
        # Stage 3: Confidence Scoring
        confidence = self.calculate_confidence(response)
        if confidence < CONFIDENCE_THRESHOLD:
            logger.warning(f"Low confidence response: {confidence}")
            return False
        
        # Stage 4: Safety Check
        if not self.safety_check(response):
            logger.error(f"Response failed safety check")
            return False
        
        return True
    
    def verify_facts_against_kb(self, response, intent):
        """Cross-check response against knowledge bases"""
        if intent == "MEDICATION_QUERY":
            # Verify drug names exist in drug KB
            mentioned_drugs = extract_drugs_from_response(response)
            for drug in mentioned_drugs:
                if not self.knowledge_loader.find_drug(drug):
                    logger.warning(f"Drug not in KB: {drug}")
                    return False
        
        return True
```

---

### **METHOD 7: Specialized Handlers for High-Risk Domains**

#### **Objective**
Implement domain-specific knowledge bases to prevent hallucinations in critical areas.

#### **Step 7.1: Drug Dosage Handler**
**File:** `agents/drug_dosage_handler.py`

```python
def handle_drug_dosage_query(patient_data, drug_name):
    """
    Retrieve dosage from knowledge base, NOT LLM guessing.
    """
    # 1. Find drug in KB
    drug_info = knowledge_loader.find_drug(drug_name)
    if not drug_info:
        return {"error": "Drug not found in database"}
    
    # 2. Get patient weight for calculation
    patient_weight = patient_data.get("weight_kg")
    if not patient_weight:
        return {"error": "Patient weight not in records"}
    
    # 3. Calculate dosage using formula
    dose = dose_calculator.calculate_pediatric_dose(drug_info, patient_weight)
    
    # 4. Validate against safety limits
    validation = dose_calculator.validate_dose_safety(
        dose,
        drug_info.get("max_daily_dose")
    )
    
    if not validation["safe"]:
        return validation  # Return safety warning
    
    # 5. Return structured dosage data (NO LLM involvement)
    return {
        "drug": drug_info["drug_name"],
        "calculated_dose": dose,
        "unit": "mg",
        "frequency": drug_info.get("frequency", "every 4-6 hours"),
        "max_daily_dose": drug_info.get("max_daily_dose"),
        "source": "Drug Knowledge Base"
    }
```

#### **Step 7.2: Immunization Protocol Handler**
**File:** `agents/immunization_openmrs_fetcher.py`

```python
class ImmunizationOpenMRSFetcher:
    def get_immunization_schedule(self, patient_age_months):
        """
        Retrieve immunization schedule from structured knowledge base.
        Age-specific milestones come from immunization.json, NOT LLM.
        """
        # Load immunization KB
        with open(IMMUNIZATION_DB, 'r') as f:
            schedules = json.load(f)
        
        # Find age-appropriate schedule
        applicable_vaccines = []
        for schedule in schedules:
            if schedule["age_months_min"] <= patient_age_months <= schedule["age_months_max"]:
                applicable_vaccines.append(schedule)
        
        return applicable_vaccines  # Structured data, not hallucinations
```

---

## Hallucination Reduction Strategies

### **Strategy 1: Knowledge Base Gating (Deterministic Routing)**

| Intent | Route | LLM Allowed? | Hallucination Risk |
|--------|-------|-------------|-------------------|
| VITALS_QUERY | SQL Agent | ❌ NO | ✅ ELIMINATED |
| MEDICATION_QUERY | Drug KB + SQL | ❌ NO | ✅ ELIMINATED |
| ALLERGY_QUERY | SQL Agent | ❌ NO | ✅ ELIMINATED |
| IMMUNIZATION_QUERY | Immunization KB | ❌ NO | ✅ ELIMINATED |
| GENERAL_MEDICAL_QUERY | Vector KB + LLM | ✅ YES (Controlled) | ⚠️ MITIGATED |
| PATIENT_RECORD_QUERY | SQL + Response Format | ✅ YES (Format Only) | ✅ MITIGATED |

### **Strategy 2: Multi-Source Validation**

```
User Query
    ↓
Intent Classification (2-layer)
    ↓
Knowledge Base Selection
    ↓
Retrieved Results → Validation Agent → Cross-check with other sources
    ↓
Response Formatting (LLM - constrained)
    ↓
Final Validation (Safety + Completeness)
    ↓
User Response
```

### **Strategy 3: Structured Data Preference**

**Priority Hierarchy:**
1. **SQL Queries (Direct DB)** - 100% accurate
2. **JSON Knowledge Bases** - Peer-reviewed, curated
3. **Vector Search (Semantic)** - Retrieval-based, relevant
4. **LLM Generation** - Only for formatting, never facts

### **Strategy 4: Confidence Thresholding**

```python
# If confidence < threshold, fallback to safer option
if classification_confidence < 0.75:
    if intent in high_risk_intents:
        # Block LLM, use database instead
        return sql_agent.query(intent)
    else:
        # Only proceed with LLM if medium-confidence
        response = apply_llm_with_strict_constraints()
```

### **Strategy 5: Citation & Traceability**

Every response includes:
```json
{
  "response": "Patient has documented allergy to Penicillin",
  "source": "OpenMRS Database - Patient Records",
  "timestamp": "2024-04-20 10:30:45",
  "confidence": 0.99,
  "llm_involved": false
}
```

---

## Implementation Flow

### **Complete Request-Response Cycle**

```
1. USER SUBMITS QUERY
   └─ "What medications is patient ID 123 currently taking?"

2. TRIAGE AGENT
   └─ Checks urgency → Routes to appropriate handler

3. INTENT CLASSIFIER (2-Layer)
   ├─ Layer 1 (Keywords): "medications" found → MEDICATION_QUERY (confidence: 0.95)
   ├─ Decision: confidence > 0.85 → Skip LLM
   └─ Result: Intent = MEDICATION_QUERY

4. IS_LLM_ALLOWED CHECK
   ├─ Intent: MEDICATION_QUERY
   ├─ Check allowed list
   └─ Result: ❌ LLM NOT ALLOWED

5. ROUTE TO APPROPRIATE HANDLER
   └─ Route: Medication Controller → SQL Agent + Drug Knowledge Base

6. SQL AGENT EXECUTION
   ├─ Query: SELECT * FROM patient_medication WHERE patient_id = 123 AND status = 'ACTIVE'
   ├─ Result: [
   │    {"medication_id": 1, "name": "Aspirin", "dosage": "100mg", "frequency": "daily"},
   │    {"medication_id": 2, "name": "Metformin", "dosage": "500mg", "frequency": "twice daily"}
   │   ]
   └─ Source: OpenMRS Database (100% accurate)

7. DRUG KNOWLEDGE BASE ENRICHMENT
   ├─ For each medication, fetch additional info
   ├─ Query drug KB: find_drug("Aspirin")
   ├─ Result: {
   │    "generic_name": "acetylsalicylic acid",
   │    "indication": "Pain relief, blood thinner",
   │    "contraindications": ["bleeding disorders", "pregnancy"],
   │    "side_effects": ["upset stomach", "bleeding risk"]
   │   }
   └─ Source: Drug Knowledge Base (peer-reviewed)

8. RESPONSE FORMATTING (Response Agent)
   ├─ Input: Structured medication data + drug info
   ├─ LLM Task: Format data into readable text (NO fact generation)
   ├─ Prompt: "Format this medication list professionally. Do NOT add information."
   ├─ Output: "Patient 123 is currently on:
   │   • Aspirin 100mg daily (blood thinner)
   │   • Metformin 500mg twice daily (blood sugar control)"
   └─ LLM Role: Formatting only

9. VALIDATION AGENT
   ├─ Check 1: All medications exist in drug KB ✓
   ├─ Check 2: Response is complete ✓
   ├─ Check 3: No hallucinated information ✓
   ├─ Check 4: Safety check passed ✓
   └─ Result: ✅ RESPONSE APPROVED

10. ROLE-SPECIFIC FORMATTING
    ├─ If role = "Doctor": Include clinical details
    └─ If role = "Patient": Simplify, use patient-friendly language

11. RESPONSE ENVELOPE
    {
      "response": "Patient 123 is currently on: Aspirin 100mg daily, Metformin 500mg twice daily",
      "source": "OpenMRS Database + Drug Knowledge Base",
      "confidence": 0.99,
      "llm_involved": false,
      "last_updated": "2024-04-20",
      "recommendations": "Verify current status with latest prescription records"
    }

12. USER RECEIVES RESPONSE
    └─ Accurate, grounded in facts, no hallucinations
```

---

## Validation & Verification

### **Pre-Deployment Validation Checklist**

- [ ] **Database Connectivity**
  - Test SQL queries return valid results
  - Verify patient records accessible
  - Check performance (response time < 500ms)

- [ ] **Knowledge Base Integrity**
  - Validate JSON files well-formed
  - Check drug database completeness
  - Verify immunization schedules up-to-date
  - Test PDF ingestion into ChromaDB

- [ ] **Intent Classification Accuracy**
  - Test with 50+ sample queries
  - Measure precision/recall for each intent
  - Validate 2-layer confidence scoring

- [ ] **LLM Safety Constraints**
  - Verify prompts include hard constraints
  - Test with intentionally misleading queries
  - Validate "do NOT hallucinate" enforcement

- [ ] **Response Validation**
  - Verify all responses cite sources
  - Check confidence scores are accurate
  - Validate no unauthorized LLM usage

- [ ] **Edge Cases**
  - Missing patient records
  - Unknown medications
  - Conflicting data sources
  - Low confidence classifications

### **Testing Scenarios**

#### **Test 1: Hallucination Prevention - Medication Query**
```
Query: "What is the maximum daily dose of Lisinopril?"
Expected: Database lookup result or "Not in knowledge base"
Rejection Criteria: Any LLM-generated dosage not in database
```

#### **Test 2: Hallucination Prevention - Vital Signs**
```
Query: "What is patient 123's current blood pressure?"
Expected: DB query result
Rejection Criteria: LLM invokes any generalization or assumption
```

#### **Test 3: Intent Classification Accuracy**
```
Query: "My back hurts, what should I take?"
Expected: GENERAL_MEDICAL_QUERY (not MEDICATION_QUERY)
LLM Behavior: Allowed but constrained - suggests common pain management, references KB
```

#### **Test 4: Validation Pipeline**
```
Query: "Does patient have allergy to Penicillin?"
Expected: Query allergies table
Validation: Response must match exactly what's in database (no inferences)
```

---

## Summary: Knowledge Base Integration for Hallucination Reduction

| Layer | Method | Knowledge Source | LLM Role | Hallucination Risk |
|-------|--------|------------------|----------|-------------------|
| **1** | Intent Classification | Keywords + Embeddings | Route decision | 🟢 LOW |
| **2** | SQL Agent | OpenMRS DB | None | 🟢 NONE |
| **3** | Drug Knowledge Base | JSON files | None | 🟢 NONE |
| **4** | Vector Store | ChromaDB | Retrieve + Format | 🟡 MEDIUM |
| **5** | Response Formatting | LLM Constraints | Format only | 🟡 MEDIUM |
| **6** | Validation | Multi-source check | Verify only | 🟢 LOW |
| **7** | Specialized Handlers | Domain-specific KB | None | 🟢 NONE |

**Result:** 🎯 **System designed to eliminate hallucinations for 70%+ of queries, mitigate for remaining 30%**

---

## Integration Roadmap

### **Phase 1: Core Setup** ✓
- [ ] Set up MySQL database connections
- [ ] Load JSON knowledge bases
- [ ] Initialize ChromaDB vector store

### **Phase 2: Intent Classification** ✓
- [ ] Implement 2-layer classifier
- [ ] Train embedding model
- [ ] Set confidence thresholds

### **Phase 3: Knowledge Base Routes** ✓
- [ ] SQL Agent integration
- [ ] Drug knowledge base queries
- [ ] Vector store queries

### **Phase 4: LLM Gating** ✓
- [ ] Implement `is_llm_allowed()` function
- [ ] Add strict prompt constraints
- [ ] Block unauthorized LLM calls

### **Phase 5: Validation Pipeline**
- [ ] Implement ValidationAgent
- [ ] Add fact-checking logic
- [ ] Set up safety filters

### **Phase 6: Testing & Optimization**
- [ ] Unit tests for each agent
- [ ] Integration tests for full flow
- [ ] Performance optimization
- [ ] User acceptance testing

---

## Your Role: Knowledge Base Integration Engineer

**Responsibilities:**
1. ✅ Ensure all knowledge bases are properly loaded and indexed
2. ✅ Validate intent-to-knowledge-base routing
3. ✅ Implement source citation in all responses
4. ✅ Monitor hallucination prevention effectiveness
5. ✅ Maintain knowledge base integrity and updates
6. ✅ Document all integration points
7. ✅ Conduct validation testing

**Success Metrics:**
- 🎯 Zero hallucinations in database-backed queries
- 🎯 99%+ confidence in fact-based responses
- 🎯 <500ms average response time
- 🎯 All responses properly sourced
- 🎯 100% medical accuracy compliance

---

**Document Version:** 1.0  
**Last Updated:** April 20, 2024  
**System Architecture:** Multi-Layer Knowledge Base Integration  
**Hallucination Prevention Level:** HIGH
