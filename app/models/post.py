from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.database import Base


class Post(Base):

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    slug = Column(String(250), unique=True, index=True, nullable=False)
    excerpt = Column(String(500), nullable=True)
    
    is_published = Column(Boolean, default=False, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    
    meta_title = Column(String(200), nullable=True)
    meta_description = Column(String(300), nullable=True)
    tags = Column(String(500), nullable=True)  # Comma-separated tags
    
    view_count = Column(Integer, default=0, nullable=False)
    like_count = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    author = relationship("User", back_populates="posts")
    
    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}', author_id={self.author_id})>"
    
    @property
    def tag_list(self) -> list:
        """Get tags as a list."""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
    
    @tag_list.setter
    def tag_list(self, tags: list):
        """Set tags from a list."""
        self.tags = ", ".join(tags) if tags else None
    
    def increment_view_count(self):
        """Increment the view count."""
        self.view_count += 1
    
    def increment_like_count(self):
        """Increment the like count."""
        self.like_count += 1
    
    def decrement_like_count(self):
        """Decrement the like count (minimum 0)."""
        self.like_count = max(0, self.like_count - 1)
    
    def to_dict(self, include_content: bool = True) -> dict:

        data = {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "excerpt": self.excerpt,
            "is_published": self.is_published,
            "is_featured": self.is_featured,
            "meta_title": self.meta_title,
            "meta_description": self.meta_description,
            "tags": self.tag_list,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "author_id": self.author_id,
        }
        
        if include_content:
            data["content"] = self.content
            
        return data
