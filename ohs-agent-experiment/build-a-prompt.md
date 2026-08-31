# Build A opening prompt

Paste everything below the line as the first message of a fresh agent session
started in `~/AndroidStudioProjects/anc-build-a-cold`.

---

Build an Android app for nurses at a small clinic to track antenatal care
(ANC) visits.

1. **Register screen:** a list of currently pregnant patients showing name,
   age, estimated due date, and current weeks of pregnancy, sorted by due
   date (soonest first).
2. Tapping a patient opens a **patient detail screen** showing her past ANC
   visits: date, weight, blood pressure, and hemoglobin if recorded.
3. From the detail screen the nurse can **record a new ANC visit** by
   filling a form with: visit date, gestational age in weeks, weight (kg),
   systolic and diastolic blood pressure (mmHg), any danger signs (none /
   vaginal bleeding / severe headache / blurred vision / fever, multiple
   allowed), and free-text notes.
4. Saving the form persists the visit; it appears in the patient's visit
   list and survives app restart.

The clinic already has these three patients on file, each with one prior
visit:

| Name | Date of birth | Est. due date | Last visit | Weight | BP | Hb |
|---|---|---|---|---|---|---|
| Emily Carter | 1996-04-12 | 2026-12-05 | 2026-08-10 | 68.5 kg | 118/76 | 11.8 g/dL |
| Sarah Mitchell | 1990-11-02 | 2027-01-20 | 2026-08-12 | 61.2 kg | 110/70 | 12.4 g/dL |
| Grace Thompson | 2001-07-30 | 2026-10-15 | 2026-08-05 | 72.0 kg | 128/84 | 10.2 g/dL |

Use whatever architecture, libraries, data model, and storage you think are
best. The three existing patients above should be present in the app as
starting data.
