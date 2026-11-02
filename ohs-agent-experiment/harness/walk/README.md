# Walk scripts

Helpers for scoring an app on the 10 checks in
`../../results/app-scores.md`. They need the emulator running
and, for FHIR apps, the HAPI server from `../../docker-compose.yml`.
Apps differ in layout, so you still drive the screens yourself. The
scripts handle setup, input and the timed parts.

| Script | What it does |
|---|---|
| `prep.sh <run_id>` | Fresh seeded server, clean device, installs the run's APK from `../archive/` and launches it online |
| `ui.py` | Lists what is on screen with tap coordinates |
| `input.sh` | Taps, typing, scrolling, Home, airplane mode, app restart |
| `counts.sh` | Resource counts on the server, with no caching |
| `check10.sh` | Runs check 10 end to end, see below |

## Scoring one app

The 10 checks and how to test each one with these scripts are in
`../../results/app-scores.md`. A session starts like this.

```bash
cd ohs-agent-experiment/harness/walk
./prep.sh s1-ohs-skills-claude-opus-5-5-medium-8
python3 ui.py                      # find the patient row, then tap it
./input.sh tap 720 434
```

Fill fields with `./input.sh type X Y TEXT`, using coordinates from
`ui.py`. A typical visit is weight 74, blood pressure 118/76, danger
signs None.

`check10.sh` turns on airplane mode and waits while you save a visit. It
then checks the form closed, presses Home, ends the app with `am kill`
(unlike force-stop, this keeps scheduled background work), restores the
network and watches the server for 5 minutes without reopening the app.
