#!/usr/bin/env node
/**
 * PHASE 4 Runtime Verification (Fast Version)
 * Tests pages that don't require slow /answer endpoint
 */

const BASE_URL = 'http://127.0.0.1:8000';
const API_KEY = 'dev-key';

const headers = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY,
};

let passed = 0;
let failed = 0;

async function test(name, fn) {
  try {
    await fn();
    passed++;
    console.log(`✓ ${name}`);
    return true;
  } catch (err) {
    failed++;
    console.log(`✗ ${name}: ${err.message}`);
    return false;
  }
}

async function main() {
  console.log('\n=== PHASE 4: RUNTIME VERIFICATION (FAST) ===\n');

  // Test Dashboard
  await test('Dashboard API calls', async () => {
    const docs = await fetch(`${BASE_URL}/documents`, { headers }).then(r => r.json());
    const diag = await fetch(`${BASE_URL}/diagnostics`, { headers }).then(r => r.json());

    if (!docs.total_documents || !Array.isArray(docs.documents)) throw new Error('DocumentsResponse invalid');
    if (!diag.build || !diag.providers) throw new Error('DiagnosticsResponse invalid');
  });

  // Test Regulations page
  await test('Regulations page', async () => {
    const docs = await fetch(`${BASE_URL}/documents`, { headers }).then(r => r.json());
    if (!docs.total_documents) throw new Error('DocumentsResponse invalid');
    if (docs.documents.some(d => !d.document_id || !d.filename || d.chunk_count === undefined)) {
      throw new Error('DocumentSummary fields missing');
    }
  });

  // Test Health page
  await test('Health page', async () => {
    const health = await fetch(`${BASE_URL}/health`, { headers }).then(r => r.json());
    const readiness = await fetch(`${BASE_URL}/health/ready`, { headers }).then(r => r.json());
    const liveness = await fetch(`${BASE_URL}/health/live`, { headers }).then(r => r.json());

    if (typeof health.status !== 'string') throw new Error('health.status invalid');
    if (!readiness.checks) throw new Error('readiness.checks invalid');
    if (liveness.status !== 'alive') throw new Error('liveness.status invalid');
  });

  // Test Audit page
  await test('Audit page', async () => {
    const events = await fetch(`${BASE_URL}/audit/events?limit=5`, { headers }).then(r => r.json());
    if (!Array.isArray(events.events)) throw new Error('AuditEventsResponse.events invalid');
    if (typeof events.total !== 'number') throw new Error('AuditEventsResponse.total invalid');
  });

  // Test Admin page
  await test('Admin page', async () => {
    const diag = await fetch(`${BASE_URL}/diagnostics`, { headers }).then(r => r.json());
    if (!diag.build || !diag.providers || !Array.isArray(diag.readiness)) throw new Error('DiagnosticsResponse invalid');
    if (!diag.metrics) throw new Error('metrics missing');
  });

  // Test Citation types (skip full /answer but check key properties)
  await test('Citation type contract', async () => {
    const answer = await fetch(`${BASE_URL}/answer`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ question: 'q', top_k: 1 }),
    }).then(r => r.json());

    if (!Array.isArray(answer.structured_citations)) throw new Error('structured_citations not array');

    const c = answer.structured_citations[0];
    if (!c) return; // Empty results okay

    // CRITICAL: Verify page is number|null (was string before fix)
    if (c.page !== null && typeof c.page !== 'number') {
      throw new Error(`page type wrong: ${typeof c.page}, expected number|null`);
    }

    // Check authority is NOT in the response (removed because backend doesn't send it)
    // This is okay - backend excludes None values

    // Verify other critical fields
    if (typeof c.citation_id !== 'string') throw new Error('citation_id not string');
    if (typeof c.document_id !== 'string') throw new Error('document_id not string');
    if (typeof c.confidence !== 'number') throw new Error('confidence not number');
  });

  // Verify /metrics endpoint is removed (doesn't exist)
  await test('Removed /metrics endpoint', async () => {
    const response = await fetch(`${BASE_URL}/metrics`, { headers });
    // Should NOT be 200 - either 404 or auth error is expected
    if (response.status === 200) throw new Error('/metrics should not return 200');
  });

  console.log(`\n✓ Passed: ${passed}`);
  console.log(`✗ Failed: ${failed}`);
  console.log(`Total: ${passed + failed}`);

  if (failed > 0) {
    console.log('\n⚠️  SOME TESTS FAILED');
    process.exit(1);
  } else {
    console.log('\n✅ ALL TESTS PASSED');
    process.exit(0);
  }
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
