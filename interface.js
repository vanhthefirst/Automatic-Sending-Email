const express = require('express');
const cors = require('cors');
const path = require('path');
const dotenv = require('dotenv');
const { createServer } = require('http');
const fs = require('fs');

// Load environment variables
dotenv.config({ path: '.env.local' });
dotenv.config({ path: '.env' });

const app = express();
const port = process.env.PORT || 3000;

// Environment configuration
const ENV_CONFIG = {
  API_KEY: process.env.NEXT_PUBLIC_API_KEY || '123',
  FRONTEND_URL: process.env.FRONTEND_URL || 'http://localhost:3000',
  BACKEND_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  SMTP_SERVER: process.env.SMTP_SERVER || 'e2ksmtp01.e2k.ad.ge.com',
  SMTP_SENDER: process.env.SMTP_SENDER || '223144086@geaerospace.com',
  ADMIN_EMAIL: process.env.ADMIN_EMAIL || '223144086@geaerospace.com',
  TEAM_EMAIL: process.env.TEAM_EMAIL || 'team@example.com',
  ALLOWED_ORIGINS: [
    process.env.FRONTEND_URL || 'http://localhost:3000',
    'http://172.24.29.224:3000',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000'
  ]
};

// MIME types for static file serving
const mimeTypes = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'application/font-woff',
  '.woff2': 'application/font-woff2',
  '.ttf': 'application/font-ttf',
  '.eot': 'application/vnd.ms-fontobject',
  '.otf': 'application/font-otf',
  '.wasm': 'application/wasm'
};

// Express middleware setup
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// CORS configuration
app.use(cors({
  origin: (origin, callback) => {
    if (!origin || ENV_CONFIG.ALLOWED_ORIGINS.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key'],
  maxAge: 86400,
}));

// Static file serving middleware with security headers
const serveStaticWithHeaders = (directory) => {
  return express.static(directory, {
    maxAge: '1d',
    setHeaders: (res, filePath) => {
      const ext = path.extname(filePath).toLowerCase();
      if (mimeTypes[ext]) {
        res.setHeader('Content-Type', mimeTypes[ext]);
      }
      // Security headers
      res.setHeader('X-Content-Type-Options', 'nosniff');
      res.setHeader('X-Frame-Options', 'SAMEORIGIN');
      res.setHeader('X-XSS-Protection', '1; mode=block');
    }
  });
};

// Serve static files from out directory (Next.js static export)
app.use(serveStaticWithHeaders(path.join(__dirname, 'out')));

// Serve static files from public directory
app.use(serveStaticWithHeaders(path.join(__dirname, 'public')));

// API key middleware for /api routes
app.use('/api', (req, res, next) => {
  const apiKey = req.headers['x-api-key'];
  if (!apiKey || apiKey !== ENV_CONFIG.API_KEY) {
    return res.status(401).json({
      error: 'Invalid API Key',
      message: 'Please provide a valid API key'
    });
  }
  next();
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    env: process.env.NODE_ENV
  });
});

// Handle all routes - serve index.html for client-side routing
app.get('*', (req, res, next) => {
  try {
    const indexPath = path.join(__dirname, 'out', 'index.html');
    if (fs.existsSync(indexPath)) {
      res.setHeader('Content-Type', 'text/html');
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
      res.sendFile(indexPath);
    } else {
      // If index.html doesn't exist, send a basic HTML response
      const htmlResponse = `
        <!DOCTYPE html>
        <html>
          <head>
            <title>CSV Upload Portal</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
              body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
              .container { max-width: 800px; margin: 0 auto; text-align: center; }
              h1 { color: #333; }
              p { color: #666; }
            </style>
          </head>
          <body>
            <div class="container">
              <h1>CSV Upload Portal</h1>
              <p>Please ensure the application is properly built before running.</p>
            </div>
          </body>
        </html>
      `;
      res.setHeader('Content-Type', 'text/html');
      res.send(htmlResponse);
    }
  } catch (error) {
    console.error('Error serving page:', error);
    next(error);
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  
  // Handle CORS errors
  if (err.message === 'Not allowed by CORS') {
    return res.status(403).json({
      error: 'CORS Error',
      message: 'Origin not allowed'
    });
  }

  // Handle file not found errors
  if (err.code === 'ENOENT') {
    return res.status(404).json({
      error: 'Not Found',
      message: 'The requested resource could not be found'
    });
  }

  // Handle other errors
  res.status(err.status || 500).json({
    error: process.env.NODE_ENV === 'development' ? err.message : 'Internal Server Error'
  });
});

// Create HTTP server
const server = createServer(app);

// Start server
server.listen(port, '0.0.0.0', (err) => {
  if (err) {
    console.error('Error starting server:', err);
    process.exit(1);
  }
  console.log(`> Server running on http://0.0.0.0:${port}`);
  console.log('Environment:', process.env.NODE_ENV);
  console.log('Frontend URL:', ENV_CONFIG.FRONTEND_URL);
  console.log('Backend URL:', ENV_CONFIG.BACKEND_URL);
});

// Handle process errors
process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
  setTimeout(() => process.exit(1), 1000);
});

process.on('unhandledRejection', (err) => {
  console.error('Unhandled Rejection:', err);
  setTimeout(() => process.exit(1), 1000);
});