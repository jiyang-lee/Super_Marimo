const sharp = require('C:/Users/flfkr/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
(async () => {
for (const width of [320, 480]) await sharp('src/assets/marimo.png').resize({width, kernel:'nearest'}).webp({lossless:true, effort:6}).toFile(`src/demo/marimo-${width}.webp`);
})();
