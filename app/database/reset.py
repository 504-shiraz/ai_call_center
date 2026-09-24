from sqlalchemy import delete

from app.database.connection import get_session, init_db
from app.models.appointment import Appointment

def clear_appointments():
    
    init_db()
    
    with get_session() as session:
        result = session.execute(
            delete(Appointment)
        )
        
        session.commit()
        
        print(f"Deleted {result.rowcount} Appointment(s).")
        
if __name__ == "__main__":
    clear_appointments()