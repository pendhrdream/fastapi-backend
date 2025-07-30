from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime
from app.schemas.user import User


class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    excerpt: Optional[str] = Field(None, max_length=500)
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = Field(None, max_length=300)
    tags: Optional[List[str]] = Field(None, max_items=10)
    is_featured: bool = False


class PostCreate(PostBase):
    slug: Optional[str] = Field(None, min_length=1, max_length=250, regex="^[a-z0-9-]+$")
    
    @validator('slug', pre=True, always=True)
    def generate_slug(cls, v, values):
        if not v and 'title' in values:
            slug = values['title'].lower()
            slug = ''.join(c if c.isalnum() else '-' for c in slug)
            slug = '-'.join(filter(None, slug.split('-')))
            return slug[:250]
        return v
    
    @validator('excerpt', pre=True, always=True)
    def generate_excerpt(cls, v, values):
        if not v and 'content' in values:
            content = values['content']
            import re
            clean_content = re.sub('<[^<]+?>', '', content)
            return clean_content[:497] + "..." if len(clean_content) > 500 else clean_content
        return v


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    excerpt: Optional[str] = Field(None, max_length=500)
    slug: Optional[str] = Field(None, min_length=1, max_length=250, regex="^[a-z0-9-]+$")
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = Field(None, max_length=300)
    tags: Optional[List[str]] = Field(None, max_items=10)
    is_featured: Optional[bool] = None
    is_published: Optional[bool] = None


class PostInDBBase(PostBase):
    id: int
    slug: str
    is_published: bool
    view_count: int
    like_count: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    author_id: int

    class Config:
        orm_mode = True


class Post(PostInDBBase):
    author: Optional[User] = None


class PostSummary(BaseModel):
    id: int
    title: str
    excerpt: Optional[str]
    slug: str
    is_published: bool
    is_featured: bool
    tags: Optional[List[str]]
    view_count: int
    like_count: int
    created_at: datetime
    published_at: Optional[datetime]
    author_id: int
    author: Optional[User] = None

    class Config:
        orm_mode = True


class PostDetail(PostInDBBase):
    author: User

    class Config:
        orm_mode = True


class PostPublish(BaseModel):
    is_published: bool = True
    published_at: Optional[datetime] = None


class PostStats(BaseModel):
    id: int
    title: str
    view_count: int
    like_count: int
    created_at: datetime
    published_at: Optional[datetime]

    class Config:
        orm_mode = True


class PostList(BaseModel):
    posts: List[PostSummary]
    total: int
    page: int
    per_page: int
    pages: int

    class Config:
        orm_mode = True


class PostSearch(BaseModel):
    query: Optional[str] = Field(None, min_length=1, max_length=100)
    tags: Optional[List[str]] = Field(None, max_items=5)
    author_id: Optional[int] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class PostBulkAction(BaseModel):
    post_ids: List[int] = Field(..., min_items=1, max_items=100)
    action: str = Field(..., regex="^(publish|unpublish|delete|feature|unfeature)$")

    @validator('post_ids')
    def validate_post_ids(cls, v):
        """Ensure all post IDs are positive."""
        if any(post_id <= 0 for post_id in v):
            raise ValueError('All post IDs must be positive integers')
        return v
