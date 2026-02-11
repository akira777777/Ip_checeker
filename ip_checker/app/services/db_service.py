"""
Database service for PostgreSQL integration.
Handles connection pooling, CRUD operations, and migration support.
"""

import os
import json
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    GeoLocation, IPLookupHistory, SecurityScanResult, WHOISRecord,
    init_db, get_db_session
)

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost/ipchecker')
DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 10))
DB_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', 20))
DB_POOL_TIMEOUT = int(os.environ.get('DB_POOL_TIMEOUT', 30))
DB_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', 3600))

# Cache TTL settings
GEO_CACHE_TTL = int(os.environ.get('GEO_CACHE_TTL', 3600))  # 1 hour default
WHOIS_CACHE_TTL = int(os.environ.get('WHOIS_CACHE_TTL', 86400))  # 24 hours default


class DatabaseService:
    """PostgreSQL database service with connection pooling and caching."""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine with connection pooling."""
        try:
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=DB_POOL_SIZE,
                max_overflow=DB_MAX_OVERFLOW,
                pool_timeout=DB_POOL_TIMEOUT,
                pool_recycle=DB_POOL_RECYCLE,
                pool_pre_ping=True,  # Verify connections before use
                echo=False  # Set to True for SQL debugging
            )
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established successfully")
            
            # Initialize tables
            init_db(self.engine)
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions with automatic cleanup."""
        session = get_db_session(self.engine)
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def health_check(self) -> Dict[str, Any]:
        """Check database connectivity and status."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()")).fetchone()
                db_version = result[0] if result else "Unknown"
                
                # Get table counts
                counts = {}
                tables = ['geolocations', 'ip_lookup_history', 'security_scan_results', 'whois_records']
                for table in tables:
                    try:
                        count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                        counts[table] = count_result[0] if count_result else 0
                    except:
                        counts[table] = 0
                
                return {
                    "status": "healthy",
                    "database_version": db_version,
                    "tables": counts,
                    "pool_status": {
                        "size": self.engine.pool.size(),
                        "checkedout": self.engine.pool.checkedout(),
                        "overflow": self.engine.pool.overflow()
                    }
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    # Geolocation methods
    def get_geolocation(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get geolocation data from database cache."""
        try:
            with self.get_session() as session:
                geo_record = session.query(GeoLocation).filter_by(ip_address=ip_address).first()
                if geo_record:
                    # Check if record is expired
                    if geo_record.updated_at and \
                       datetime.utcnow() - geo_record.updated_at > timedelta(seconds=GEO_CACHE_TTL):
                        return None
                    
                    return {
                        "ip": geo_record.ip_address,
                        "city": geo_record.city,
                        "region": geo_record.region,
                        "country": geo_record.country,
                        "country_code": geo_record.country_code,
                        "lat": geo_record.latitude,
                        "lon": geo_record.longitude,
                        "timezone": geo_record.timezone,
                        "isp": geo_record.isp,
                        "asn": geo_record.asn,
                        "org": geo_record.org,
                        "status": geo_record.status,
                        "cached": True
                    }
        except Exception as e:
            logger.warning(f"Failed to get geolocation from DB: {e}")
        return None
    
    def save_geolocation(self, ip_address: str, geo_data: Dict[str, Any]) -> bool:
        """Save geolocation data to database."""
        try:
            with self.get_session() as session:
                # Check if record exists
                existing = session.query(GeoLocation).filter_by(ip_address=ip_address).first()
                
                if existing:
                    # Update existing record
                    existing.city = geo_data.get('city')
                    existing.region = geo_data.get('region')
                    existing.country = geo_data.get('country')
                    existing.country_code = geo_data.get('country_code')
                    existing.latitude = geo_data.get('lat')
                    existing.longitude = geo_data.get('lon')
                    existing.timezone = geo_data.get('timezone')
                    existing.isp = geo_data.get('isp')
                    existing.asn = geo_data.get('asn')
                    existing.org = geo_data.get('org')
                    existing.status = geo_data.get('status', 'success')
                    existing.lookup_count += 1
                else:
                    # Create new record
                    new_record = GeoLocation(
                        ip_address=ip_address,
                        city=geo_data.get('city'),
                        region=geo_data.get('region'),
                        country=geo_data.get('country'),
                        country_code=geo_data.get('country_code'),
                        latitude=geo_data.get('lat'),
                        longitude=geo_data.get('lon'),
                        timezone=geo_data.get('timezone'),
                        isp=geo_data.get('isp'),
                        asn=geo_data.get('asn'),
                        org=geo_data.get('org'),
                        status=geo_data.get('status', 'success')
                    )
                    session.add(new_record)
                
                return True
        except Exception as e:
            logger.error(f"Failed to save geolocation: {e}")
            return False
    
    # WHOIS methods
    def get_whois_record(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get WHOIS data from database cache."""
        try:
            with self.get_session() as session:
                whois_record = session.query(WHOISRecord).filter_by(ip_address=ip_address).first()
                if whois_record:
                    # Check if record is expired
                    if whois_record.updated_at and \
                       datetime.utcnow() - whois_record.updated_at > timedelta(seconds=WHOIS_CACHE_TTL):
                        return None
                    
                    return {
                        "status": "success",
                        "domain": whois_record.domain,
                        "registrar": whois_record.registrar,
                        "creation_date": whois_record.creation_date.isoformat() if whois_record.creation_date else None,
                        "expiration_date": whois_record.expiration_date.isoformat() if whois_record.expiration_date else None,
                        "name_servers": json.loads(whois_record.name_servers) if whois_record.name_servers else None,
                        "status_raw": json.loads(whois_record.status_raw) if whois_record.status_raw else None,
                        "cached": True
                    }
        except Exception as e:
            logger.warning(f"Failed to get WHOIS from DB: {e}")
        return None
    
    def save_whois_record(self, ip_address: str, whois_data: Dict[str, Any]) -> bool:
        """Save WHOIS data to database."""
        try:
            with self.get_session() as session:
                # Check if record exists
                existing = session.query(WHOISRecord).filter_by(ip_address=ip_address).first()
                
                if existing:
                    # Update existing record
                    existing.domain = whois_data.get('domain')
                    existing.registrar = whois_data.get('registrar')
                    existing.creation_date = whois_data.get('creation_date')
                    existing.expiration_date = whois_data.get('expiration_date')
                    existing.name_servers = json.dumps(whois_data.get('name_servers')) if whois_data.get('name_servers') else None
                    existing.status_raw = json.dumps(whois_data.get('status_raw')) if whois_data.get('status_raw') else None
                    existing.lookup_count += 1
                else:
                    # Create new record
                    new_record = WHOISRecord(
                        ip_address=ip_address,
                        domain=whois_data.get('domain'),
                        registrar=whois_data.get('registrar'),
                        creation_date=whois_data.get('creation_date'),
                        expiration_date=whois_data.get('expiration_date'),
                        name_servers=json.dumps(whois_data.get('name_servers')) if whois_data.get('name_servers') else None,
                        status_raw=json.dumps(whois_data.get('status_raw')) if whois_data.get('status_raw') else None
                    )
                    session.add(new_record)
                
                return True
        except Exception as e:
            logger.error(f"Failed to save WHOIS record: {e}")
            return False
    
    # Lookup history
    def log_lookup(self, ip_address: str, endpoint: str, success: bool = True, 
                   response_time: int = None, client_ip: str = None, user_agent: str = None) -> bool:
        """Log IP lookup request for analytics."""
        try:
            with self.get_session() as session:
                history = IPLookupHistory(
                    ip_address=ip_address,
                    endpoint=endpoint,
                    success=success,
                    response_time_ms=response_time,
                    client_ip=client_ip,
                    user_agent=user_agent
                )
                session.add(history)
                return True
        except Exception as e:
            logger.warning(f"Failed to log lookup: {e}")
            return False
    
    # Security scan results
    def save_security_scan(self, scan_data: Dict[str, Any]) -> bool:
        """Save security scan results to database."""
        try:
            with self.get_session() as session:
                scan_result = SecurityScanResult(
                    total_connections=scan_data.get('total_connections', 0),
                    security_score=scan_data.get('security_score', 0),
                    grade=scan_data.get('grade', 'Unknown'),
                    threats_count=scan_data.get('threats', 0),
                    warnings_count=scan_data.get('warnings', 0),
                    secure_connections=scan_data.get('secure', 0),
                    suspicious_ports=scan_data.get('suspicious_ports', 0),
                    geo_failures=scan_data.get('geo_failures', 0),
                    top_countries=json.dumps(scan_data.get('top_countries', [])),
                    findings_summary=json.dumps(scan_data.get('findings', [])),
                    recommendations=json.dumps(scan_data.get('recommendations', []))
                )
                session.add(scan_result)
                return True
        except Exception as e:
            logger.error(f"Failed to save security scan: {e}")
            return False
    
    def get_recent_scans(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent security scan results."""
        try:
            with self.get_session() as session:
                scans = session.query(SecurityScanResult)\
                              .order_by(SecurityScanResult.scan_timestamp.desc())\
                              .limit(limit)\
                              .all()
                
                return [{
                    'id': scan.id,
                    'timestamp': scan.scan_timestamp.isoformat(),
                    'score': scan.security_score,
                    'grade': scan.grade,
                    'total_connections': scan.total_connections,
                    'threats': scan.threats_count,
                    'warnings': scan.warnings_count
                } for scan in scans]
        except Exception as e:
            logger.error(f"Failed to get recent scans: {e}")
            return []


# Global database service instance
db_service = None


def get_db_service() -> DatabaseService:
    """Get singleton database service instance."""
    global db_service
    if db_service is None:
        db_service = DatabaseService()
    return db_service


def init_database_service(database_url: str = None) -> DatabaseService:
    """Initialize and return database service."""
    global db_service
    db_service = DatabaseService(database_url)
    return db_service