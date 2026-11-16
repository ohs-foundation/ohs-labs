// Runs Tokempic under Node through tsx. Tokempic's CLI only starts under Bun,
// so this calls its exported run() and prints the result.
//   TOKEMPIC_DIR=~/AndroidStudioProjects/tokempic tsx tokempic-node.mjs --patient <id> --server <url> [--template <file>]
const { run } = await import(process.env.TOKEMPIC_DIR + "/src/cli.ts");
const { markdown } = await run(process.argv.slice(2));
process.stdout.write(markdown + "\n");
