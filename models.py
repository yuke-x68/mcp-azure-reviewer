from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel

class Creator(BaseModel):
    displayName: str
    uniqueName: str  # usually email
    id: str

class PullRequest(BaseModel):
    pullRequestId: int
    status: str
    creationDate: datetime
    title: str
    description: Optional[str] = None
    createdBy: Creator
    url: str
    sourceRefName: str
    targetRefName: str

class Change(BaseModel):
    # This models a file change in a PR diff
    originalPath: Optional[str] = None
    path: Optional[str] = None # Identifying path
    changeType: str # edit, add, delete, etc.
    status: Optional[str] = None  # Normalized status: "added", "deleted", "modified", "renamed"
    existsInBase: Optional[bool] = None  # Whether file exists in base branch
    existsInHead: Optional[bool] = None  # Whether file exists in head branch
    item: Optional[dict] = None # contains more info like objectId, etc.

class Thread(BaseModel):
    id: int
    publishedDate: datetime
    lastUpdatedDate: datetime
    comments: List[dict] # Simplified for now, can be detailed if needed
    status: Optional[str] = None

