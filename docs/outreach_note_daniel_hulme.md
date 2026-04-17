# Outreach Note Drafts for Dr. Daniel Hulme

## Short Version (DM / LinkedIn)

Hi Dr. Hulme, I wanted to share a small concept I have been building called Fenrir. It is an early local tool for evaluating pressure-sensitive risk patterns in model behavior, using a hybrid of static anchors and adaptive pressure ladders rather than broad alignment claims. The readout is deterministic and heuristic-first, with an optional LLM-friendly export for usability. It is not production-complete, but I thought the framing might be relevant to your safety-first alignment work at Conscium.

## Longer Version (Email / Follow-Up)

Hi Dr. Hulme,

I have been building an early evaluation tool called Fenrir and wanted to share the concept in case it is useful context for your work.

The core question behind it is how to measure alignment-relevant behavior empirically, rather than asserting it from high-level benchmarks. The current MVP uses a hybrid structure: a small static anchor slice for comparability, plus adaptive pressure ladders that escalate conditions and track where behavior shifts.

Fenrir currently produces deterministic heuristic readouts (condition deltas, threshold/failure-mode summaries, stress effects, uncertainty/caveats) and keeps claims tightly bounded. There is also an optional LLM-native export for convenience, but the canonical output remains the heuristic report.

This is still an installable concept and not a production claim. I am sharing it as a practical framing for pressure-sensitive behavioral evaluation, which seemed potentially relevant to your alignment and safety-first focus at Conscium.
