# Allergy System — Complete Backend Workflow

This document explains how the OpenMRS Clinical Chatbot processes allergy-related queries, from the moment a user types a question to the final response displayed on screen.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Agents, MCPs, and LLM — What Gets Triggered](#agents-mcps-and-llm--what-gets-triggered)
3. [Files Involved](#files-involved)
4. [Workflow: "What allergies does this patient have?"](#workflow-1-what-allergies-does-this-patient-have)
5. [Workflow: "Can I prescribe Salbutamol?"](#workflow-2-can-i-prescribe-salbutamol)
6. [Workflow: "Can I give Ampicillin?"](#workflow-3-can-i-give-ampicillin)
7. [3-Layer Allergy Check](#3-layer-allergy-check-check_drug_allergy)
8. [Safety Net (Option B)](#safety-net-option-b)
9. [External APIs Used](#external-apis-used)
10. [Key Design Decisions](#key-design-decisions)

---

## System Overview

```
  User Question
       │
       ▼
┌─────────────────┐
│  main.py        │   Central orchestrator
│  ClinicalChatbot│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  triage_agent.py│   Intent classification (keyword matching)
│  classify_intent│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Pipeline: Doctor or Patient            │
│  ┌───────────────┐  ┌────────────────┐  │
│  │ Doctor Pipeline│  │Patient Pipeline│  │
│  └───────┬───────┘  └───────┬────────┘  │
│          │                  │            │
│          ▼                  ▼            │
│  ┌──────────────────────────────────┐   │
│  │  Intent Handler (ALLERGY_QUERY,  │   │
│  │  MEDICATION_QUERY, etc.)         │   │
│  └──────────────┬───────────────────┘   │
│                 │                        │
│                 ▼                        │
│  ┌──────────────────────────────────┐   │
│  │  _allergy_safety_net()           │   │
│  │  (Post-processing: catches any   │   │
│  │   drug mention not yet checked)  │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
         │
         ▼
  Response to User
```

---

## Agents, MCPs, and LLM — What Gets Triggered

### All Agents in the System

| Agent | File | Role | Uses LLM? |
|-------|------|------|-----------|
| **TriageAgent** | `agents/triage_agent.py` | Classifies intent (ALLERGY_QUERY, MEDICATION_QUERY, etc.) and user type (DOCTOR/PATIENT) | **NO** — pure keyword matching |
| **SQLAgent** | `agents/sql_agent.py` | Executes SQL queries against OpenMRS MySQL database | **YES** — uses Ollama (llama2) to generate SQL from natural language for PATIENT_RECORD_QUERY and VITALS_QUERY |
| **MCPAgent** | `agents/mcp_agent.py` | Searches local JSON databases (medications, immunizations, milestones), calculates doses | **NO** — JSON lookup + RxNorm API + FDA API |
| **KnowledgeAgent** | `agents/knowledge_agent.py` | Queries ChromaDB vector store for doctor/patient knowledge base | **NO** — vector similarity search only |
| **ResponseAgent** | `agents/response_agent.py` | Generates natural language responses from structured data | **YES** — uses Ollama (llama2) to format final responses for GENERAL queries |
| **ValidationAgent** | `agents/validation_agent.py` | Validates data availability, prevents hallucination | **NO** — rule-based checks |
| **AllergyOpenMRSFetcher** | `agents/allergy_openmrs_fetcher.py` | Fetches allergies from DB, runs 3-layer drug safety check | **NO** — SQL + REST APIs |
| **AllergyResponseDoctor/Patient** | `agents/allergy_response.py` | Formats allergy check results for Doctor or Patient | **NO** — template-based string formatting |

### What Gets Triggered for Allergy Queries

For the 3 allergy workflows documented below, here is exactly what fires:

```
┌────────────────────────────────────────────────────────────────────┐
│              ALLERGY QUERY — AGENT TRIGGER MAP                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  1. TriageAgent.classify_intent()          ✅ TRIGGERED            │
│     → Keyword matching (NO LLM)                                    │
│     → Returns: "ALLERGY_QUERY"                                     │
│     → Mapped agent: MCP_MEDICATION_AGENT                           │
│                                                                    │
│  2. TriageAgent.classify_user_type()       ✅ TRIGGERED            │
│     → Keyword matching (NO LLM)                                    │
│     → Returns: "DOCTOR" or "PATIENT"                               │
│                                                                    │
│  3. drug_dosage_handler.extract_drug_name() ✅ TRIGGERED           │
│     → Regex pattern matching (NO LLM)                              │
│     → Returns: drug name or None                                   │
│                                                                    │
│  4. AllergyOpenMRSFetcher                  ✅ TRIGGERED            │
│     → get_patient_allergies() — SQL to OpenMRS DB                  │
│     → check_drug_allergy() — 3-layer check (if drug detected)     │
│     → check_substance_allergy() — (if food detected)              │
│     NO LLM — direct DB queries + REST API calls                    │
│                                                                    │
│  5. _get_drug_classes()                    ✅ TRIGGERED (Layer 2)  │
│     → REST call to RxNorm RxClass API                              │
│     → NO LLM                                                       │
│                                                                    │
│  6. _get_fda_inactive_ingredients()        ✅ TRIGGERED (Layer 3)  │
│     → REST call to FDA OpenFDA API                                 │
│     → NO LLM                                                       │
│                                                                    │
│  7. AllergyResponseDoctor/Patient          ✅ TRIGGERED            │
│     → format_drug_allergy_check() or format_allergy_list()         │
│     → Template-based string formatting (NO LLM)                    │
│                                                                    │
│  8. _allergy_safety_net()                  ✅ TRIGGERED            │
│     → Post-processing on every response (NO LLM)                  │
│     → Skips if intent was already ALLERGY_QUERY                    │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│  AGENTS NOT TRIGGERED FOR ALLERGY QUERIES:                         │
│                                                                    │
│  ✗ SQLAgent              — Not needed (AllergyFetcher has own SQL) │
│  ✗ MCPAgent              — Not needed (no JSON lookup/dose calc)   │
│  ✗ KnowledgeAgent        — Not needed (no vector store query)      │
│  ✗ ResponseAgent (LLM)   — NOT triggered (no Ollama call)          │
│  ✗ ValidationAgent       — Not needed (allergy has own validation) │
│                                                                    │
│  ⚠️  THE LLM (Ollama/llama2) IS NEVER CALLED FOR ALLERGY QUERIES  │
│     Everything is deterministic: keywords → SQL → APIs → templates │
└────────────────────────────────────────────────────────────────────┘
```

### When IS the LLM (Ollama) Triggered?

The LLM is used only for **non-allergy** intents:

| Intent | LLM Used? | Where |
|--------|-----------|-------|
| `ALLERGY_QUERY` | **NO** | All responses are template-formatted from DB + API data |
| `MEDICATION_QUERY` (dosage) | **NO** | MCPAgent calculates dose from JSON + RxNorm |
| `MEDICATION_QUERY` (safety) | **NO** | AllergyFetcher handles drug safety check |
| `IMMUNIZATION_QUERY` | **NO** | ImmunizationOpenMRSFetcher + template formatting |
| `VITALS_QUERY` | **YES** | `SQLAgent.generate_sql_query()` — LLM generates SQL from NL question |
| `PATIENT_RECORD_QUERY` | **YES** | `SQLAgent.generate_sql_query()` — LLM generates SQL; `ResponseAgent.generate_doctor_response()` or `generate_patient_response()` — LLM formats the final answer |
| `MILESTONE_QUERY` | **YES** | `ResponseAgent.generate_milestone_response()` — LLM formats milestone data |
| `GENERAL_MEDICAL_QUERY` | **YES** | `ResponseAgent.generate_doctor_response()` — LLM generates from KB context |

### MCP Routing Labels (from `triage_agent.py`)

Each intent in `INTENT_KEYWORDS` has an `agent` field. These are **routing labels** that indicate which subsystem handles the query:

| MCP Label | What It Actually Routes To |
|-----------|--------------------------|
| `MCP_MEDICATION_AGENT` | `MCPAgent` (JSON/RxNorm/FDA), `AllergyOpenMRSFetcher` (allergy checks), `MedicationOpenMRSFetcher` (active/past meds) |
| `MCP_IMMUNIZATION_AGENT` | `ImmunizationOpenMRSFetcher` (queries OpenMRS vaccination records) |
| `MCP_MILESTONE_AGENT` | `MCPAgent.search_milestone()` (JSON lookup) + `ResponseAgent` (LLM formatting) |
| `SQL_AGENT` | `SQLAgent` (LLM-generated SQL → OpenMRS DB) + `ResponseAgent` (LLM formatting) |

> **Important**: The MCP label `MCP_MEDICATION_AGENT` is logged by the triage agent, but the actual handler is determined by the intent type in `main.py`. For `ALLERGY_QUERY`, the code in `main.py` directly calls `AllergyOpenMRSFetcher` — it never goes through `MCPAgent`.

---

## Files Involved

| File | Role |
|------|------|
| `main.py` | Central orchestrator — routes questions through pipelines, calls allergy fetcher, formats final output |
| `agents/triage_agent.py` | Intent classification — keyword matching to determine query type (ALLERGY_QUERY, MEDICATION_QUERY, etc.) |
| `agents/allergy_openmrs_fetcher.py` | Database + API layer — fetches allergies from OpenMRS, runs 3-layer drug safety check (direct match, RxNorm cross-reactivity, FDA excipient) |
| `agents/allergy_response.py` | Response formatters — `AllergyResponseDoctor` and `AllergyResponsePatient` format results for each role |
| `agents/drug_dosage_handler.py` | Drug name extraction — `extract_drug_name()` uses regex patterns to pull drug names from natural language |
| `database/db.py` | OpenMRS MySQL connection — executes raw SQL queries against the OpenMRS database |

---

## Workflow 1: "What allergies does this patient have?"

This is a **general allergy listing** query — no specific drug mentioned.

### Flowchart

```
  "What allergies does this patient have?"
       │
       ▼
┌──────────────────────────────────────┐
│ TriageAgent.classify_intent()        │  ← AGENT: TriageAgent
│ File: triage_agent.py                │  ← LLM: NO (keyword matching)
│                                      │  ← MCP Label: MCP_MEDICATION_AGENT
│ Keyword match: "allergies" found in  │
│ allergy_keywords list                │
│                                      │
│ Result: ALLERGY_QUERY                │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ main.py — ALLERGY_QUERY handler      │  ← AGENT: None (main.py logic)
│                                      │  ← LLM: NO
│ 1. extract_drug_name() → None        │  ← TOOL: drug_dosage_handler (regex)
│    (no drug name in question)        │
│                                      │
│ 2. Check food substances → None      │
│    (no food keywords found)          │
│                                      │
│ 3. Neither drug nor food detected    │
│    → Fall through to LIST ALL        │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ AllergyOpenMRSFetcher                │  ← AGENT: AllergyOpenMRSFetcher
│ get_patient_allergies(patient_id)    │  ← LLM: NO
│ File: allergy_openmrs_fetcher.py     │  ← DB: OpenMRS MySQL (SQL query)
│                                      │
│ SQL query to OpenMRS allergy tables: │
│ - allergy table                      │
│ - coded_allergen (concept name)      │
│ - allergen_type (DRUG/FOOD/ENV)      │
│ - severity                           │
│ - reactions                          │
│                                      │
│ Returns grouped dict:                │
│ {                                    │
│   'DRUG': [                          │
│     {'name': 'Penicillin',           │
│      'severity': 'Moderate',         │
│      'reactions': [...]}             │
│   ],                                 │
│   'ENVIRONMENT': [                   │
│     {'name': 'Dust',                 │
│      'severity': 'Mild', ...}        │
│   ]                                  │
│ }                                    │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ AllergyResponseDoctor/Patient        │  ← AGENT: AllergyResponse formatter
│ File: allergy_response.py            │  ← LLM: NO (template formatting)
│                                      │
│ Doctor: format_allergy_list()        │
│   → Clinical table with severity,    │
│     reactions, and types             │
│                                      │
│ Patient: format_allergy_list()       │
│   → Friendly warning with plain      │
│     language explanation             │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ _allergy_safety_net()                │  ← AGENT: Safety net (main.py)
│                                      │  ← LLM: NO
│ extract_drug_name() → None           │
│ No drug in question → SKIP           │
│ (returns result unchanged)           │
└──────────────┬───────────────────────┘
               │
               ▼
         Response to User
```

**Summary — Agents triggered:**
| Step | Agent/Component | LLM? | External API? |
|------|----------------|-------|---------------|
| Intent classification | TriageAgent | No | No |
| Drug extraction | extract_drug_name (regex) | No | No |
| Allergy fetch | AllergyOpenMRSFetcher | No | No (DB only) |
| Response formatting | AllergyResponseDoctor/Patient | No | No |
| Safety net | _allergy_safety_net | No | No |

### Example Output (Doctor)

```
======================================================================
ALLERGY REPORT — Patient Joshua (100008E)
======================================================================

DRUG ALLERGIES:
  ● Penicillin
    Severity: Moderate
    Reactions: Rash

ENVIRONMENT ALLERGIES:
  ● Dust
    Severity: Mild

Source: OpenMRS Patient Allergy Record
```

---

## Workflow 2: "Can I prescribe Salbutamol?"

This is a **safe drug** query — Salbutamol is NOT in the Penicillin drug class, so it should pass all 3 layers.

### Flowchart

```
  "Can I prescribe Salbutamol?"
       │
       ▼
┌──────────────────────────────────────┐
│ TriageAgent.classify_intent()        │  ← AGENT: TriageAgent
│ File: triage_agent.py                │  ← LLM: NO (keyword matching)
│                                      │  ← MCP Label: MCP_MEDICATION_AGENT
│ Step 1: Food check → No food words   │
│                                      │
│ Step 2: prescribe_patterns check     │
│  "can i prescribe" matches list:     │
│  ['can i prescribe', 'can we        │
│   prescribe', 'can i give', ...]    │
│                                      │
│  patient_context? No explicit        │
│  "patient" keyword, but             │
│  not has_food_substance → True       │
│                                      │
│  interaction check: no "together",   │
│  "with", "and" combo → OK           │
│                                      │
│ Result: ALLERGY_QUERY                │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ main.py — ALLERGY_QUERY handler      │  ← AGENT: None (main.py logic)
│                                      │  ← LLM: NO
│ 1. extract_drug_name() → "Salbutamol"│  ← TOOL: drug_dosage_handler (regex)
│    Pattern matched:                  │
│    r'prescribe\s+(\w+)'             │
│                                      │
│ 2. drug_name is set → skip food      │
│    substance check                   │
│                                      │
│ 3. Go to drug allergy check          │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ AllergyOpenMRSFetcher                │  ← AGENT: AllergyOpenMRSFetcher
│ check_drug_allergy("100008E",        │  ← LLM: NO
│                    "Salbutamol")      │  ← DB: OpenMRS MySQL
│ File: allergy_openmrs_fetcher.py     │  ← API: RxNorm + FDA
│                                      │
│ LAYER 1: Direct match                │
│  Patient allergies: [Penicillin,Dust]│
│  "salbutamol" in "penicillin"? No    │
│  "penicillin" in "salbutamol"? No    │
│  → No direct match                   │
│                                      │
│ LAYER 2: RxNorm cross-reactivity     │  ← EXTERNAL API: RxNorm RxClass
│  API call to RxClass:                │
│  GET rxclass/class/byDrugName.json   │
│    ?drugName=Salbutamol              │
│  Returns classes:                    │
│    ["Adrenergic beta-2 Receptor      │
│     Agonists", "SYMPATHOMIMETICS",   │
│     ...]                             │
│  Compare with "penicillin" →         │
│  No overlap → No cross-reactivity    │
│                                      │
│ LAYER 3: FDA excipient check         │  ← EXTERNAL API: FDA OpenFDA
│  Patient has Dust (ENVIRONMENT)      │
│  API call to openFDA:                │
│  GET api.fda.gov/drug/label.json     │
│    ?search=openfda.generic_name:     │
│     Salbutamol                       │
│  Check inactive ingredients for      │
│  allergen excipients → No match      │
│                                      │
│ Result:                              │
│ {                                    │
│   is_contraindicated: false,         │
│   message: "Salbutamol is safe.      │
│     No documented allergies or       │
│     cross-reactivity detected."      │
│ }                                    │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ AllergyResponseDoctor                │  ← AGENT: AllergyResponse formatter
│ format_drug_allergy_check()          │  ← LLM: NO (template formatting)
│ File: allergy_response.py            │
│ is_contraindicated == False          │
│ → "SAFE TO PRESCRIBE" section        │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ _allergy_safety_net()                │  ← AGENT: Safety net (main.py)
│                                      │  ← LLM: NO
│ intent == ALLERGY_QUERY → SKIP       │
│ (already handled by allergy check)   │
└──────────────┬───────────────────────┘
               │
               ▼
         Response to User
```

**Summary — Agents triggered:**
| Step | Agent/Component | LLM? | External API? |
|------|----------------|-------|---------------|
| Intent classification | TriageAgent | No | No |
| Drug extraction | extract_drug_name (regex) | No | No |
| DB allergy fetch | AllergyOpenMRSFetcher.get_patient_allergies() | No | No (DB only) |
| Layer 1 — Direct match | AllergyOpenMRSFetcher (in-memory compare) | No | No |
| Layer 2 — Cross-reactivity | _get_drug_classes() | No | **RxNorm RxClass API** |
| Layer 3 — Excipient | _get_fda_inactive_ingredients() | No | **FDA OpenFDA API** |
| Response formatting | AllergyResponseDoctor | No | No |
| Safety net | _allergy_safety_net (skipped) | No | No |

### Example Output (Doctor)

```
======================================================================
DRUG ALLERGY CHECK — SALBUTAMOL
Patient: Joshua (100008E)
======================================================================

[OK] SAFE TO PRESCRIBE

Salbutamol is safe. No documented allergies or cross-reactivity detected.

Documented Allergies:
  ● Penicillin (DRUG) — Moderate
  ● Dust (ENVIRONMENT) — Mild

Source: OpenMRS Allergy Record + RxNorm RxClass + FDA OpenFDA
======================================================================
```

---

## Workflow 3: "Can I give Ampicillin?"

This is a **dangerous drug** query — Ampicillin IS a Penicillin-class drug and should be detected by the cross-reactivity check.

### Flowchart

```
  "Can I give Ampicillin?"
       │
       ▼
┌──────────────────────────────────────┐
│ TriageAgent.classify_intent()        │  ← AGENT: TriageAgent
│ File: triage_agent.py                │  ← LLM: NO (keyword matching)
│                                      │  ← MCP Label: MCP_MEDICATION_AGENT
│ Step 1: Food check → No food words   │
│                                      │
│ Step 2: prescribe_patterns check     │
│  "can i give" matches list           │
│  not has_food_substance → True       │
│  No interaction indicators           │
│                                      │
│ Result: ALLERGY_QUERY                │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ main.py — ALLERGY_QUERY handler      │  ← AGENT: None (main.py logic)
│                                      │  ← LLM: NO
│ 1. extract_drug_name() → "Ampicillin"│  ← TOOL: drug_dosage_handler (regex)
│    Pattern matched:                  │
│    r'give\s+(\w+)'                   │
│                                      │
│ 2. drug_name is set → skip food      │
│    substance check                   │
│                                      │
│ 3. Go to drug allergy check          │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ AllergyOpenMRSFetcher                        │  ← AGENT: AllergyOpenMRSFetcher
│ check_drug_allergy("100008E", "Ampicillin")  │  ← LLM: NO
│ File: allergy_openmrs_fetcher.py             │  ← DB: OpenMRS MySQL
│                                              │  ← API: RxNorm (Layer 2 hit)
│ LAYER 1: Direct match                        │
│  "ampicillin" in "penicillin"? No            │
│  "penicillin" in "ampicillin"? No            │
│  → No direct match                           │
│                                              │
│ LAYER 2: RxNorm cross-reactivity     ← HIT  │  ← EXTERNAL API: RxNorm RxClass
│  API call to RxClass:                        │
│  GET rxclass/class/byDrugName.json           │
│    ?drugName=Ampicillin                      │
│  Returns classes:                            │
│    ["Penicillins with extended spectrum",     │
│     "PENICILLINS,AMINO DERIVATIVES", ...]    │
│                                              │
│  Compare with patient's allergen:            │
│    allergen = "Penicillin"                   │
│    allergen_core = "penicillin"              │
│    class = "Penicillins with extended..."    │
│                                              │
│  "penicillin" in "penicillins with..." → YES │
│                                              │
│  ⚠️ STOPS HERE — Layer 3 NOT called          │
│  (contraindication found at Layer 2)         │
│                                              │
│ Result:                                      │
│ {                                            │
│   is_contraindicated: true,                  │
│   allergen_matched: "Penicillin",            │
│   severity: "Moderate",                      │
│   cross_reactivity: "Penicillins with        │
│     extended spectrum",                      │
│   message: "CONTRAINDICATED                  │
│     (Cross-Reactivity): Ampicillin           │
│     belongs to the Penicillins with          │
│     extended spectrum drug class..."         │
│ }                                            │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ AllergyResponseDoctor/Patient        │  ← AGENT: AllergyResponse formatter
│ format_drug_allergy_check()          │  ← LLM: NO (template formatting)
│ File: allergy_response.py            │
│ is_contraindicated == True           │
│ → "CONTRAINDICATED" section          │
│ → Cross-reactivity explanation       │
│ → DO NOT PRESCRIBE warning           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ _allergy_safety_net()                │  ← AGENT: Safety net (main.py)
│                                      │  ← LLM: NO
│ intent == ALLERGY_QUERY → SKIP       │
│ (already handled by allergy check)   │
└──────────────┬───────────────────────┘
               │
               ▼
         Response to User
```

**Summary — Agents triggered:**
| Step | Agent/Component | LLM? | External API? |
|------|----------------|-------|---------------|
| Intent classification | TriageAgent | No | No |
| Drug extraction | extract_drug_name (regex) | No | No |
| DB allergy fetch | AllergyOpenMRSFetcher.get_patient_allergies() | No | No (DB only) |
| Layer 1 — Direct match | AllergyOpenMRSFetcher (in-memory compare) | No | No |
| Layer 2 — Cross-reactivity | _get_drug_classes() | No | **RxNorm RxClass API** (HIT!) |
| Layer 3 — Excipient | _get_fda_inactive_ingredients() | **SKIPPED** | **SKIPPED** (Layer 2 found match) |
| Response formatting | AllergyResponseDoctor/Patient | No | No |
| Safety net | _allergy_safety_net (skipped) | No | No |

### Example Output (Doctor)

```
======================================================================
DRUG ALLERGY CHECK — AMPICILLIN
Patient: Joshua (100008E)
======================================================================

[CONTRAINDICATED] DO NOT PRESCRIBE

Matched Allergen: Penicillin
Severity: Moderate
Cross-Reactivity: Ampicillin belongs to the "Penicillins with
  extended spectrum" drug class

CONTRAINDICATED (Cross-Reactivity): Ampicillin belongs to the
Penicillins with extended spectrum drug class. Patient has documented
allergy to Penicillin (Severity: Moderate).

RECOMMENDATION: DO NOT PRESCRIBE. Consider alternatives outside
the Penicillin drug family.

Source: OpenMRS Allergy Record + RxNorm RxClass
======================================================================
```

### Example Output (Patient/Parent)

```
======================================================================
MEDICATION SAFETY CHECK — AMPICILLIN
For: Joshua (100008E)
======================================================================

[WARNING] THIS MEDICATION MAY NOT BE SAFE

Your child has a documented allergy to: Penicillin
Severity: Moderate
Note: Ampicillin belongs to the same drug family
  (Penicillins with extended spectrum) as the allergen.

Do NOT give this medication to your child.
Contact your doctor for a safe alternative.

Source: Patient Medical Records
======================================================================
```

---

## 3-Layer Allergy Check (`check_drug_allergy`)

This is the core safety logic in `allergy_openmrs_fetcher.py`:

```
  check_drug_allergy(patient_id, drug_name)
       │
       ▼
┌──────────────────────────────────────────┐
│ Fetch patient allergies from OpenMRS DB  │
│ get_patient_allergies(patient_id)        │
│ Returns: {DRUG: [...], FOOD: [...],      │
│           ENVIRONMENT: [...]}            │
└──────────────┬───────────────────────────┘
               │
       ┌───────┴──────────────────────────┐
       ▼                                  │
┌────────────────────┐                    │
│ LAYER 1            │                    │
│ Direct Match       │                    │
│                    │                    │
│ Is drug_name a     │── YES ──► RETURN   │
│ substring of any   │          CONTRAINDICATED
│ DRUG allergen?     │          (direct match)
│                    │                    │
└────────┬───────────┘                    │
         │ NO                             │
         ▼                                │
┌────────────────────┐                    │
│ LAYER 2            │                    │
│ RxNorm Cross-      │                    │
│ Reactivity         │                    │
│                    │                    │
│ 1. Call RxClass API│                    │
│    to get drug's   │                    │
│    pharmacological │                    │
│    classes         │                    │
│                    │                    │
│ 2. Compare class   │── YES ──► RETURN   │
│    names with      │          CONTRAINDICATED
│    patient's DRUG  │          (cross-reactivity)
│    allergens       │                    │
│                    │                    │
└────────┬───────────┘                    │
         │ NO                             │
         ▼                                │
┌────────────────────┐                    │
│ LAYER 3            │                    │
│ FDA Excipient      │                    │
│ Check              │                    │
│                    │                    │
│ 1. Call FDA API    │                    │
│    to get inactive │                    │
│    ingredients     │                    │
│                    │                    │
│ 2. Check if any    │── YES ──► RETURN   │
│    FOOD/ENV        │          CONTRAINDICATED
│    allergen maps   │          (excipient)
│    to an excipient │                    │
│    in the drug     │                    │
│                    │                    │
└────────┬───────────┘                    │
         │ NO                             │
         ▼                                │
┌────────────────────┐                    │
│ RETURN: SAFE       │                    │
│ No contraindication│                    │
│ detected           │                    │
└────────────────────┘                    │
```

### Layer Details

| Layer | Data Source | What It Checks | Example |
|-------|-----------|----------------|---------|
| 1 — Direct Match | OpenMRS DB | Drug name is a substring of a DRUG allergen | "Penicillin" query on patient allergic to "Penicillin" |
| 2 — Cross-Reactivity | RxNorm RxClass API | Drug belongs to same pharmacological class as an allergen | Ampicillin → "Penicillins" class → matches "Penicillin" allergen |
| 3 — Excipient | FDA OpenFDA API | Drug's inactive ingredients contain substance matching a FOOD/ENV allergen | Drug contains lactose → patient has Milk allergy |

---

## Safety Net (Option B)

The **allergy safety net** is a post-processing step that runs after EVERY response in both the Doctor and Patient pipelines. It catches cases where a drug name was mentioned but the intent was NOT classified as `ALLERGY_QUERY`.

### Why It Exists

Some queries like `"Would Amoxicillin be appropriate for this patient?"` might be classified as `GENERAL_MEDICAL_QUERY` because no allergy or prescribe keyword is present. Without the safety net, the response would have no allergy information.

### Flowchart

```
  Any pipeline response
       │
       ▼
┌──────────────────────────────────────┐
│ _allergy_safety_net()                │
│                                      │
│ 1. Has patient_id? ── No ──► SKIP   │
│                                      │
│ 2. intent == ALLERGY_QUERY?          │
│    ── Yes ──► SKIP (already handled) │
│                                      │
│ 3. extract_drug_name(question)       │
│    ── None ──► SKIP (no drug found)  │
│                                      │
│ 4. Drug found! Run background        │
│    allergy check:                    │
│    check_drug_allergy(patient, drug) │
│                                      │
│ 5a. Contraindicated?                 │
│     ── Yes ──► PREPEND WARNING       │
│     (loud alert before the           │
│      original response)              │
│                                      │
│ 5b. Safe?                            │
│     ── Yes ──► APPEND clearance note │
│     (subtle note after the           │
│      original response)              │
└──────────────────────────────────────┘
```

### Where It's Called

```python
# main.py — Doctor Pipeline (line ~526)
def _doctor_pipeline(self, ...):
    result = self._handle_shared_intents(...)
    return self._allergy_safety_net(result, ...)  # ← Always runs

# main.py — Patient Pipeline (line ~549)
def _patient_pipeline(self, ...):
    result = self._handle_shared_intents(...)
    return self._allergy_safety_net(result, ...)  # ← Always runs
```

---

## External APIs Used

### 1. RxNorm RxClass API (Layer 2)

- **Purpose**: Look up which pharmacological classes a drug belongs to
- **Endpoint**: `https://rxnav.nlm.nih.gov/REST/rxclass/class/byDrugName.json`
- **Example**: `?drugName=Ampicillin` → returns `["Penicillins with extended spectrum", ...]`
- **Used in**: `_get_drug_classes()` in `allergy_openmrs_fetcher.py`
- **Free**: Yes, no API key required

### 2. FDA OpenFDA API (Layer 3)

- **Purpose**: Look up inactive ingredients (excipients) in a drug's formulation
- **Endpoint**: `https://api.fda.gov/drug/label.json`
- **Example**: `?search=openfda.brand_name:"Salbutamol"` → returns label with inactive ingredients section
- **Used in**: `_get_fda_inactive_ingredients()` in `allergy_openmrs_fetcher.py`
- **Free**: Yes, no API key required (rate-limited)

---

## Key Design Decisions

### 1. Keyword Matching, Not ML
Intent classification uses deterministic keyword matching in `triage_agent.py`, not a machine learning model. This makes routing predictable and debuggable — every classification can be traced to exactly which keyword triggered it.

### 2. Priority-Based Routing
The `classify_intent()` function checks patterns in priority order:
1. Food/substance safety queries (e.g., "can I give egg to my child")
2. Prescribe/give-drug patterns (e.g., "can I prescribe Ampicillin")
3. Dosage keywords
4. Allergy keywords
5. Default keyword scoring

### 3. Safety Net Over Accuracy
Option B (always check allergies when a drug is detected) was chosen over trying to make intent classification perfect. It's better to run a redundant allergy check than to miss a contraindication.

### 4. Dual Formatters
Every allergy response has two formatters:
- **Doctor**: Clinical language, severity levels, cross-reactivity details, prescribing recommendations
- **Patient**: Plain language, "do NOT give" warnings, when to seek help, reassurance

### 5. Excipient Mapping
The `FOOD_ALLERGEN_TO_EXCIPIENT` dictionary maps common food/environment allergens to their pharmaceutical excipient equivalents. For example, a milk allergy maps to checking for lactose, casein, and whey in inactive ingredients.
