module.exports = {
    apps: [
      {
        name: 'fastapi-app',
        script: 'uvicorn',
        args: '-m uvicorn main:app --host 0.0.0.0 --port 8000',
        cwd: './backend',
        watch: true,
        env: {
          NODE_ENV: 'production',
        },
        autorestart: true,
        max_memory_restart: '1G'
      },
      {
        name: 'nextjs-app',
        script: 'npm',
        args: 'run dev',
        cwd: '../src',
        watch: true,
        env: {
          NODE_ENV: 'development',
        }
      }
    ]
  };