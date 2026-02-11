# Gunicorn Configuration for IP Checker Pro
# =========================================

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('FLASK_PORT', '5000')}"
backlog = 2048

# Worker processes
workers = int(os.environ.get('WEB_CONCURRENCY', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.environ.get('WORKER_CLASS', 'gevent')
worker_connections = int(os.environ.get('WORKER_CONNECTIONS', '1000'))
timeout = int(os.environ.get('TIMEOUT', '30'))
keepalive = int(os.environ.get('KEEPALIVE', '5'))
graceful_timeout = int(os.environ.get('GRACEFUL_TIMEOUT', '30'))

# Restart workers after N requests (helps prevent memory leaks)
max_requests = int(os.environ.get('MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.environ.get('MAX_REQUESTS_JITTER', '100'))

# Logging
accesslog = '-'  # stdout
errorlog = '-'   # stderr
loglevel = os.environ.get('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'ip-checker-pro'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance tuning
preload_app = True
reuse_port = True

# SSL (if needed)
# keyfile = '/path/to/key.pem'
# certfile = '/path/to/cert.pem'

# Custom headers
forwarded_allow_ips = '*'
secure_scheme_headers = {
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-FOR': 'FORWARDED',
    'X-REAL-IP': 'REMOTE_ADDR',
}

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process")

def post_worker_init(worker):
    """Called just after a worker is initialized."""
    worker.log.info("Worker initialized")