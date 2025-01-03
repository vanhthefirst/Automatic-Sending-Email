const express = require('express');
const cors = require('cors');
const path = require('path');
const dotenv = require('dotenv');
const { createServer } = require('http');
const fs = require('fs');

// Load environment variables from both files
dotenv.config({ path: '.env.local' });
dotenv.config({ path: '.env' });

const app = express();
const port = process.env.PORT || 3000;

// Comprehensive environment configuration
const ENV_CONFIG = {
  API_KEY: process.env.NEXT_PUBLIC_API_KEY || '123',
  FRONTEND_URL: process.env.FRONTEND_URL || 'http://localhost:3000',
  BACKEND_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  NODE_ENV: process.env.NODE_ENV || 'development',
  ALLOWED_ORIGINS: [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000'
  ]
};

// Complete MIME types configuration
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
  '.otf': 'application/font-otf'
};

// Security headers middleware
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  next();
});

// Body parser middleware
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

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
  maxAge: 86400
}));

// Serve static files with proper headers
const serveStaticWithHeaders = (directory) => {
  return express.static(directory, {
    setHeaders: (res, filePath) => {
      const ext = path.extname(filePath).toLowerCase();
      if (mimeTypes[ext]) {
        res.setHeader('Content-Type', mimeTypes[ext]);
      }
      res.setHeader('Cache-Control', 'public, max-age=86400');
    }
  });
};

// Configure static file serving
app.use('/_next', express.static(path.join(__dirname, '.next'), {
  maxAge: '1y',
  immutable: true,
  setHeaders: (res, filePath) => {
    const ext = path.extname(filePath).toLowerCase();
    if (mimeTypes[ext]) {
      res.setHeader('Content-Type', mimeTypes[ext]);
    }
  }
}));

app.use(express.static(path.join(__dirname, 'public')));

// API key middleware for protected routes
app.use('/api', (req, res, next) => {
  const apiKey = req.headers['x-api-key'];
  if (!apiKey || apiKey !== ENV_CONFIG.API_KEY) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Invalid API Key'
    });
  }
  next();
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    environment: ENV_CONFIG.NODE_ENV
  });
});

// Main application route handler
app.get('*', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>CSV Upload Portal</title>
        <link rel="stylesheet" href="/_next/static/css/8d60cd91efe62344.css">
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
          }
          .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
          }
          h1 {
            color: #2d3748;
            text-align: center;
            margin-bottom: 2rem;
          }
        </style>
      </head>
      <body>
        <div id="__next">
          <div class="container">
            <h1>CSV Upload Portal</h1>
            <div id="app-root"></div>
          </div>
        </div>
        <script src="/_next/static/chunks/webpack-5be858628468b409.js"></script>
        <script src="/_next/static/chunks/main-92f7e840df16e494.js"></script>
        <script src="/_next/static/chunks/pages/_app-60989c630625b0d6.js"></script>
        <script src="/_next/static/chunks/pages/index-284b4f3d1662716c.js"></script>
      </body>
    </html>
  `);
});

// Global error handling middleware
app.use((err, req, res, next) => {
  console.error('Server error:', err);

  // Handle specific error types
  if (err.message === 'Not allowed by CORS') {
    return res.status(403).json({
      error: 'CORS Error',
      message: 'Origin not allowed'
    });
  }

  if (err.code === 'ENOENT') {
    return res.status(404).json({
      error: 'Not Found',
      message: 'The requested resource could not be found'
    });
  }

  // Default error response
  res.status(err.status || 500).json({
    error: ENV_CONFIG.NODE_ENV === 'development' ? err.message : 'Internal Server Error',
    ...(ENV_CONFIG.NODE_ENV === 'development' && { stack: err.stack })
  });
});

// Create HTTP server
const server = createServer(app);

// Graceful shutdown handler
const gracefulShutdown = () => {
  console.log('Received shutdown signal. Closing server...');
  server.close(() => {
    console.log('Server closed. Exiting process...');
    process.exit(0);
  });

  // Force close after timeout
  setTimeout(() => {
    console.error('Could not close connections in time, forcefully shutting down');
    process.exit(1);
  }, 10000);
};

// Process event handlers
process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
  gracefulShutdown();
});

process.on('unhandledRejection', (err) => {
  console.error('Unhandled Rejection:', err);
  gracefulShutdown();
});

// Start server
server.listen(port, '0.0.0.0', (err) => {
  if (err) {
    console.error('Error starting server:', err);
    process.exit(1);
  }
  console.log(`> Server running on http://0.0.0.0:${port}`);
  console.log('Environment:', ENV_CONFIG.NODE_ENV);
  console.log('Frontend URL:', ENV_CONFIG.FRONTEND_URL);
  console.log('Backend URL:', ENV_CONFIG.BACKEND_URL);
});