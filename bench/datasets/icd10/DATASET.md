# ICD-10 clinical notes: dataset audit

Dataset: `birgermoell/icd10-clinical-notes` on Hugging Face (CC-BY-4.0,
synthetic notes, no patient data). Pinned revision
`e4192bde319f7513f98796a97948168f965d461c`. Audited 2026-09-21.

## What the files contain

Row fields: `id`, `code`, `language`, `name`, `journal_note`, `label`.

- 1,802 rows (1,441 train + 361 test) = 53 codes × 34 languages.
- `language` and `name` describe the **diagnosis name's** translation, not the
  note. The notes come in two languages only.
- **106 distinct notes**: exactly two per code. One English note is shared by
  the 33 non-Swedish rows; one Swedish note belongs to the `sv` row. No note
  maps to two codes.
- **48 templated notes** (24 per language): "Patient diagnosed with
  <name>. Assessment and plan documented." / "Patient diagnosticerad med
  <namn>. ...". They contain the answer verbatim.
- **58 clinical notes** (29 per language): realistic shorthand with symptoms,
  vitals, labs and treatment, e.g. N18 "eGFR 42. Proteinuria 0.5g/d. BP
  controlled on ACEi...". Some still name the diagnosis ("Dx: Viral
  gastroenteritis"), but not in the official ICD-10 wording.

## Why the obvious setup is wrong

- **`name` is the answer.** Anything that sends the whole row leaks the label.
  Send `journal_note` only.
- **Rows are not items.** Scoring all 1,802 rows scores the same 106 notes up to
  33 times each, which inflates n about 17× and makes the intervals meaningless.
- **Train/test leakage.** 53 of the 62 distinct test notes also appear in
  train, so the shipped TF-IDF (98.6%) and multilingual-embedding (99.7%)
  classifiers memorized them. There is no note-disjoint split within a
  language: each code has one note per language. A trained baseline is
  therefore not meaningful here. Use `stringmatch` as the no-model floor instead.
- **Templated notes are free points.** `stringmatch` gets all 24 English
  templated notes. They can't separate models, so report them as a sanity check.

## Slices and what to claim

| Slice | n | Use |
|---|---|---|
| en/clinical | 29 | Headline accuracy |
| en/templated | 24 | Sanity check: every competent model should score about 100% |
| sv/clinical | 29 | Non-English robustness. TypeSafe says English is Jev's strongest language |
| sv/templated | 24 | Sanity check in Swedish (the name is in Swedish, so the English-label `stringmatch` misses almost all of these) |

A ±18-point interval at n=29 means this set can show large differences (for
example, "Jev misses a third of realistic notes that Opus gets right") but not
fine rankings. For a sharper benchmark, keep this as a smoke-level study and add
a larger set, such as a de-identified clinical coding corpus you are licensed to use.

## Error analysis hints

Codes that sit close together, where a wrong answer is informative rather than
careless:

- E10 / E11 / O24 (diabetes type 1, type 2, in pregnancy)
- I20 / I21 / I25 (angina, acute MI, chronic ischemic heart disease)
- F32 / F33 / F41 (single depressive episode, recurrent depression, anxiety)
- J44 / J45 (COPD, asthma); J06 / J18 / R05 (URI, pneumonia, cough)
- G43 / R51 (migraine, headache); M54 / R10 (back pain, abdominal pain)
- S52 / S72 (forearm, femur fracture); N18 / N39 (CKD, other urinary)

Notes whose key evidence is numeric (eGFR, HbA1c, BP readings, PEF
variability) exercise Jev's documented weakness with numbers. Tag them if you
want a "numeric evidence" slice.
