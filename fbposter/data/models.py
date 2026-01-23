"""
Data models for Facebook Auto-Poster
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
import uuid


@dataclass
class Group:
    """Represents a Facebook group"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    city: str = ""
    name: str = ""
    language: str = ""  # e.g., "es", "en", "de" - empty means default/unspecified
    active: bool = True
    last_posted: Optional[datetime] = None
    notes: str = ""

    def __post_init__(self):
        """Validate required fields"""
        if not self.url:
            raise ValueError("Group URL is required")
        if not self.city:
            raise ValueError("City label is required")

    @property
    def city_key(self) -> str:
        """Returns city with language suffix for job filtering (e.g., 'Paris-es')"""
        if self.language:
            return f"{self.city}-{self.language}"
        return self.city

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "url": self.url,
            "city": self.city,
            "name": self.name,
            "language": self.language,
            "active": self.active,
            "last_posted": self.last_posted.isoformat() if self.last_posted else None,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Group':
        """Create from dictionary"""
        if data.get("last_posted"):
            data["last_posted"] = datetime.fromisoformat(data["last_posted"])
        # Handle old data without language field
        if "language" not in data:
            data["language"] = ""
        return cls(**data)


@dataclass
class Text:
    """Represents a post text template"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    content: str = ""
    image_url: Optional[str] = None
    user_id: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate required fields"""
        if not self.name:
            raise ValueError("Text name is required")
        if not self.content:
            raise ValueError("Text content is required")

    def format(self, **kwargs) -> str:
        """Format text with placeholders"""
        try:
            return self.content.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing placeholder value: {e}")

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "image_url": self.image_url,
            "user_id": self.user_id,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Text':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class Job:
    """Represents a posting job configuration"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    text_id: str = ""
    group_filters: Dict = field(default_factory=dict)
    schedule: str = ""
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

    def __post_init__(self):
        """Validate required fields"""
        if not self.name:
            raise ValueError("Job name is required")
        if not self.text_id:
            raise ValueError("Text ID is required")
        if not self.schedule:
            raise ValueError("Schedule is required")

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "text_id": self.text_id,
            "group_filters": self.group_filters,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Job':
        """Create from dictionary"""
        if data.get("last_run"):
            data["last_run"] = datetime.fromisoformat(data["last_run"])
        if data.get("next_run"):
            data["next_run"] = datetime.fromisoformat(data["next_run"])
        return cls(**data)


@dataclass
class PostLog:
    """Represents a posting attempt log entry"""
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    job_id: str = ""
    text_id: str = ""
    group_id: str = ""
    group_url: str = ""
    city: str = ""
    status: str = ""  # 'success', 'failed', 'skipped'
    error_message: Optional[str] = None
    retry_count: int = 0
    duration_ms: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "job_id": self.job_id,
            "text_id": self.text_id,
            "group_id": self.group_id,
            "group_url": self.group_url,
            "city": self.city,
            "status": self.status,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "duration_ms": self.duration_ms,
        }
