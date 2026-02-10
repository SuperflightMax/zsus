const fs = require("fs");
const path = require("path");

const rootDir = path.resolve(__dirname, "..", "..");
const instancesDir = path.join(rootDir, "instances");

function loadInstances() {
  if (!fs.existsSync(instancesDir)) {
    return [];
  }

  return fs
    .readdirSync(instancesDir)
    .filter((entry) => {
      const fullPath = path.join(instancesDir, entry);
      return fs.statSync(fullPath).isDirectory();
    })
    .map((entry) => {
      const instancePath = path.join(instancesDir, entry);
      const logsDir = path.join(instancePath, "logs");

      return {
        name: `zsus-${entry}`,
        cwd: instancePath,
        script: "bash",
        args: [
          "-lc",
          "set -a; source .env; set +a; ./.venv/bin/python -m src.interfaces.http.server"
        ],
        out_file: path.join(logsDir, "pm2.out.log"),
        error_file: path.join(logsDir, "pm2.err.log"),
        autorestart: true,
      };
    });
}

module.exports = {
  apps: loadInstances(),
};
