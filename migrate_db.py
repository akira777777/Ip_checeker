#!/usr/bin/env python3
"""
Database migration script for IP Checker application.
Creates required tables and indexes for PostgreSQL database.
"""

import os
import sys
from sqlalchemy import create_engine, text

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable not set")
    print("Example: export DATABASE_URL='postgresql://user:password@localhost/ipchecker'")
    sys.exit(1)

def create_tables(engine):
    """Create all required database tables."""
    with engine.connect() as conn:
        # Create geolocations table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS geolocations (
                id SERIAL PRIMARY KEY,
                ip_address VARCHAR(45) UNIQUE NOT NULL,
                city VARCHAR(100),
                region VARCHAR(100),
                country VARCHAR(100),
                country_code VARCHAR(10),
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                timezone VARCHAR(50),
                isp VARCHAR(200),
                asn VARCHAR(50),
                org VARCHAR(200),
                status VARCHAR(20) DEFAULT 'success',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                lookup_count INTEGER DEFAULT 1
            )
        """))
        
        # Create ip_lookup_history table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ip_lookup_history (
                id SERIAL PRIMARY KEY,
                ip_address VARCHAR(45) NOT NULL,
                user_agent TEXT,
                client_ip VARCHAR(45),
                endpoint VARCHAR(50),
                success BOOLEAN DEFAULT TRUE,
                response_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        
        # Create security_scan_results table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS security_scan_results (
                id SERIAL PRIMARY KEY,
                scan_timestamp TIMESTAMP DEFAULT NOW(),
                total_connections INTEGER,
                security_score INTEGER,
                grade VARCHAR(20),
                threats_count INTEGER DEFAULT 0,
                warnings_count INTEGER DEFAULT 0,
                secure_connections INTEGER DEFAULT 0,
                suspicious_ports INTEGER DEFAULT 0,
                geo_failures INTEGER DEFAULT 0,
                top_countries TEXT,
                findings_summary TEXT,
                recommendations TEXT
            )
        """))
        
        # Create whois_records table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS whois_records (
                id SERIAL PRIMARY KEY,
                ip_address VARCHAR(45) UNIQUE NOT NULL,
                domain VARCHAR(255),
                registrar VARCHAR(200),
                creation_date TIMESTAMP,
                expiration_date TIMESTAMP,
                name_servers TEXT,
                status_raw TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                lookup_count INTEGER DEFAULT 1
            )
        """))
        
        conn.commit()
        print("Tables created successfully!")

def create_indexes(engine):
    """Create indexes for better query performance."""
    with engine.connect() as conn:
        # Geolocation indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_geolocation_ip ON geolocations(ip_address)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_geolocation_country ON geolocations(country)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_geolocation_created ON geolocations(created_at)"))
        
        # Lookup history indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_lookup_history_ip ON ip_lookup_history(ip_address)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_lookup_history_client ON ip_lookup_history(client_ip)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_lookup_history_date ON ip_lookup_history(created_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_lookup_history_endpoint ON ip_lookup_history(endpoint)"))
        
        # Security scan indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_security_scan_timestamp ON security_scan_results(scan_timestamp)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_security_scan_grade ON security_scan_results(grade)"))
        
        # WHOIS indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_whois_ip ON whois_records(ip_address)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_whois_domain ON whois_records(domain)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_whois_registrar ON whois_records(registrar)"))
        
        conn.commit()
        print("Indexes created successfully!")

def main():
    """Main migration function."""
    print("Starting database migration...")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT version()"))
            version = conn.execute(text("SELECT version()")).fetchone()
            print(f"Connected to: {version[0]}")
        
        # Create tables and indexes
        create_tables(engine)
        create_indexes(engine)
        
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()