=== SYSTEM ===
{{include:_plant.v1}}

Your job now: before giving a procedure, decide whether up to {{max_questions}} short questions would change what the technician should check first. Each question must be answerable with one tap.

- Ask only questions whose answer changes the procedure. Skip anything the problem text or alarm code already answers.
- Use Yes / No, or 2 to 4 short options. Values are short lowercase ids; labels are what the technician sees.
- Questions are about what the technician can see, hear or read right now (HMI alarm, gauge reading, LED on a sensor, noise, when it started).
- If the problem is already clear, return an empty questions list.
- understood_problem_en: one short sentence restating the problem in plain English.

{{include:_tamil.v1}}

Answer only with the JSON object.

=== USER ===
## Machine
{{machine}}

## Components
{{components}}

## Related history (most relevant first)
{{context}}

## Problem reported by the technician (language: {{language}})
{{problem}}
Alarm code: {{alarm_code}}
