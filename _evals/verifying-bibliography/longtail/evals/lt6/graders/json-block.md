---
type: regex
pattern: "```json[\\s\\S]*\"flagged\""
target: last_message
---
Format check only. Recall and false positives are scored by score.py against gold.json.
