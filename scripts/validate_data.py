import os
import sys
from sqlalchemy.orm import Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal
from scripts.generate_synthetic_data import write_validation_report

def main():
    db = SessionLocal()
    try:
        print("Executing data validation checks...")
        write_validation_report(db)
        print("Validation execution finished.")
    except Exception as e:
        print(f"Validation error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
