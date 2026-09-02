from datetime import datetime

from sqlalchemy import inspect, text

from extensions import db


def ensure_album_schema(engine):
    """Migración idempotente para instalaciones existentes del álbum."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "albums" not in tables:
        return
    album_columns = {column["name"] for column in inspector.get_columns("albums")}
    page_columns = {column["name"] for column in inspector.get_columns("album_pages")} if "album_pages" in tables else set()
    indexes = {index["name"] for index in inspector.get_indexes("albums")}
    with engine.begin() as connection:
        if "owner_user_id" not in album_columns:
            connection.execute(text("ALTER TABLE albums ADD COLUMN owner_user_id INTEGER NULL"))
        if "uq_albums_owner_user_id" not in indexes:
            connection.execute(text("CREATE UNIQUE INDEX uq_albums_owner_user_id ON albums (owner_user_id)"))
        if "admin_pin_hash" not in album_columns:
            connection.execute(text("ALTER TABLE albums ADD COLUMN admin_pin_hash VARCHAR(255) NULL"))
        if "admin_session_version" not in album_columns:
            connection.execute(text("ALTER TABLE albums ADD COLUMN admin_session_version INTEGER NOT NULL DEFAULT 1"))
        if "music_url" not in page_columns:
            connection.execute(text("ALTER TABLE album_pages ADD COLUMN music_url VARCHAR(1000) NULL"))
        if "share_enabled" not in page_columns:
            connection.execute(text("ALTER TABLE album_pages ADD COLUMN share_enabled BOOLEAN NOT NULL DEFAULT 1"))
        if "share_version" not in page_columns:
            connection.execute(text("ALTER TABLE album_pages ADD COLUMN share_version INTEGER NOT NULL DEFAULT 1"))


def assign_album_owner(engine, slug, email):
    """Vincula una sola vez un álbum heredado con un usuario DPIA existente."""
    with engine.begin() as connection:
        user_id = connection.execute(
            text("SELECT id FROM usuarios WHERE LOWER(correo_electronico) = :email LIMIT 1"),
            {"email": email.strip().lower()},
        ).scalar()
        if user_id:
            connection.execute(
                text("UPDATE albums SET owner_user_id = :user_id WHERE slug = :slug AND owner_user_id IS NULL"),
                {"user_id": user_id, "slug": slug},
            )


class Album(db.Model):
    __tablename__ = "albums"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), nullable=False, unique=True, index=True)
    title = db.Column(db.String(160), nullable=False)
    subtitle = db.Column(db.String(255))
    music_url = db.Column(db.String(500))
    active = db.Column(db.Boolean, nullable=False, default=True)
    owner_user_id = db.Column(db.Integer, unique=True, index=True)
    admin_pin_hash = db.Column(db.String(255))
    admin_session_version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    pages = db.relationship("AlbumPage", back_populates="album", cascade="all, delete-orphan", order_by="AlbumPage.position")


class AlbumPage(db.Model):
    __tablename__ = "album_pages"
    __table_args__ = (db.UniqueConstraint("album_id", "position", name="uq_album_page_position"),)
    id = db.Column(db.Integer, primary_key=True)
    album_id = db.Column(db.Integer, db.ForeignKey("albums.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    memory_date = db.Column(db.Date)
    description = db.Column(db.Text)
    music_url = db.Column(db.String(1000))
    share_enabled = db.Column(db.Boolean, nullable=False, default=False)
    share_version = db.Column(db.Integer, nullable=False, default=1)
    position = db.Column(db.Integer, nullable=False)
    is_visible = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    album = db.relationship("Album", back_populates="pages")
    media = db.relationship("AlbumMedia", back_populates="page", cascade="all, delete-orphan", order_by="AlbumMedia.position")
    external_media = db.relationship("AlbumExternalMedia", back_populates="page", cascade="all, delete-orphan", order_by="AlbumExternalMedia.position")
    gifts = db.relationship("AlbumGift", back_populates="page", cascade="all, delete-orphan", order_by="AlbumGift.created_at")


class AlbumMedia(db.Model):
    __tablename__ = "album_media"
    __table_args__ = (
        db.UniqueConstraint("object_key", name="uq_album_media_object"),
        db.UniqueConstraint("page_id", "sha256", name="uq_album_media_hash"),
        db.UniqueConstraint("page_id", "position", name="uq_album_media_position"),
    )
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey("album_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    media_type = db.Column(db.Enum("image", "video", name="album_media_type"), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255))
    object_key = db.Column(db.String(700), nullable=False)
    thumbnail_key = db.Column(db.String(700))
    mime_type = db.Column(db.String(100), nullable=False)
    size = db.Column(db.BigInteger, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    duration = db.Column(db.Float)
    position = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    page = db.relationship("AlbumPage", back_populates="media")


class AlbumExternalMedia(db.Model):
    __tablename__ = "album_external_media"
    __table_args__ = (db.UniqueConstraint("page_id", "position", name="uq_album_external_position"),)
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey("album_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    media_type = db.Column(db.String(20), nullable=False)
    provider = db.Column(db.String(30), nullable=False)
    original_url = db.Column(db.String(2000), nullable=False)
    embed_url = db.Column(db.String(2000), nullable=False)
    title = db.Column(db.String(255))
    alt_text = db.Column(db.String(500))
    position = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    page = db.relationship("AlbumPage", back_populates="external_media")


class AlbumGift(db.Model):
    __tablename__ = "album_gifts"
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey("album_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    public_token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    provider = db.Column(db.String(120))
    secret_encrypted = db.Column(db.Text, nullable=False)
    pin_hash = db.Column(db.String(255))
    expires_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default="available", index=True)
    opened_at = db.Column(db.DateTime)
    claimed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    page = db.relationship("AlbumPage", back_populates="gifts")
