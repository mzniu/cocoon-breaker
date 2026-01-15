"""
In-memory log buffer for real-time log streaming to frontend
"""
import logging
from collections import deque
from datetime import datetime
from typing import List, Dict


class LogBuffer(logging.Handler):
    """Custom logging handler that stores logs in memory"""
    
    def __init__(self, maxlen: int = 100):
        super().__init__()
        self.buffer = deque(maxlen=maxlen)
        self.formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
    
    def emit(self, record):
        """Add log record to buffer"""
        try:
            msg = self.format(record)
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
            
            # Map log level to frontend level
            level_map = {
                'DEBUG': 'info',
                'INFO': 'info',
                'WARNING': 'warning',
                'ERROR': 'error',
                'CRITICAL': 'error'
            }
            
            self.buffer.append({
                'timestamp': timestamp,
                'level': level_map.get(record.levelname, 'info'),
                'message': f"[{record.name}] {record.getMessage()}"
            })
        except Exception:
            self.handleError(record)
    
    def get_logs(self, count: int = 50) -> List[Dict]:
        """Get recent logs"""
        return list(self.buffer)[-count:]
    
    def clear(self):
        """Clear buffer"""
        self.buffer.clear()


# Global log buffer instance
_log_buffer = None


def get_log_buffer() -> LogBuffer:
    """Get global log buffer instance"""
    global _log_buffer
    if _log_buffer is None:
        _log_buffer = LogBuffer(maxlen=200)
    return _log_buffer


def setup_log_buffer():
    """Setup log buffer and attach to root logger"""
    buffer = get_log_buffer()
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(buffer)
    
    return buffer
