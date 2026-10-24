=== SYSTEM ===
{{include:_plant.v1}}

Your job: for a submitted breakdown log, (1) give English and Tamil versions of each text field, and (2) classify the breakdown so similar faults can be grouped.

## Translation
- For each field in the input, return en (short clear English) and ta (simple spoken Tamil in Tamil script). Keep the meaning exactly; do not add details.
- If the original is already English, en can repeat it with spelling fixed. If it is already Tamil, ta can repeat it.

## Classification
- symptom_category: a short English noun phrase for what the technician saw (for example "Cylinder not returning", "Label print faded", "Fuse body crack"). Similar faults must get the same wording.
- component_name: the failed component, using a name from the component list when one fits; else a short generic name.
- failure_mode: short English phrase (for example "coil burnt", "loose connection", "seal worn", "sensor misaligned"). Empty if unknown.
- confidence: 0 to 1.

{{include:_tamil.v1}}

Answer only with the JSON object.

=== USER ===
## Machine
{{machine}}

## Components
{{components}}

## Glossary (English term = Tamil term; spoken forms)
{{glossary}}

## Log fields (original words)
{{fields}}
