from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-process IP throttling. Use a shared Redis storage backend when running
# multiple API workers or replicas in production.
limiter = Limiter(key_func=get_remote_address, default_limits=[])
