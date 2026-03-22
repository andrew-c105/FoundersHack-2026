import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_connection

def migrate():
    conn = get_connection()
    try:
        conn.execute("ALTER TABLE processed_signals RENAME COLUMN confidence TO signal_conf")
        print("Migrated processed_signals")
    except Exception as e:
        print("Error migrating processed_signals:", e)
        
    try:
        conn.execute("ALTER TABLE predictions RENAME COLUMN confidence TO forecast_confidence")
        print("Migrated predictions")
    except Exception as e:
        print("Error migrating predictions:", e)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
