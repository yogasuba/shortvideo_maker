from database import SessionLocal, PostizIntegration
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def remove_integration():
    session = SessionLocal()
    try:
        # Check for Test122
        integrations = session.query(PostizIntegration).filter(PostizIntegration.name == 'Test122').all()
        logger.info(f"Found {len(integrations)} integrations with name 'Test122'")
        
        for integration in integrations:
            logger.info(f"Deleting integration: {integration.name} (ID: {integration.id}, Platform: {integration.platform})")
            session.delete(integration)
            
        # Also check for 'unknown' platform
        unknowns = session.query(PostizIntegration).filter(PostizIntegration.platform == 'unknown').all()
        logger.info(f"Found {len(unknowns)} integrations with platform 'unknown'")
        
        for integration in unknowns:
            logger.info(f"Deleting unknown integration: {integration.name} (ID: {integration.id})")
            session.delete(integration)
            
        session.commit()
        logger.info("Cleanup complete.")
        
    except Exception as e:
        logger.error(f"Error removing integration: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    remove_integration()
