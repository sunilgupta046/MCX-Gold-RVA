import pytest
from app.database import init_db, SessionLocal
from app.services.ingestion import seed_contracts, generate_synthetic_demo_bhavcopy
from app.models.bhavcopy import BhavcopyRecord

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Ensure database schema and contract specifications are initialized
    before any integration or API tests run on a fresh repository clone.
    """
    init_db()
    db = SessionLocal()
    try:
        seed_contracts(db)
        if db.query(BhavcopyRecord).count() == 0:
            generate_synthetic_demo_bhavcopy(db, days=30)
    finally:
        db.close()
