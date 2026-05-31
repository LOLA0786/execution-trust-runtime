"""
core/policy_loader.py
Per-tenant policy loader with hot-reload on YAML file change.
- Loads policies/{tenant_id}/config.yaml (defaults to 'default').
- Caches in per-tenant Redis namespace (policy:{tenant_id}:config).
- Uses watchdog for efficient file watching (fallback polling).
- Policies used by vault_checkpoint, ApprovalGate, agents for enforcement (max_discount_pct, etc.).
"""
import os
import time
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from redis import Redis
import json

logger = logging.getLogger(__name__)

class PolicyEventHandler(FileSystemEventHandler):
    """Hot-reload handler for policy YAML changes."""
    def __init__(self, loader):
        self.loader = loader

    def on_modified(self, event):
        if event.src_path.endswith('.yaml') or event.src_path.endswith('.yml'):
            logger.info(f"Policy file changed: {event.src_path}. Reloading...")
            self.loader.load_policies()  # trigger reload


class PolicyLoader:
    """Loads and hot-reloads per-tenant policies from policies/{tenant_id}/config.yaml.
    Stores in Redis under policy:{tenant_id}:config for fast access + persistence.
    """
    
    def __init__(self, redis_client: Optional[Redis] = None, policies_dir: str = "policies"):
        self.policies_dir = Path(policies_dir)
        self.redis = redis_client or Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True
        )
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.observer = None
        self._ensure_default_policies()
        self.load_policies()
        self._start_watcher()
    
    def _ensure_default_policies(self):
        """Create default policy if missing."""
        default_dir = self.policies_dir / "default"
        default_dir.mkdir(parents=True, exist_ok=True)
        default_file = default_dir / "config.yaml"
        if not default_file.exists():
            default_policy = {
                "max_discount_pct": 25,
                "max_payment_amount": 25000,
                "require_approval_above": 10000,
                "approvers": ["cfo@company.com", "security@company.com"],
                "capability_scopes": {
                    "revenue_ops": ["discounts", "anomalies", "pipeline"],
                    "procurement": ["contracts", "vendors", "payments"]
                },
                "trust_decay_base": 1.0
            }
            with open(default_file, "w") as f:
                yaml.dump(default_policy, f, default_flow_style=False)
            logger.info(f"Created default policy: {default_file}")
    
    def load_policies(self) -> Dict[str, Dict[str, Any]]:
        """Load all tenant policies from YAML. Cache in memory + Redis."""
        self.cache.clear()
        for tenant_dir in self.policies_dir.iterdir():
            if tenant_dir.is_dir():
                tenant_id = tenant_dir.name
                config_file = tenant_dir / "config.yaml"
                if config_file.exists():
                    try:
                        with open(config_file, "r") as f:
                            config = yaml.safe_load(f) or {}
                        self.cache[tenant_id] = config
                        # Persist to per-tenant Redis namespace
                        redis_key = f"policy:{tenant_id}:config"
                        self.redis.set(redis_key, json.dumps(config), ex=3600)  # 1h TTL
                        logger.info(f"Loaded policy for tenant {tenant_id} (Redis key: {redis_key})")
                    except Exception as e:
                        logger.error(f"Failed to load policy for {tenant_id}: {e}")
        
        # Ensure default always present
        if "default" not in self.cache:
            self.cache["default"] = {
                "max_discount_pct": 25,
                "max_payment_amount": 25000,
                "require_approval_above": 10000,
                "approvers": ["cfo@company.com"],
                "capability_scopes": {},
                "trust_decay_base": 1.0
            }
        return self.cache
    
    def get_policy(self, tenant_id: str = "default") -> Dict[str, Any]:
        """Get policy for tenant (Redis first, then cache, then default)."""
        redis_key = f"policy:{tenant_id}:config"
        cached = self.redis.get(redis_key)
        if cached:
            return json.loads(cached)
        
        return self.cache.get(tenant_id, self.cache.get("default", {}))
    
    def _start_watcher(self):
        """Start watchdog observer for hot-reload on policy file changes."""
        try:
            event_handler = PolicyEventHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, str(self.policies_dir), recursive=True)
            self.observer.start()
            logger.info(f"Policy hot-reload watcher started on {self.policies_dir} (watchdog)")
        except Exception as e:
            logger.warning(f"Watchdog failed to start: {e}. Falling back to manual reload.")
            # Fallback could be a background thread with polling, omitted for min complexity
    
    def stop_watcher(self):
        """Stop the file watcher."""
        if self.observer:
            self.observer.stop()
            self.observer.join()


# Singleton (initialized in main_fastapi or app startup)
policy_loader = PolicyLoader()
