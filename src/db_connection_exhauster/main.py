import time
import psycopg2
import logging
import sys
import os
from openfeature import api
from openfeature.client import OpenFeatureClient
from openfeature.contrib.provider.flagd import FlagdProvider

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    def __init__(self, max_connections: int = 100):
        """
        Initialize the connection manager
        
        Args:
            max_connections: Maximum number of connections to create
        """
        # Initialize database config from environment variables
        self.db_config = {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'database': os.environ.get('DB_NAME', 'postgres'),
            'user': os.environ.get('DB_USER', 'postgres'),
            'password': os.environ.get('DB_PASSWORD', ''),
            'port': int(os.environ.get('DB_PORT', 5432))
        }
        
        self.max_connections = max_connections
        self.connections = []
        self.is_started = False

    def create_connection(self) -> bool:
        """
        Create a single database connection with retry logic
        Returns True if connection created successfully, False otherwise
        """
        max_retries = 3
        backoff_time = 1  # Start with 1 second
        
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(**self.db_config)
                conn.set_session(autocommit=True)
                self.connections.append(conn)
                logger.info(f"Connection {len(self.connections)} established successfully")
                return True
                
            except Exception as e:
                
                if "remaining connection slots" in str(e).lower():
                    
                    # Connection exhaustion - backoff and retry
                    if attempt < max_retries - 1:
                        logger.debug(f"Connection exhausted, retrying in {backoff_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(backoff_time)
                        backoff_time = min(backoff_time * 3, 5)  # Exponential backoff, max 5s
                    else:
                        logger.debug("Max retries reached for connection creation")
                        return False
               
                else:
                    # Other error - log and fail immediately
                    logger.error(f"Failed to create connection: {e}")
                    return False

        return False
    
    def start(self):
        """Start creating connections"""
        if self.is_started:
            logger.debug("Manager already started")
            return
        
        logger.info(f"Starting connection manager - attempting to create {self.max_connections} connections")
        self.is_started = True
        self.connections = []
        
        for _ in range(self.max_connections):
            if not self.create_connection():
                # If we can't create more connections, stop trying
                logger.info(f"Stopped creating connections at {len(self.connections)}/{self.max_connections} due to connection limits")
                break
            
            # Wait 200 milliseconds between connection attempts
            time.sleep(0.2)
        
        logger.info(f"Connection creation completed. Active connections: {len(self.connections)}")
    
    def stop(self):
        """Stop and close all connections"""
        if not self.is_started:
            logger.debug("Manager already stopped")
            return
        
        logger.info("Stopping connection manager - closing all connections")
        
        for i, conn in enumerate(self.connections):
            try:
                conn.close()
                logger.debug(f"Connection {i + 1} closed")
            except Exception as e:
                logger.error(f"Error closing connection {i + 1}: {e}")
        
        self.connections = []
        self.is_started = False
        logger.info("All connections closed")
    
    def get_connection_count(self) -> int:
        """Get the current number of active connections"""
        return len(self.connections)


def setup_openfeature() -> OpenFeatureClient:
    """Setup OpenFeature provider and return client"""
    try:
        flagd_host = os.environ.get('FLAGD_HOST', 'flagd')
        flagd_port = int(os.environ.get('FLAGD_PORT', 8013))
        api.set_provider(FlagdProvider(host=flagd_host, port=flagd_port))
        client = api.get_client()
        logger.info(f"OpenFeature initialized with flagd at {flagd_host}:{flagd_port}")
        return client
    except Exception as e:
        sys.exit(f"Failed to initialize OpenFeature: {e}")


def check_feature_flag(client: OpenFeatureClient, flag_name: str) -> int:
    """Check the feature flag value"""
    if not client:
        logger.warning("OpenFeature client not initialized, defaulting to False")
        return False
    
    try:
        return client.get_integer_value(flag_name, 0)
    except Exception as e:
        logger.error(f"Error checking feature flag '{flag_name}': {e}")
        return False
    

def main():

    flag_name = "kafkaQueueProblems"

    # Check required environment variables
    required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Setup OpenFeature client
    openfeature_client = setup_openfeature()
    
    # Create connection manager
    manager = DatabaseConnectionManager()
    
    logger.info("Starting feature flag monitoring...")
    logger.info(f"Database: {manager.db_config['host']}:{manager.db_config['port']}/{manager.db_config['database']}")
    logger.info(f"Monitoring flag: kafkaQueueProblems")
    
    try:
        
        while True:
        
            flag_value = check_feature_flag(openfeature_client, flag_name)
            
            if flag_value > 0:
                
                # Flag is set - start manager if not already started
                if not manager.is_started:
                    logger.info("Feature flag enabled - starting connections")
                    manager.start()
                else:
                    # Already started, just sleep and check again
                    logger.debug(f"Feature enabled, manager running with {manager.get_connection_count()} connections")
                
            else:
                
                # Flag is unset - stop manager if running
                if manager.is_started:
                    logger.info("Feature flag disabled - stopping connections")
                    manager.stop()
                else:
                    # Already stopped, just sleep and check again
                    logger.debug("Feature disabled, manager stopped")
            
            time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")

    finally:
        logger.info("Shutting down...")
        manager.stop()


if __name__ == "__main__":
    main()
