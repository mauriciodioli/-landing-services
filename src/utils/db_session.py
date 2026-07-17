# src/utils/db_session.py
from contextlib import contextmanager
from extensions import db

@contextmanager
def get_db_session():
    try:
        yield db.session          # usás la scoped_session de SQLAlchemy
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    finally:
        # cerrar conexión en uso (si hay) y devolverla al pool
        try:
            bind = db.session.get_bind()
            if bind and not getattr(bind, "closed", False):
                db.session.close()
        except Exception:
            pass
        finally:
            # importantísimo: limpiar la scoped_session
            try:
                db.session.remove()
            except Exception:
                pass
