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

test('Meta status distinguishes proven controlled publishing from global automation', () => {
  const {context} = dashboard();
  context.meta = {status:'PROVEN_CONTROLLED_ONLY', controlled_publish_proven:true, unattended_automation_enabled:false};
  assert.equal(
    vm.runInContext('metaStatusText(meta)', context),
    'verbunden · offizieller API-Versand bewiesen · Automatik geschützt'
  );
  context.meta = {status:'BLOCKED'};
  assert.equal(
    vm.runInContext('metaStatusText(meta)', context),
    'nicht vollständig verbunden · Einrichtung prüfen'
  );
});

test('Virality card renders secret-free QA and media-gate status', () => {
  const {context,nodes} = dashboard();
  context.factory = {
    trend_briefs: 1,
    patterns: 2,
    by_status: {QA_READY: 1},
    latest_project: {topic: '<b>Original Short</b>', persona_slug: 'leona-voss', status: 'QA_READY'},
    media_jobs: [{status: 'AWAITING_COST_CONFIRMATION'}],
    external_actions: 0,
  };
  vm.runInContext('renderShortFactory(factory)', context);
  const html = nodes.get('#short-factory-status').innerHTML;
  assert.match(html, /Shorts QA-ready/);
  assert.match(html, /AWAITING_COST_CONFIRMATION/);
  assert.match(html, /externe Aktionen 0/);
  assert.doesNotMatch(html, /<b>Original Short<\/b>/);
});

test('Instagram DM P1 view exposes Messages & Sales truth and guarded actions', () => {
  const source = readFileSync(join(__dirname, '../dashboard/engagement.js'), 'utf8');
  assert.match(source, /\/api\/instagram-dm/);
  assert.match(source, /INSTAGRAM · MESSAGES & SALES/);
  assert.match(source, /Owner Reviews/);
  assert.match(source, /Open Payments/);
  assert.match(source, /Confirmed DM Revenue/);
  assert.match(source, /expected_open_amount/);
  assert.match(source, /confirmed_revenue/);
  assert.match(source, /data-action="approve"/);
  assert.match(source, /data-action="reconcile"/);
  assert.doesNotMatch(source, /\/api\/instagram-dm\/send/);
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
