const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('linha do tempo seleciona a geometria da cota, inclusive com a foto ligada', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'app', 'mapa.html'), 'utf8');
  assert.match(html, /maplibre-gl@6\.17\.0/, 'motor de mapas validado no navegador');
  const code = html.match(/<script type="module">([\s\S]*?)<\/script>/)?.[1]?.replace(/^\s*import[^\n]*\n/u, '');
  assert.ok(code, 'script do mapa no HTML público');

  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      clientHeight: 600, clientWidth: 62, style: {}, dataset: {},
      setAttribute(name, value) { this[name] = String(value); },
      getAttribute(name) { return this[name]; },
      addEventListener(name, callback) { this[name] = callback; },
      fire(name, value) { this[name]({ target: value === undefined ? this : { value } }); },
    });
    return elements.get(id);
  };
  let map;
  class FakeMap {
    constructor(options) { this.options = options; this.handlers = new Map(); this.filters = new Map(); this.layouts = new Map(); this.paints = new Map(); this.water = null; map = this; }
    addControl() {}
    isStyleLoaded() { return false; }
    on(name, callback) { this.handlers.set(name, callback); }
    once(name, callback) { this.handlers.set(name, callback); }
    emit(name) { this.handlers.get(name)?.(); }
    setFilter(name, filter) { this.filters.set(name, filter); }
    getSource(name) { assert.equal(name, 'agua'); return { setData: data => { this.water = data; } }; }
    setLayoutProperty(layer, name, value) { this.layouts.set(`${layer}.${name}`, value); }
    setPaintProperty(layer, name, value) { this.paints.set(`${layer}.${name}`, value); }
    easeTo() {}
    getCanvas() { return { style: {} }; }
    resize() {}
  }
  const context = vm.createContext({
    document: { getElementById: element, body: { dataset: {} } },
    maplibregl: { Map: FakeMap, NavigationControl: class {}, Popup: class {} },
    ResizeObserver: class { observe() {} },
    location: { search: '' }, URLSearchParams, performance: { now: () => 0 },
    setInterval: () => 1, clearInterval: () => {}, console,
  });
  vm.runInContext(code, context, { timeout: 5000 });
  const serie = vm.runInContext('S', context);
  const peak = serie.findIndex(row => row.cm === 535);
  const intermediate = serie.findIndex(row => row.cm >= 500 && row.cm < 510);
  assert.ok(peak > 0 && intermediate > 0);

  const ids = map.options.style.layers.map(layer => layer.id);
  assert.ok(ids.indexOf('foto') < ids.indexOf('agua'), 'foto está sob a simulação');
  assert.ok(ids.indexOf('agua') < ids.indexOf('predios'), 'prédios 3D ficam acima da água');
  assert.ok(map.options.style.sources.eventos.data.features.every(f => f.geometry.coordinates.every(Number.isFinite)));

  map.emit('style.load');
  assert.equal(map.water.features.length, 0);
  element('hora').fire('input', intermediate);
  assert.equal(map.water.features[0].properties.cota, 500);
  element('hora').fire('input', peak);
  assert.equal(map.water.features[0].properties.cota, 535);
  assert.match(element('cota-mapa').textContent, /5,35 m/);
  assert.match(element('pessoas').textContent, /139\.179 pessoas/);
  element('bfoto').fire('click');
  element('brealce').fire('click');
  assert.equal(map.paints.get('agua.fill-opacity'), .72);
  element('brealce').fire('click');
  assert.equal(map.paints.get('agua.fill-opacity'), .48);
  element('b3d').fire('click');
  assert.equal(map.layouts.get('predios.visibility'), 'visible');
  element('hora').fire('input', 0);
  assert.equal(map.water.features.length, 0, 'a água recua ao voltar ao início');
});
