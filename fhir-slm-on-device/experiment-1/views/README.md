# Views

Tokempic's built-in ViewDefinitions, with one fix in `vitals.json` and `labs.json`.
Tokempic reads only `valueQuantity`, so blood pressure (two components, systolic and
diastolic) and coded results (such as "Not detected") came out empty. The `value` column now
gives `systolic/diastolic` for blood pressure and the coded display for coded results.
