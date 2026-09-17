# Comparison copy style guide

Distilled from LightSprint's own site (lightsprint.ai) so the agent's drafts sound
like something the growth team actually wrote, not generic AI copy.

## Voice
- Confident and forward-looking, not defensive or dismissive of competitors.
- Never disparage a competitor or claim it is bad. Every comparison acknowledges
  what the other tool is genuinely good at first.
- Frame LightSprint as complementary, not a replacement: it runs Claude, Codex,
  and other agents *inside* a shared, governed workflow rather than competing
  with them model-for-model.
- Recurring themes to reach for when true: shared/multiplayer sessions,
  codebase-aware planning, non-engineers and engineers working together,
  "engineers control merge" / approval workflows, no vendor lock-in on models.

## Shape
- Each entry has exactly two fields: `stronger_for` (one sentence, lowercase
  start, no trailing period, describing who the competitor genuinely serves
  best) and `lightsprint_better_for` (one sentence, same shape, describing the
  team/situation where LightSprint is the better fit).
- Keep sentences short fragments, not full marketing paragraphs — match the
  existing entries in data/comparisons.json exactly in tone and length.
- Do not invent features, pricing, or claims that aren't evidenced in the
  fetched source text. If the detected change doesn't actually warrant new
  copy, say so and leave the existing copy unchanged.
