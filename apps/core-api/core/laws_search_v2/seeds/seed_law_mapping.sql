-- Law KB / Mapping seed data (AML + sanctions examples)
-- Run after migrations:
--   psql "$LAWS_V2_DATABASE_URL" -f laws_search_v2/seeds/seed_law_mapping.sql

INSERT INTO control_objectives (control_id, name, description, expected_artifacts, jurisdiction_scope, created_at)
VALUES
  ('CTRL_SAR_FILE', 'SAR Filing', 'File suspicious activity reports when required.', ARRAY['SAR filing', 'case narrative'], 'federal', NOW()),
  ('CTRL_STRUCTURING_MONITOR', 'Structuring Monitoring', 'Detect and escalate potential structuring.', ARRAY['alert logs', 'investigation notes'], 'both', NOW()),
  ('CTRL_OFAC_SCREEN', 'OFAC Screening', 'Screen customers and counterparties against OFAC lists.', ARRAY['screening logs', 'hit disposition notes'], 'both', NOW())
ON CONFLICT (control_id) DO UPDATE
SET name = EXCLUDED.name,
    description = EXCLUDED.description,
    expected_artifacts = EXCLUDED.expected_artifacts,
    jurisdiction_scope = EXCLUDED.jurisdiction_scope;

INSERT INTO typologies (typology_id, name, signals_definition, default_control_ids, created_at)
VALUES
  ('TYPO_STRUCTURING', 'Structuring', '{"signals": ["cash deposits below reporting threshold", "rapid sequential deposits"]}'::jsonb, ARRAY['CTRL_STRUCTURING_MONITOR', 'CTRL_SAR_FILE'], NOW()),
  ('TYPO_OFAC_NAME_MATCH', 'OFAC Name Match', '{"signals": ["sanctions name similarity", "blocked-party match"]}'::jsonb, ARRAY['CTRL_OFAC_SCREEN'], NOW())
ON CONFLICT (typology_id) DO UPDATE
SET name = EXCLUDED.name,
    signals_definition = EXCLUDED.signals_definition,
    default_control_ids = EXCLUDED.default_control_ids;

INSERT INTO rule_to_typology_map (
  id, bank_id, rule_triggered, typology_id, control_ids, confidence, version, owner, created_at
)
VALUES
  ('11111111-1111-4111-8111-111111111111', 'bank_demo', 'RULE_STRUCTURING_001', 'TYPO_STRUCTURING', ARRAY['CTRL_STRUCTURING_MONITOR', 'CTRL_SAR_FILE'], 0.95, '2026-02-08', 'seed', NOW()),
  ('22222222-2222-4222-8222-222222222222', 'bank_demo', 'RULE_OFAC_NAME_MATCH', 'TYPO_OFAC_NAME_MATCH', ARRAY['CTRL_OFAC_SCREEN'], 0.97, '2026-02-08', 'seed', NOW())
ON CONFLICT (bank_id, rule_triggered, version) DO UPDATE
SET typology_id = EXCLUDED.typology_id,
    control_ids = EXCLUDED.control_ids,
    confidence = EXCLUDED.confidence,
    owner = EXCLUDED.owner;

-- Placeholder mappings (update via seed_law_mapping.py after obligation extraction creates IDs)
INSERT INTO control_to_obligation_map (id, control_id, obligation_ids, jurisdiction_filter, priority, created_at)
VALUES
  ('33333333-3333-4333-8333-333333333333', 'CTRL_SAR_FILE', ARRAY[]::uuid[], 'federal', 10, NOW()),
  ('44444444-4444-4444-8444-444444444444', 'CTRL_STRUCTURING_MONITOR', ARRAY[]::uuid[], 'both', 8, NOW()),
  ('55555555-5555-4555-8555-555555555555', 'CTRL_OFAC_SCREEN', ARRAY[]::uuid[], 'both', 10, NOW())
ON CONFLICT (id) DO NOTHING;
