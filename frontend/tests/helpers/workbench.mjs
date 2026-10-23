// Minimal in-memory document for controller tests; no browser or layout simulation.
import { readFile } from 'node:fs/promises';

class Element {
  constructor(tag = 'div', id = '') {
    Object.assign(this, { tag, id, className: '', dataset: {}, children: [], events: {}, disabled: false,
      hidden: false, value: '', textContent: '', parent: null, scrollTop: 0, scrollHeight: 0 });
    this.classList = { toggle: (name, enabled) => {
      const names = new Set(this.className.split(' ').filter(Boolean));
      if (enabled) names.add(name); else names.delete(name);
      this.className = [...names].join(' ');
    } };
  }
  append(...nodes) { for (const n of nodes) { n.parent = this; this.children.push(n); } }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(n => n !== this); }
  get firstElementChild() { return this.children[0]; }
  addEventListener(name, fn) { (this.events[name] ??= []).push(fn); }
  async emit(name, event = {}) { for (const fn of this.events[name] ?? []) await fn(event); }
  querySelector(query) { return this.all().find(n => matches(n, query)) ?? null; }
  all() { return this.children.flatMap(n => [n, ...n.all()]); }
  focus() {}
  showModal() {}
}
function matches(n, selector) {
  return selector.split(',').some(q => q.startsWith('#') ? n.id === q.slice(1)
    : q.startsWith('.') ? n.className.split(' ').includes(q.slice(1))
    : q === '[data-query]' && 'query' in n.dataset);
}
function documentStub() {
  const ids = 'notice messages trace balance send input connect reset phase health mode refresh composer example new reset-dialog'.split(' ');
  const elements = Object.fromEntries(ids.map(id => [id, new Element('div', id)]));
  return { elements, getElementById: id => elements[id], createElement: tag => new Element(tag),
    querySelectorAll: q => [...new Set(Object.values(elements).flatMap(n => [n, ...n.all()]))].filter(n => matches(n, q)) };
}
let serial = 0;
export async function loadWorkbench(fetchImpl) {
  globalThis.document = documentStub(); globalThis.fetch = fetchImpl;
  let source = await readFile(new URL('../../app.mjs', import.meta.url), 'utf8');
  for (const file of ['agent-client.mjs', 'view-model.mjs']) {
    source = source.replace(`'./${file}'`, JSON.stringify(new URL('../../' + file, import.meta.url).href));
  }
  // Instrument only the in-memory test module; production exports stay unchanged.
  source += '\nexport const controller = {state, send, respond, connect, controls};';
  const module = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64') + '#' + serial++);
  await new Promise(resolve => setImmediate(resolve));
  return { app: module.controller, doc: globalThis.document };
}
