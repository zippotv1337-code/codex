const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');

function dashboard() {
  const nodes = new Map();
  const context = vm.createContext({document:{querySelector(key) {
    if (!nodes.has(key)) nodes.set(key, {innerHTML:''});
    return nodes.get(key);
  }, querySelectorAll(){return [];}}});
  const source = readFileSync(join(__dirname, '../dashboard/app.js'), 'utf8');
  vm.runInContext(source.slice(0, source.indexOf('cardsRoot.addEventListener')), context);
  return {context, nodes};
}
test('old story reserves remain visible with correct deep link', () => {
  const {context,nodes} = dashboard();
  context.items = [{content_id:6,date:'2026-09-01',creator_slug:'mara-field',display_name:'Mara',series:'Küchenfenster',status:'PAUSED',frames:[]}];
  vm.runInContext('renderStoryOps(items)', context);
  assert.match(nodes.get('#story-ops').innerHTML, /Küchenfenster/);
  assert.match(nodes.get('#story-ops').innerHTML, /\/stories#story-6/);
  assert.match(nodes.get('#story-ops').innerHTML, /NO PREVIEW ASSET/);
});
test('Needs Attention escapes metadata and shows safe preview or explicit fallback', () => {
  const {context} = dashboard();
  context.card = {content_id:2,creator_slug:'mara-field',series:'<script>bad</script>',status:'BLOCKED',visibility_scope:'PUBLIC_SFW',assets:[]};
  let html = vm.runInContext('attentionTemplate(card)', context);
  assert.match(html, /NO PREVIEW ASSET/);
  assert.doesNotMatch(html, /<script>/);
  context.card.assets = [{preview_url:'/api/assets/2/preview',excluded:false}];
  html = vm.runInContext('attentionTemplate(card)', context);
  assert.match(html, /<img src="\/api\/assets\/2\/preview"/);
  assert.match(html, /data-large-preview="2"/);
  context.card.privacy_blur = true;
  assert.doesNotMatch(vm.runInContext('attentionTemplate(card)', context), /<img /);
});

for (const ready of [false, true]) {
  test(`story editor ${ready ? 'accepts current backend' : 'blocks writes until old backend restarts'}`, async () => {
    const buttons = [{disabled:false}];
    const nodes = new Map();
    let requests = 0;
    const context = vm.createContext({document:{querySelector(key) {
      if (!nodes.has(key)) nodes.set(key, {innerHTML:'', textContent:'', querySelectorAll(){return buttons;}});
      return nodes.get(key);
    }}, fetch:async () => {
      requests++;
      return {ok:true,json:async()=>({items:[], ...(ready ? {review_schema:'story-review-v1'} : {})})};
    }});
    const source = readFileSync(join(__dirname, '../dashboard/stories.js'), 'utf8');
    vm.runInContext(source.slice(0, source.indexOf("root.addEventListener('click'")), context);
    await vm.runInContext('loadStories()', context);
    assert.equal(buttons[0].disabled, !ready);
    if (!ready) {
      assert.match(nodes.get('#story-notice').textContent, /Server-Neustart erforderlich/);
      await assert.rejects(vm.runInContext("save(3, 'approve')", context), /neu starten/);
      assert.equal(requests, 1, 'old server must not receive any write');
    }
  });
}
