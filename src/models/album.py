from datetime import datetime
from extensions import db


class Album(db.Model):
    __tablename__ = "albums"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), nullable=False, unique=True, index=True)
    title = db.Column(db.String(160), nullable=False)
    subtitle = db.Column(db.String(255))
    music_url = db.Column(db.String(500))
    active = db.Column(db.Boolean, nullable=False, default=True)
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
    position = db.Column(db.Integer, nullable=False)
    is_visible = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    album = db.relationship("Album", back_populates="pages")
    media = db.relationship("AlbumMedia", back_populates="page", cascade="all, delete-orphan", order_by="AlbumMedia.position")


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
