import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const text = path => readFileSync(new URL(path,import.meta.url),'utf8').replace(/\r\n/g,'\n');
const block = (s,a,b) => s.split(a)[1]?.split(b)[0];
test('actual main clock uses the tested program and only the proposed hourly trigger',()=>{
 const actual=text('../../../sheets-supabase-sync-main-preparation/.github/workflows/staging-clock.yml');
 const candidate=text('./staging-clock.candidate.yml');
 assert.equal(block(actual,'// CLOCK_PROGRAM_BEGIN','// CLOCK_PROGRAM_END'),block(candidate,'// CLOCK_PROGRAM_BEGIN','// CLOCK_PROGRAM_END'));
 assert.match(actual,/cron: '17 \* \* \* \*'/);
 assert.match(actual,/workflow_dispatch:/);
 assert.match(actual,/group: staging-clock\s+cancel-in-progress: false/);
 assert.doesNotMatch(actual.replace(/#.*$/gm,''),/secrets\.|environment:|\buses:/);
});
test('actual dev executor retains the tested adapter and guard precedes secrets',()=>{
 const actual=text('../../.github/workflows/scheduled-sync.yml');
 const candidate=text('./scheduled-sync.candidate.yml');
 assert.equal(block(actual,'# EXECUTOR_SUMMARY_BEGIN','# EXECUTOR_SUMMARY_END'),block(candidate,'# EXECUTOR_SUMMARY_BEGIN','# EXECUTOR_SUMMARY_END'));
 assert.match(actual,/dispatch:\s+needs: preflight/);
 assert(actual.indexOf('EXECUTOR_GUARD_BEGIN') < actual.indexOf('actions/checkout'));
 assert(actual.indexOf('EXECUTOR_GUARD_BEGIN') < actual.indexOf('secrets.'));
 assert(actual.indexOf('Verify checkout revision') < actual.indexOf('secrets.'));
 assert.match(actual,/ref: \$\{\{ github.sha \}\}/);
 assert.match(actual,/Validate staging guard/);
});
