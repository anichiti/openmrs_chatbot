# OpenMRS Clinical Chatbot – Architecture Flowcharts

Two flowcharts are provided below. PNG images (high-resolution, 150 dpi) are also
available alongside this file and can be regenerated at any time with:

```bash
python docs/flowcharts/generate_flowcharts.py
```

---

## Flowchart 1 — OpenMRS Clinical Chatbot: An Intelligent Agent-Based Architecture for Pediatric Clinical Decision Support

> Traces the full processing pipeline from raw user input through the multi-agent
> system to the final, role-aware clinical response.

📄 High-resolution PNG: [`flowchart1_agent_architecture.png`](flowchart1_agent_architecture.png)

```mermaid
flowchart TD
    A(["👤 USER INPUT\nDoctor | Patient | Parent"])

    A --> B["🔍 TRIAGE AGENT\n• Intent Classification (11 categories)\n• User Role Detection: Doctor / Patient\n• Entity Extraction: Patient ID, Drug, Vaccine\n• Returns: intent, user_type, confidence"]

    B --> C{{"INTENT ROUTER\n(Select Specialised Agent)"}}

    C -->|MEDICATION| D["💊 MEDICATION AGENT\n• Drug Dosage Handler\n• Medication OpenMRS Fetcher\n• Medication Allergy Checker\n• Dosage / Side-Effects / Admin / Emergency"]
    C -->|ALLERGY| E["🚫 ALLERGY AGENT\n• Allergy OpenMRS Fetcher\n• Drug–Allergy Cross-Check\n• Contraindication Alerts"]
    C -->|IMMUNIZATION| F["💉 IMMUNIZATION AGENT\n• Immunization OpenMRS Fetcher\n• Vaccine Schedule Lookup\n• Next-Dose Prediction"]
    C -->|VITALS| G["📊 VITALS AGENT\n• SQL Agent → OpenMRS obs\n• BMI Calculation\n• Height / Weight / BP"]
    C -->|PATIENT RECORD| H["📋 PATIENT RECORD AGENT\n• SQL Agent → Full Profile\n• Demographics\n• Clinical History"]
    C -->|HYBRID| I["🔀 HYBRID AGENT\n• Hybrid Question Detector\n• Multi-Intent Handler\n• Combined Data Sources"]

    D & E & F & G & H & I --> J

    subgraph J["📦 DATA RETRIEVAL LAYER"]
        J1["🗄️ OpenMRS MySQL DB\npatient · person · orders\nobs · allergy · immunization"]
        J2["📚 JSON Knowledge Bases\ndrug_knowledge_base.json\nimmunization.json · milestones.json"]
        J3["🔎 ChromaDB Vector Store\nWHO Essential Medicines (PDF)\nCDC Milestone Checklists (PDF)"]
        J4["🌐 External APIs\nRxNorm API · FDA API"]
    end

    J --> K["🛡️ VALIDATION AGENT  (Safety Layer)\n• Verify data existence — prevent hallucinations\n• Validate patient IDs & DB connections\n• Block empty / unsafe responses"]

    K --> L["📝 RESPONSE AGENT  (Role-Based Formatting)\n• Doctor View: clinical detail, drug IDs, safety alerts\n• Patient / Parent View: plain language, simplified"]

    L --> M(["📤 OUTPUT\nFormatted JSON  |  responses.json  |  Audit Log"])

    subgraph PED["🧒 PAEDIATRIC CLINICAL DECISION SUPPORT FEATURES"]
        P1["Age & Weight-Based\nDrug Dosage Calculation"]
        P2["Immunization Schedule\nTracking & Next-Dose Prediction"]
        P3["Developmental Milestone\nAssessment (CDC / WHO)"]
        P4["Drug–Allergy Safety Checks\n& Contraindication Alerts"]
        P5["BMI Percentile Calculation\n(Age-Adjusted for Children)"]
    end

    M -.->|feeds into| PED

    style A fill:#2E4057,color:#fff
    style B fill:#048A81,color:#fff
    style C fill:#048A81,color:#fff
    style D fill:#1565C0,color:#fff
    style E fill:#1565C0,color:#fff
    style F fill:#1565C0,color:#fff
    style G fill:#1565C0,color:#fff
    style H fill:#1565C0,color:#fff
    style I fill:#1565C0,color:#fff
    style J fill:#EDE7F6,stroke:#6A1B9A
    style J1 fill:#6A1B9A,color:#fff
    style J2 fill:#6A1B9A,color:#fff
    style J3 fill:#6A1B9A,color:#fff
    style J4 fill:#6A1B9A,color:#fff
    style K fill:#B71C1C,color:#fff
    style L fill:#1B5E20,color:#fff
    style M fill:#4E342E,color:#fff
    style PED fill:#FBE9E7,stroke:#E65100
    style P1 fill:#E65100,color:#fff
    style P2 fill:#E65100,color:#fff
    style P3 fill:#E65100,color:#fff
    style P4 fill:#E65100,color:#fff
    style P5 fill:#E65100,color:#fff
```

---

## Flowchart 2 — OpenMRS-Integrated Chatbot for Pediatric Care: A Knowledge-Source Framework for Clinical Query Scenario Classification

> Shows how each of the 11 clinical query scenario categories is mapped to its
> primary knowledge source(s) within the OpenMRS-integrated chatbot.

📄 High-resolution PNG: [`flowchart2_knowledge_classification.png`](flowchart2_knowledge_classification.png)

```mermaid
flowchart TD
    Q(["💬 CLINICAL QUERY\n(Natural Language Input)"])

    Q --> T["🔍 TRIAGE AGENT\nKeyword Matching  •  LLM (Ollama / llama2)  •  Confidence Scoring"]

    T --> CL["🎯 CLINICAL QUERY SCENARIO CLASSIFIER\nReturns: intent · user_role · patient_id · confidence"]

    CL --> CATS["QUERY SCENARIO CATEGORIES"]

    CATS --> M1["MEDICATION_QUERY\nDrug dosage, side effects, dosing frequency"]
    CATS --> M2["MEDICATION_INFO_QUERY\nCurrent prescribed medications for patient"]
    CATS --> M3["MEDICATION_ADMINISTRATION_QUERY\nHow to administer / give a medication"]
    CATS --> M4["MEDICATION_SIDE_EFFECTS_QUERY\nAdverse effects, toxicity, reactions"]
    CATS --> M5["⚠️ MEDICATION_EMERGENCY_QUERY\nOverdose, missed dose — HIGH PRIORITY"]
    CATS --> M6["MEDICATION_COMPATIBILITY_QUERY\nDrug–drug interactions, simultaneous use"]
    CATS --> AL["ALLERGY_QUERY\nDrug-allergy contraindication checks"]
    CATS --> IM["IMMUNIZATION_QUERY\nVaccination history, next dose, schedules"]
    CATS --> VI["VITALS_QUERY\nVital signs, BMI, weight, height, BP"]
    CATS --> PR["PATIENT_RECORD_QUERY\nFull demographic & clinical profile"]
    CATS --> HY["HYBRID_QUERY\nMulti-intent — combined knowledge sources"]

    M1 & M3 & M4 & M5 & M6 -->|"Primary"| KS2["📚 JSON Knowledge Bases\ndrug_knowledge_base.json\n• Indications & dosing\n• Paediatric mg/kg doses\n• Contraindications\n• Drug interactions"]
    M2 & AL & VI & PR -->|"Primary"| KS1["🗄️ OpenMRS MySQL DB\norders  – active medications\nallergy – allergies + severity\nobs     – vitals\npatient – demographics"]
    IM -->|"Primary"| KS1
    IM -->|"Secondary"| KS2b["📚 immunization.json\nVaccine schedules\nDose intervals"]
    M5 & M1 -->|"Fallback RAG"| KS3["🔎 ChromaDB Vector Store\nWHO Essential Medicines (PDF)\nCDC Milestone Checklists (PDF)\n(Semantic retrieval)"]
    M5 & M6 -->|"Supplement"| KS4["🌐 External APIs\nRxNorm API – drug concepts\nFDA API   – labelling & recalls"]
    HY -->|"All sources"| KS1
    HY -->|"All sources"| KS2
    HY -->|"All sources"| KS3
    HY -->|"All sources"| KS4

    style Q fill:#2E4057,color:#fff
    style T fill:#00695C,color:#fff
    style CL fill:#1565C0,color:#fff
    style CATS fill:#37474F,color:#fff
    style M1 fill:#1565C0,color:#fff
    style M2 fill:#1565C0,color:#fff
    style M3 fill:#1565C0,color:#fff
    style M4 fill:#1565C0,color:#fff
    style M5 fill:#C62828,color:#fff
    style M6 fill:#1565C0,color:#fff
    style AL fill:#6A1B9A,color:#fff
    style IM fill:#00838F,color:#fff
    style VI fill:#4527A0,color:#fff
    style PR fill:#37474F,color:#fff
    style HY fill:#E65100,color:#fff
    style KS1 fill:#6A1B9A,color:#fff
    style KS2 fill:#00838F,color:#fff
    style KS2b fill:#00838F,color:#fff
    style KS3 fill:#4527A0,color:#fff
    style KS4 fill:#558B2F,color:#fff
```

---

## Knowledge Source → Query Scenario Mapping Summary

| Knowledge Source | Primary Query Scenarios |
|---|---|
| **OpenMRS MySQL DB** | `MEDICATION_INFO_QUERY`, `ALLERGY_QUERY`, `IMMUNIZATION_QUERY`, `VITALS_QUERY`, `PATIENT_RECORD_QUERY`, `HYBRID_QUERY` |
| **drug_knowledge_base.json** | `MEDICATION_QUERY`, `MEDICATION_ADMINISTRATION_QUERY`, `MEDICATION_SIDE_EFFECTS_QUERY`, `MEDICATION_EMERGENCY_QUERY`, `MEDICATION_COMPATIBILITY_QUERY` |
| **immunization.json** | `IMMUNIZATION_QUERY` (schedule lookup) |
| **milestones.json** | Developmental milestone queries (part of `PATIENT_RECORD_QUERY` / `HYBRID_QUERY`) |
| **ChromaDB (WHO / CDC PDFs)** | `MEDICATION_QUERY` fallback, `MEDICATION_EMERGENCY_QUERY`, `HYBRID_QUERY` |
| **RxNorm API** | `MEDICATION_COMPATIBILITY_QUERY`, `HYBRID_QUERY` |
| **FDA API** | `MEDICATION_EMERGENCY_QUERY`, `MEDICATION_COMPATIBILITY_QUERY`, `HYBRID_QUERY` |

---

## Regenerating the PNG Images

```bash
# From the repository root
pip install matplotlib pillow   # only needed once
python docs/flowcharts/generate_flowcharts.py
```

Output files:
- `docs/flowcharts/flowchart1_agent_architecture.png`
- `docs/flowcharts/flowchart2_knowledge_classification.png`
