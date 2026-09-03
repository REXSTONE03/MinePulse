import os
import sys
from sqlalchemy.orm import Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal
from scripts.generate_synthetic_data import write_data_summary

def main():
    db = SessionLocal()
    try:
        print("Generating data summary report...")
        write_data_summary(db)
        print("Summary report generation finished.")
    except Exception as e:
        print(f"Summary execution error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
