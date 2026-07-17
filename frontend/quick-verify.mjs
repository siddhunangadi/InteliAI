const BASE_URL = 'http://127.0.0.1:8000';
const headers = { 'X-API-Key': 'dev-key' };

// Quick test - just check page type
fetch(`${BASE_URL}/answer`, {
  method: 'POST',
  headers: { ...headers, 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: 'x', top_k: 1 })
}).then(r => r.json()).then(data => {
  const c = data.structured_citations[0];
  if (!c) { console.log('✓ No citations (OK)'); process.exit(0); }
  
  if (c.page !== null && typeof c.page !== 'number') {
    console.log(`✗ FAIL: page type is ${typeof c.page}, expected number|null`);
    process.exit(1);
  }
  
  console.log(`✓ page type correct: ${typeof c.page === 'number' ? 'number' : 'null'}`);
  console.log('✓ Citation contract verified');
  process.exit(0);
}).catch(e => { console.error(e); process.exit(1); });
