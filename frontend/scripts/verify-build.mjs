import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const indexPage = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8')
const fallbackPage = await readFile(new URL('../dist/404.html', import.meta.url), 'utf8')

assert.equal(
  fallbackPage,
  indexPage,
  'The GitHub Pages 404 document must match index.html for SPA deep links.',
)
assert.match(indexPage, /<div id="root"><\/div>/)

console.log('Build smoke checks passed.')
