// Inspect a local JSON array supplied on stdin. Never echo input or error text.
import {parseEvidence} from './evidence.mjs';
let data='', size=0, oversized=false;
for await (const chunk of process.stdin) {
  size += chunk.length;
  if (size > 5 * 1024 * 1024) { oversized=true; continue; }
  data += chunk.toString('utf8');
}
const result=oversized ? {error:'INPUT_TOO_LARGE',observations:[],last_valid_at:null} : parseEvidence(data);
console.log(JSON.stringify(result));
if (result.error || !result.observations.length || result.observations.some(x=>!['SUCCESS','NO_CHANGES','NO_DUE'].includes(x.state))) process.exitCode=1;
