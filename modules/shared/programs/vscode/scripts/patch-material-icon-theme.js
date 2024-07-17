const fs = require("fs");

const [_node, _script, argument] = process.argv;

const parse = (content) => {
  const cleaned = content.toString().replaceAll(/\/\/.*/g, "");
  console.log(cleaned);
  return JSON.parse(cleaned);
};

const vscodeConfig = parse(fs.readFileSync(argument));
const extensionConfig = parse(fs.readFileSync("./dist/material-icons.json"));

// vscode settings.json "material-icon-theme.*"
const options = Object.fromEntries(
  Object.entries(vscodeConfig)
    .filter(([key, _]) => key.startsWith("material-icon-theme."))
    .map(([key, value]) => [key.replace("material-icon-theme.", ""), value])
);

// extension material-icons.json
const data = {
  ...extensionConfig,
  fileExtensions: { ...extensionConfig.fileExtensions, gotmpl: "template" },
  options,
  hidesExplorerArrows: options.hidesExplorerArrows,
};

fs.writeFileSync("./dist/material-icons.json", JSON.stringify(data, null, 2));
