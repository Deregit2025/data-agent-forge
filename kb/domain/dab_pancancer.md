# Knowledge Base: Pancancer Dataset

## 1. Dataset Overview
This dataset contains multi-cancer clinical and molecular data from TCGA (The Cancer Genome Atlas), covering patient demographics, tumor characteristics, treatment history, somatic mutations, and gene expression across multiple cancer types.

---

## 2. Tables

### PostgreSQL — `clinical_info`
Patient-level clinical records across multiple cancer types.

| Field | Meaning | Notes |
|---|---|---|
| `Patient_description` | Free-text summary of patient record | Includes TCGA barcode, UUID, sex, vital status |
| `patient_id` | Numeric portion of TCGA barcode | e.g., `"1953"` from `TCGA-31-1953` |
| `days_to_birth` | Days from birth to diagnosis (negative) | e.g., `-19064.0` |
| `days_to_death` | Days from diagnosis to death | `"[Not Applicable]"` if alive |
| `days_to_last_followup` | Days to last known contact | Stored as `text` despite numeric values |
| `age_at_initial_pathologic_diagnosis` | Age in years at diagnosis | `double precision` |
| `pathologic_stage` / `clinical_stage` | TNM staging | Values like `"Stage IIIC"`, `"Stage IV"`, or `"[Not Applicable]"` |
| `tumor_tissue_site` | Primary tumor location | e.g., `"Ovary"`, `"Lung"` |
| `histological_type` | Tumor histology | e.g., `"Serous Cystadenocarcinoma"` |
| `icd_10` / `icd_o_3_site` | Disease classification codes | e.g., `"C56.9"` |
| `person_neoplasm_cancer_status` | Current tumor status | `"WITH TUMOR"` or `"TUMOR FREE"` |
| `tissue_source_site` | Numeric code for collection site | Links to TCGA site registry |

**Important:** Many fields use `"[Not Applicable]"` (string) rather than NULL for missing/irrelevant values.

---

### DuckDB — `Mutation_Data`
Somatic mutation calls per patient per gene.

| Field | Meaning |
|---|---|
| `ParticipantBarcode` | Full TCGA participant ID (e.g., `TCGA-AX-A3G8`) |
| `Hugo_Symbol` | Mutated gene name |
| `Variant_Classification` | Mutation type: `Missense_Mutation`, `Frame_Shift_Del`, `Frame_Shift_Ins`, etc. |
| `HGVSp_Short` | Protein-level change (e.g., `p.S351P`) |
| `HGVSc` | cDNA-level change |
| `FILTER` | Quality filter flag (e.g., `ndp`, `wga`) |
| `CENTERS` | Calling pipelines used (pipe-delimited) |

---

### DuckDB — `RNASeq_Expression`
Gene-level RNA expression per patient sample.

| Field | Meaning |
|---|---|
| `ParticipantBarcode` | Full TCGA participant ID |
| `Symbol` | Gene name |
| `Entrez` | Entrez gene ID (integer) |
| `normalized_count` | Normalized expression value (double) |
| `SampleTypeLetterCode` | Sample type code (e.g., `TP` = primary tumor) |

---

## 3. Join Keys

| Join | Key | Format Note |
|---|---|---|
| `clinical_info` ↔ `Mutation_Data` | `patient_id` ↔ derived from `ParticipantBarcode` | Extract last segment: `TCGA-XX-{patient_id}` |
| `Mutation_Data` ↔ `RNASeq_Expression` | `ParticipantBarcode` | Identical format across both DuckDB tables |

> **Critical:** `clinical_info.patient_