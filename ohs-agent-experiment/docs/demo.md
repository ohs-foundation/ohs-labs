# ANC PoC — Demo Video Runbook

One video, all four scenarios, ~7 minutes final cut. Recorded as five
separate takes (state resets between scenarios), stitched with title cards.
Every take doubles as an eval scenario run — record the eval, get the demo.

## Final cut structure

| # | Segment | Source footage | Cut length |
|---|---|---|---|
| 0 | Title card: "One prompt. Two apps. Four questions." | still | 5s |
| 1 | **Build it** — time-lapse of the agent building the OHS app from an empty project | ~30 min screen recording, sped up ~20× with 4 real-time slowdowns | ~90s |
| 2 | **Change it** — edit Questionnaire on server → reopen app → new field. Then the cold build's diff for the same request | real-time recording | ~90s |
| 3 | **Connect it** — one server query → district CSV opens. Then the cold build's hand-built exporter | real-time | ~60s |
| 4 | **Trust it** — bad record POSTed to HAPI → rejected with OperationOutcome; same record into cold app's SQLite → accepted silently → poisoned district report | real-time | ~2 min |
| 5 | Closing card: the headline table (+ model-matrix chart when data exists) | still | 15s |

Real-time slowdown moments in segment 1 (caption each):
1. The one prompt being pasted.
2. The form rendering itself from the server's Questionnaire.
3. An error → self-correction exchange (server or compiler).
4. The final server query showing standard FHIR resources.

## Screen layout (identical in every take)

Terminal (Claude Code / curl) left, emulator right, browser with HAPI
behind — QuickTime full-screen capture, Do Not Disturb on, font size up.

## Recording order (≠ playback order, because of state)

**Take T (Trust it / scenario 4)** — record FIRST, needs today's state:
current build B app + HAPI seeded, current build A app installed.
- `curl -X POST` the malformed visit (systolic −40, danger sign
  `"sever-headache"`) → OperationOutcome on screen.
- adb: insert the same row into build A's SQLite; open the app — accepted.
- Run the scenario 3 report against build A's pulled DB → bad row in CSV.

**Take C3 (Connect it)** — same state:
- OHS side: the district-report query against HAPI → CSV opens.
- Cold side: screen-record the S3 eval session's key moments (the agent
  building the exporter), or capture stills from its transcript.

**Take C2 (Change it)** — needs Questionnaire WITHOUT fetal heart rate:
- Verify `anc-contact` has no FHR field (reset HAPI + reseed if needed).
- OHS side: agent (or curl) adds the FHR item to the server Questionnaire,
  reopen app, field appears. This is also the S2-build-B eval run.
- Cold side: record the S2-build-A eval session; in the cut, show its
  diff stat + the rebuild/reinstall step.

**Take B (Build it)** — record LAST, needs pristine state:
- Fresh scaffold from build B baseline (`e414d2f`) in a new dir, HAPI
  reset + reseed, app uninstalled from emulator.
- Start QuickTime, paste `build-b-prompt.md`, auto-accept, hands off
  ~30 min. This is also an extra scenario-1 data point — archive it as
  `runs/s1-ohs-fable-02/` (transcript, run.json, code.diff, recording).

**Cards** — title + closing stills (HTML/PNG, generated).

## Edit pipeline

1. Trim each take (QuickTime or ffmpeg).
2. Speed up take B: `ffmpeg -i takeB.mov -vf "setpts=PTS/20" -an takeB-fast.mp4`,
   then splice the 4 real-time moments back at 1×.
3. Concat with cards: ffmpeg concat demuxer, one `list.txt`.
4. Captions: burn in per-segment title cards rather than subtitles —
   less editing, reads better at speed.
5. Target: ≤ 8 min, 1080p+, audio optional (captions carry it; add a
   voiceover later only if the blog post needs it).

## State cheat sheet

- Reset HAPI: `cd ohs-agent-experiment && docker-compose down && docker-compose up -d && ./load-seed.sh`
- Bad-record POST and adb insert one-liners: prepare in `demo-assets/`
  before recording day.
- Fallback rule: keep every raw take — any segment can be re-cut without
  re-recording the others.
