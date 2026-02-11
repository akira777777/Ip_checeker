"""
Database models for IP Checker application.
Defines tables for geolocation data, IP lookup history, and security scans.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class GeoLocation(Base):
    """Store geolocation data for IP addresses."""
    __tablename__ = 'geolocations'
    
    id = Column(Integer, primary_key=True)
    ip_address = Column(String(45), nullable=False, unique=True)  # Support IPv6
    city = Column(String(100))
    region = Column(String(100))
    country = Column(String(100))
    country_code = Column(String(10))
    latitude = Column(Float)
    longitude = Column(Float)
    timezone = Column(String(50))
    isp = Column(String(200))
    asn = Column(String(50))
    org = Column(String(200))
    status = Column(String(20), default='success')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    lookup_count = Column(Integer, default=1)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_geolocation_ip', 'ip_address'),
        Index('idx_geolocation_country', 'country'),
        Index('idx_geolocation_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<GeoLocation(ip='{self.ip_address}', country='{self.country}')>"


class IPLookupHistory(Base):
    """Track IP lookup requests and their results."""
    __tablename__ = 'ip_lookup_history'
    
    id = Column(Integer, primary_key=True)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(Text)
    client_ip = Column(String(45))  # Client's real IP
    endpoint = Column(String(50))   # Which API endpoint was called
    success = Column(Boolean, default=True)
    response_time_ms = Column(Integer)  # API response time
    created_at = Column(DateTime, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_lookup_history_ip', 'ip_address'),
        Index('idx_lookup_history_client', 'client_ip'),
        Index('idx_lookup_history_date', 'created_at'),
        Index('idx_lookup_history_endpoint', 'endpoint'),
    )
    
    def __repr__(self):
        return f"<IPLookupHistory(ip='{self.ip_address}', endpoint='{self.endpoint}')>"


class SecurityScanResult(Base):
    """Store security scan results for analysis and trending."""
    __tablename__ = 'security_scan_results'
    
    id = Column(Integer, primary_key=True)
    scan_timestamp = Column(DateTime, default=func.now())
    total_connections = Column(Integer)
    security_score = Column(Integer)
    grade = Column(String(20))
    threats_count = Column(Integer, default=0)
    warnings_count = Column(Integer, default=0)
    secure_connections = Column(Integer, default=0)
    suspicious_ports = Column(Integer, default=0)
    geo_failures = Column(Integer, default=0)
    top_countries = Column(Text)  # JSON string of country distribution
    findings_summary = Column(Text)  # JSON string of security findings
    recommendations = Column(Text)   # JSON string of recommendations
    
    # Indexes
    __table_args__ = (
        Index('idx_security_scan_timestamp', 'scan_timestamp'),
        Index('idx_security_scan_grade', 'grade'),
    )
    
    def __repr__(self):
        return f"<SecurityScanResult(score={self.security_score}, grade='{self.grade}')>"


class WHOISRecord(Base):
    """Cache WHOIS lookup results."""
    __tablename__ = 'whois_records'
    
    id = Column(Integer, primary_key=True)
    ip_address = Column(String(45), nullable=False, unique=True)
    domain = Column(String(255))
    registrar = Column(String(200))
    creation_date = Column(DateTime)
    expiration_date = Column(DateTime)
    name_servers = Column(Text)  # JSON array
    status_raw = Column(Text)    # Raw WHOIS status
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    lookup_count = Column(Integer, default=1)
    
    # Indexes
    __table_args__ = (
        Index('idx_whois_ip', 'ip_address'),
        Index('idx_whois_domain', 'domain'),
        Index('idx_whois_registrar', 'registrar'),
    )
    
    def __repr__(self):
        return f"<WHOISRecord(ip='{self.ip_address}', domain='{self.domain}')>"


# Database utility functions
def init_db(engine):
    """Initialize database tables."""
    Base.metadata.create_all(engine)


def get_db_session(engine):
    """Create a database session."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    return Session()