import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import { createApiRouter } from './routes/api.js';
import { NestingService } from './services/nestingService.js';
import { FirebaseService } from './services/firebaseService.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = process.env.PORT || 5001;

// Config file resolution helper
function getConfigFileCandidates() {
  return [
    path.join(__dirname, 'local_config.json'),
    path.join(__dirname, '..', 'local_config.json'),
    path.join(__dirname, '..', '..', 'local_config.json')
  ];
}

function getConfigFilePath() {
  for (const p of getConfigFileCandidates()) {
    if (fs.existsSync(p)) return p;
  }
  return path.join(__dirname, 'local_config.json');
}

function resolveValidPath(rawPath, defaultRelative) {
  if (!rawPath) rawPath = defaultRelative;
  if (path.isAbsolute(rawPath) && fs.existsSync(rawPath)) {
    return path.resolve(rawPath);
  }

  const backendDir = __dirname;
  const nestingDir = path.resolve(__dirname, '..');
  const workspaceDir = path.resolve(__dirname, '..', '..');

  const candidates = [
    path.resolve(rawPath),
    path.resolve(backendDir, rawPath),
    path.resolve(nestingDir, rawPath),
    path.resolve(workspaceDir, rawPath),
    path.resolve(backendDir, defaultRelative),
    path.resolve(nestingDir, defaultRelative),
    path.resolve(workspaceDir, defaultRelative)
  ];

  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return path.resolve(nestingDir, defaultRelative);
}

function loadConfig() {
  const cfgPath = getConfigFilePath();
  const defaultConfig = {
    anhlocal_dir: resolveValidPath('ANHLOCAL', 'ANHLOCAL'),
    output_dir: resolveValidPath('output', 'output'),
    custom_nesting: {
      paper_size: 'Custom (390x290mm)',
      width_mm: 390.0,
      height_mm: 290.0,
      dpi: 300,
      padding_mm: 3.0,
      margin_top_mm: 0.0,
      margin_bottom_mm: 0.0,
      margin_left_mm: 0.0,
      margin_right_mm: 0.0,
      rotation_angles_deg: [0, 90, 180, 270],
      auto_scale_oversized: false
    },
    pet_nesting: {
      paper_size: 'PET Roll (580x1000mm)',
      width_mm: 580.0,
      height_mm: 1000.0,
      dpi: 300,
      padding_mm: 5.0,
      margin_top_mm: 0.0,
      margin_bottom_mm: 0.0,
      margin_left_mm: 0.0,
      margin_right_mm: 0.0,
      rotation_angles_deg: [0, 90, 180, 270],
      auto_scale_oversized: false
    },
    firebase: {
      projectId: 'order-web-hoang',
      apiKey: 'AIzaSyC1SK8dB0FSz00EkeXErBdgp-SOeUj-HCU',
      auto_listen: true
    }
  };

  if (!fs.existsSync(cfgPath)) {
    saveConfig(defaultConfig);
    return defaultConfig;
  }

  try {
    const raw = fs.readFileSync(cfgPath, 'utf-8');
    const parsed = JSON.parse(raw);
    parsed.anhlocal_dir = resolveValidPath(parsed.anhlocal_dir, 'ANHLOCAL');
    parsed.output_dir = resolveValidPath(parsed.output_dir, 'output');
    return parsed;
  } catch (e) {
    console.error('[Config] Error loading config, using default:', e);
    return defaultConfig;
  }
}

function saveConfig(configData) {
  try {
    const cfgPath = getConfigFilePath();
    fs.writeFileSync(cfgPath, JSON.stringify(configData, null, 2), 'utf-8');
    // Also mirror to root NESTING/local_config.json if in backend
    const rootCfg = path.join(__dirname, '..', 'local_config.json');
    if (cfgPath !== rootCfg) {
      try {
        fs.writeFileSync(rootCfg, JSON.stringify(configData, null, 2), 'utf-8');
      } catch (e) {}
    }
    return true;
  } catch (e) {
    console.error('[Config] Error saving config:', e);
    return false;
  }
}

const app = express();

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Services
const nestingService = new NestingService(loadConfig);
const firebaseService = new FirebaseService(loadConfig);

// Mount API Router
const apiRouter = createApiRouter({ loadConfig, saveConfig, nestingService, firebaseService });
app.use('/api', apiRouter);

// Ensure folders exist
const initialCfg = loadConfig();
fs.mkdirSync(initialCfg.output_dir, { recursive: true });
fs.mkdirSync(initialCfg.anhlocal_dir, { recursive: true });

// Start Firebase listener
firebaseService.startListener(async (jobData) => {
  return await nestingService.runJob(jobData);
});

// Start Server
app.listen(PORT, '0.0.0.0', () => {
  console.log('====================================================');
  console.log(`🚀 NESTING BACKEND NODE.JS SERVER RUNNING!`);
  console.log(`📡 Backend API: http://localhost:${PORT}`);
  console.log(`📂 Output Directory: ${initialCfg.output_dir}`);
  console.log(`🖼️ ANHLOCAL Directory: ${initialCfg.anhlocal_dir}`);
  console.log('====================================================');
});
