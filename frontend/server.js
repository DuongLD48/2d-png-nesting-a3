import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { createProxyMiddleware } from 'http-proxy-middleware';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = process.env.PORT || 3001;
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:5001';

const app = express();

app.use(cors());

// Proxy /api requests to Backend Server without stripping /api
app.use(
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    pathFilter: '/api'
  })
);

// Serve static assets from public/
app.use(express.static(path.join(__dirname, 'public')));

// SPA fallback for non-API routes
app.get('*', (req, res) => {
  if (req.path.startsWith('/api')) {
    return res.status(404).json({ error: 'API route not found' });
  }
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log('====================================================');
  console.log(`🎨 NESTING FRONTEND WEB SERVER RUNNING!`);
  console.log(`🌐 Frontend Dashboard: http://localhost:${PORT}`);
  console.log(`🔗 Proxying /api -> ${BACKEND_URL}`);
  console.log('====================================================');
});
