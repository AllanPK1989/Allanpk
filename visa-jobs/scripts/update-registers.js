// Download/refresh the official sponsor registers and re-read manual imports.
//   npm run update-registers            all registers
//   npm run update-registers -- gb ca   only some
import { loadConfig } from '../server/config.js';
import { Registers } from '../server/registers.js';

const config = loadConfig();
const registers = new Registers(config.dataDir);
await registers.load();
const ids = process.argv.slice(2).filter((a) => /^[a-z]{2}$/.test(a));
const results = await registers.update({ ids: ids.length ? ids : null, log: (m) => console.log(m) });
const failed = results.filter((r) => !r.ok);
console.log(failed.length ? `\n${failed.length} register(s) failed; the others were updated.` : '\nAll registers updated.');
process.exitCode = failed.length ? 1 : 0;
