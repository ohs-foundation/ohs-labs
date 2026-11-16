# Experiment 1: token savings and scaling

How many tokens does a patient record cost in each format, and how big a
record fits on the phone before the context and memory run out? The
results are in the [folder README](../README.md#key-results). This page
explains the design and how to reproduce it.

Set up the model and the emulator first, and install `slm-bench`. Both
are described in the [folder README](../README.md#setup).

## Design

**The patient.** One synthetic [Synthea](https://github.com/synthetichealth/synthea)
patient with 20 years of history, cut into 7 sizes. Each size is the most
recent visits, with everything recorded at them and every resource they
refer to.

| Visits | FHIR resources |
|---|---|
| 1 | 47 |
| 2 | 56 |
| 5 | 95 |
| 10 | 166 |
| 20 | 280 |
| 40 | 618 |
| 51 | 703 |

Only clinical resources are kept: `Observation`, `Condition`,
`Procedure`, `Immunization`, `MedicationRequest` and
`AllergyIntolerance`, plus the `Patient`, its `Encounter`s and the
`Medication`s they refer to. Billing resources are left out.

**The formats.** The same data in 4 formats. The example is one body
weight.

| Format | What it is | Example |
|---|---|---|
| A, raw JSON | Synthea's FHIR JSON | `{"resourceType": "Observation", "meta": {...}, "category": [...], "code": {"coding": [{"system": "http://loinc.org", "code": "29463-7", "display": "Body Weight"}], ...}, "valueQuantity": {"value": 92, "unit": "kg", ...}}` (807 characters) |
| B, pruned JSON | A without `meta`, `text`, `extension`, `modifierExtension` and `identifier` | The same, 690 characters |
| C, view rows | Rows from Tokempic's SQL-on-FHIR views, as CSV | `2025-12-03T07:45:49+07:00,29463-7,Body Weight,92,kg` |
| D, Tokempic | The same rows in Tokempic's Markdown template | `- 2025-12-03T07:45:49+07:00 \| 29463-7 \| Body Weight \| 92 \| kg` |

C and D use the views in [`views/`](views/). They are Tokempic's views
with blood pressure and coded results fixed, see
[`views/README.md`](views/README.md).

**The prompt.** Every device run sends "Summarize this patient record in
3 bullet points." followed by the record.

## Setup

You need Python 3, Node.js and Docker, plus:

```bash
# Python packages, for counting tokens and the chart
python3 -m venv ~/venvs/slm && ~/venvs/slm/bin/pip install litert-lm matplotlib

# Tokempic, with tsx so it runs under Node (we used commit 4b112da)
git clone https://github.com/recodelabs/tokempic ~/AndroidStudioProjects/tokempic
cd ~/AndroidStudioProjects/tokempic && npm install && npm install --no-save tsx

# A FHIR server for Tokempic to read from
docker run -d --name slm-hapi -p 8090:8080 hapiproject/hapi:latest
```

HAPI takes about a minute to start. It is ready when
`curl http://localhost:8090/fhir/metadata` returns JSON.

`run_device.sh` uses the `adb` from Android Studio's default SDK folder.
Set `ADB` to use another one.

Run all steps from this folder. Steps 1 and 2 are optional, because the
slices are already in `data/A-raw/` and Synthea's hospital and
practitioner bundles are in `data/synthea/`. Synthea makes random
patients, so rerunning steps 1 and 2 gives a different patient.

## Steps

**1. Generate patients (optional).** Writes FHIR bundles to
`~/tools/synthea/output/fhir/`.

```bash
mkdir -p ~/tools/synthea && cd ~/tools/synthea
curl -L -o synthea.jar https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar
java -jar synthea.jar -p 5 --exporter.years_of_history 20
```

**2. Cut one patient into slices (optional).** Writes
`data/A-raw/visits-NN.json`. We used
`Miquel905_Jenkins714_23b5e581-d14c-0e84-988e-dffb5ceb2fe4.json`. The
resource counts it prints leave out the `Patient`, so they are 1 lower
than the table above. If you use a new patient, also copy Synthea's
`hospitalInformation*.json` and `practitionerInformation*.json` over the
files in `data/synthea/`.

```bash
python3 make_slices.py ~/tools/synthea/output/fhir/<patient>.json data/A-raw
```

**3. Load the slices into HAPI.** The hospital and practitioner bundles
go first, because the slices refer to them. Each slice becomes its own
patient with an ID prefix, such as `v01-` for 1 visit. Every line should
end in `200`.

```bash
python3 load_slices.py http://localhost:8090/fhir data/A-raw data/synthea/hospitals.json data/synthea/practitioners.json
```

**4. Make format B.**

```bash
python3 prune.py data/A-raw data/B-pruned
```

**5. Make formats C and D with Tokempic.** `PID` is the patient's ID,
the last part of the Synthea file name.

```bash
export TOKEMPIC_DIR=~/AndroidStudioProjects/tokempic
TSX=$TOKEMPIC_DIR/node_modules/.bin/tsx
PID=23b5e581-d14c-0e84-988e-dffb5ceb2fe4
for f in data/A-raw/visits-*.json; do
  n=$(basename $f .json); v=v${n#visits-}
  $TSX tokempic-node.mjs --patient $v-$PID --server http://localhost:8090/fhir --no-cache --views views > data/D-markdown/$n.md
  $TSX tokempic-node.mjs --patient $v-$PID --server http://localhost:8090/fhir --no-cache --views views --template rows-template.eta > data/C-rows/$n.txt
done
```

**6. Count tokens** with the model's own tokenizer. Writes
`results/tokens.csv`.

```bash
~/venvs/slm/bin/python count_tokens.py ~/models/gemma-4-E2B-it.litertlm data results/tokens.csv
```

**7. Run on the device.** One run per command. The arguments are the
file, the context size and the backend. Pick the smallest context that
fits the prompt.

```bash
./run_device.sh data/D-markdown/visits-01.md 4096 cpu
./run_device.sh data/D-markdown/visits-02.md 4096 cpu
./run_device.sh data/D-markdown/visits-05.md 8192 cpu
./run_device.sh data/D-markdown/visits-10.md 8192 cpu
./run_device.sh data/D-markdown/visits-20.md 16384 cpu
./run_device.sh data/D-markdown/visits-40.md 32768 cpu
./run_device.sh data/D-markdown/visits-51.md 32768 cpu
./run_device.sh data/A-raw/visits-01.json 32768 cpu
```

Each run adds a line to `results/device-runs.txt` and saves the reply in
`results/replies/`. A run that gives no result in 30 minutes is recorded
as `error=timeout`. Large contexts take up to 12 minutes on the emulator.

**8. Summarize.** Writes `results/summary.csv` and prints it as a table.
For each slice it keeps the run with the smallest context, and the
median run when there are several.

```bash
python3 summarize.py
```

**9. Draw the chart.** Writes `results/tokens-by-format.png`.

```bash
~/venvs/slm/bin/python plot.py
```

## Files

| Path | What it is |
|---|---|
| `data/A-raw/`, `data/B-pruned/`, `data/C-rows/`, `data/D-markdown/` | The 7 slices in each format |
| `data/synthea/` | Synthea's hospital and practitioner bundles, which the slices refer to |
| `views/` | Tokempic's views, with the blood pressure and coded value fix |
| `rows-template.eta` | Tokempic template that prints the view rows as CSV, for format C |
| `tokempic-node.mjs` | Runs Tokempic under Node. Tokempic's command line only starts under Bun |
| `results/tokens.csv` | Characters and tokens for each format and slice |
| `results/device-runs.txt` | Every device run, one `SlmBench` line each |
| `results/device-runs-before-bp-fix.txt` | Earlier runs, made before the views fix. Kept for reference |
| `results/summary.csv` | One row per slice: resources, tokens per format and the device run |
| `results/replies/` | What the model wrote. Only the 10 visit run so far, because saving replies was added after the other runs |
| `results/tokens-by-format.png` | The chart |

## Limits

- One synthetic patient. Real records have other shapes.
- Tokempic's views keep only lab results and vital signs. They drop
  surveys, social history and exams (69 of 413 observations here), so
  part of the saving comes from leaving data out.
- Device runs are on the emulator, on CPU. Times vary from run to run.
- Only format D and one raw JSON slice were run on the device. Formats B
  and C were only counted.
