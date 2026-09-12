import { readFileSync, writeFileSync } from 'node:fs';
const path = new URL('../web/src/contracts.ts', import.meta.url);
const source = readFileSync(path, 'utf8');
writeFileSync(path, source.slice(source.indexOf('export interface')));
