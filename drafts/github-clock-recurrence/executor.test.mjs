import fs from 'node:fs';
import assert from 'node:assert/strict';
import test from 'node:test';
const yaml=fs.readFileSync(new URL('./scheduled-sync.candidate.yml',import.meta.url),'utf8');
const program=yaml.split('// EXECUTOR_GUARD_BEGIN')[1].split('// EXECUTOR_GUARD_END')[0].split('\n').slice(1).map(x=>x.replace(/^          /,'')).join('\n');
const repository=yaml.match(/GITHUB_REPOSITORY!=='([^']+)'/)[1];
const sha='a'.repeat(40);
const env={GITHUB_REPOSITORY:repository,GITHUB_REF:'refs/heads/dev',GITHUB_WORKFLOW_REF:`${repository}/.github/workflows/scheduled-sync.yml@refs/heads/dev`,GITHUB_EVENT_NAME:'workflow_dispatch',GITHUB_SHA:sha,GITHUB_RUN_ID:'456',GITHUB_RUN_ATTEMPT:'1',CLOCK_RUN_ID:'123',EXECUTION_MODE:'scheduled',APPROVED_DEV_SHA:sha,APPROVED_INPUT_SHA:sha,SCHEDULE_ENABLED:'true'};
function guard(patch={}) {const process={env:{...env,...patch},exitCode:0};const logs=[];new Function('process','console',program)(process,{log:x=>logs.push(JSON.parse(x))});return {code:process.exitCode,logs};}
test('scheduled child approved revision',()=>assert.equal(guard().code,0));
for(const [name,patch] of [['child SHA changed',{GITHUB_SHA:'b'.repeat(40)}],['approved variable changed',{APPROVED_DEV_SHA:'b'.repeat(40)}],['missing approval',{APPROVED_DEV_SHA:''}],['input not approved',{APPROVED_INPUT_SHA:'b'.repeat(40)}],['opt-in rollback',{SCHEDULE_ENABLED:'false'}],['opt-in removed',{SCHEDULE_ENABLED:''}],['rerun',{GITHUB_RUN_ATTEMPT:'2'}],['wrong branch',{GITHUB_REF:'refs/heads/main'}],['invalid mode',{EXECUTION_MODE:'arbitrary'}],['invalid clock ID',{CLOCK_RUN_ID:'private-data'}]]) test(name,()=>assert.equal(guard(patch).code,1));
test('direct manual remains available without schedule variables',()=>assert.equal(guard({EXECUTION_MODE:'',SCHEDULE_ENABLED:'',APPROVED_DEV_SHA:'',APPROVED_INPUT_SHA:'',CLOCK_RUN_ID:''}).code,0));
test('child blocks race before secret materialization',()=>{
  const r=guard({GITHUB_SHA:'b'.repeat(40)}); assert.equal(r.code,1);
  assert.equal(r.logs[0].code,'EXECUTED_REVISION_NOT_APPROVED');
  assert(yaml.indexOf('// EXECUTOR_GUARD_BEGIN')<yaml.indexOf('actions/checkout'));
  assert(yaml.indexOf('// EXECUTOR_GUARD_BEGIN')<yaml.indexOf('secrets.'));
  assert.match(yaml,/ref: \$\{\{ github.sha \}\}/);
});
test('untrusted values and secrets are not emitted by guard',()=>{
  const r=guard({APPROVED_INPUT_SHA:'password=synthetic-private',CLOCK_RUN_ID:'token=synthetic-private'});
  assert(!JSON.stringify(r.logs).includes('synthetic-private'));
  assert(!program.includes('secrets.'));
});
