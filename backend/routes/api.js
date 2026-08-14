import express from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export function createApiRouter({ loadConfig, saveConfig, nestingService, firebaseService }) {
  const router = express.Router();

  // 1. GET /api/config
  router.get('/config', (req, res) => {
    try {
      const cfg = loadConfig();
      res.json(cfg);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // 2. POST /api/save_config
  router.post('/save_config', (req, res) => {
    try {
      const newConfig = req.body;
      const success = saveConfig(newConfig);
      res.json({ success });
    } catch (err) {
      res.status(400).json({ success: false, error: err.message });
    }
  });

  // 3. GET /api/history
  router.get('/history', (req, res) => {
    try {
      const cfg = loadConfig();
      const outputDir = cfg.output_dir || 'output';

      if (!fs.existsSync(outputDir)) {
        return res.json([]);
      }

      const entries = fs.readdirSync(outputDir);
      const folders = [];

      for (const entry of entries) {
        const fullPath = path.join(outputDir, entry);
        try {
          const stat = fs.statSync(fullPath);
          if (stat.isDirectory()) {
            const files = fs.readdirSync(fullPath);
            const pngs = files.filter(f => f.toLowerCase().endsWith('.png'));

            // Check if job_summary.json exists
            let summary = null;
            const summaryPath = path.join(fullPath, 'job_summary.json');
            if (fs.existsSync(summaryPath)) {
              try {
                summary = JSON.parse(fs.readFileSync(summaryPath, 'utf-8'));
              } catch (e) {}
            }

            folders.push({
              name: entry,
              path: fullPath,
              created_at: stat.birthtime || stat.mtime,
              file_count: files.length,
              png_count: pngs.length,
              png_files: pngs,
              summary: summary
            });
          }
        } catch (e) {}
      }

      // Sort newest first
      folders.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      res.json(folders);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // 4. GET /api/history/:folder/files
  router.get('/history/:folder/files', (req, res) => {
    try {
      const cfg = loadConfig();
      const outputDir = cfg.output_dir || 'output';
      const folderPath = path.join(outputDir, req.params.folder);

      if (!fs.existsSync(folderPath)) {
        return res.status(404).json({ error: 'Folder not found' });
      }

      const files = fs.readdirSync(folderPath);
      res.json({ folder: req.params.folder, files });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // 5. GET /api/output/:folder/:filename (Serve image preview)
  router.get('/output/:folder/:filename', (req, res) => {
    try {
      const cfg = loadConfig();
      const outputDir = cfg.output_dir || 'output';
      const filePath = path.join(outputDir, req.params.folder, req.params.filename);

      if (!fs.existsSync(filePath)) {
        return res.status(404).send('File Not Found');
      }

      res.sendFile(filePath);
    } catch (err) {
      res.status(500).send(err.message);
    }
  });

  // 6. POST /api/process_job
  router.post('/process_job', async (req, res) => {
    try {
      const jobData = req.body;
      console.log(`[API] Processing Job request: ${jobData.id || 'N/A'}`);

      const result = await nestingService.runJob(jobData);

      // Trigger Firebase Firestore updates if applicable
      if (result.status === 'completed' && jobData.id) {
        await firebaseService.updateJobCompleted(jobData.id, result.relative_folder);
        if (jobData.order_id) {
          await firebaseService.updateOrderPrintCompleted(jobData.order_id);
        }
      }

      res.json(result);
    } catch (err) {
      console.error(`[API] Job execution error:`, err);
      res.status(500).json({ status: 'error', message: err.message });
    }
  });

  // 7. GET /api/logs
  router.get('/logs', (req, res) => {
    res.json({ logs: nestingService.getLogs() });
  });

  // 8. GET /api/health
  router.get('/health', (req, res) => {
    res.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      firebase_listening: firebaseService.isListening
    });
  });

  return router;
}
