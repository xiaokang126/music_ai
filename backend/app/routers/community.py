from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..middleware.auth import get_current_user, get_optional_user
from ..models.user_model import User
from ..models.community_model import CommunityPost, Comment, Like, Collect, CommunityVisibilityRule
from ..schemas.community_schema import (
    CommunityPostCreate,
    CommunityPostResponse,
    CommunityPostListResponse,
    CommentCreate,
    CommentResponse,
    LikeCreate,
    CommunityRuleCreate,
    CommunityRuleUser,
    CommunitySettingsResponse,
)

router = APIRouter(prefix="/api/community", tags=["community"])

HIDE_AUTHOR = "hide_author"
BLOCK_VIEWER = "block_viewer"


def _find_user_by_username(db: Session, username: str) -> User:
    target = db.query(User).filter(User.username == username.strip()).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    return target


def _rule_users(db: Session, owner_user_id: str, mode: str) -> list[CommunityRuleUser]:
    rules = db.query(CommunityVisibilityRule).filter(
        CommunityVisibilityRule.owner_user_id == owner_user_id,
        CommunityVisibilityRule.mode == mode,
    ).order_by(CommunityVisibilityRule.created_at.desc()).all()
    result = []
    for rule in rules:
        user = db.query(User).filter(User.id == rule.target_user_id).first()
        if user:
            result.append(CommunityRuleUser(user_id=user.id, username=user.username, created_at=rule.created_at))
    return result


def _get_rule_user_ids(db: Session, owner_user_id: str, mode: str) -> list[str]:
    return [
        row[0] for row in db.query(CommunityVisibilityRule.target_user_id).filter(
            CommunityVisibilityRule.owner_user_id == owner_user_id,
            CommunityVisibilityRule.mode == mode,
        ).all()
    ]


def _get_author_ids_blocking_viewer(db: Session, viewer_user_id: str) -> list[str]:
    return [
        row[0] for row in db.query(CommunityVisibilityRule.owner_user_id).filter(
            CommunityVisibilityRule.target_user_id == viewer_user_id,
            CommunityVisibilityRule.mode == BLOCK_VIEWER,
        ).all()
    ]


def _ensure_rule(db: Session, owner_user_id: str, target_user_id: str, mode: str) -> CommunityVisibilityRule:
    if owner_user_id == target_user_id:
        raise HTTPException(status_code=400, detail="不能对自己设置这项社区规则")
    rule = db.query(CommunityVisibilityRule).filter(
        CommunityVisibilityRule.owner_user_id == owner_user_id,
        CommunityVisibilityRule.target_user_id == target_user_id,
        CommunityVisibilityRule.mode == mode,
    ).first()
    if rule:
        return rule
    rule = CommunityVisibilityRule(owner_user_id=owner_user_id, target_user_id=target_user_id, mode=mode)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def _delete_rule(db: Session, owner_user_id: str, target_user_id: str, mode: str) -> bool:
    rule = db.query(CommunityVisibilityRule).filter(
        CommunityVisibilityRule.owner_user_id == owner_user_id,
        CommunityVisibilityRule.target_user_id == target_user_id,
        CommunityVisibilityRule.mode == mode,
    ).first()
    if not rule:
        return False
    db.delete(rule)
    db.commit()
    return True


@router.post("/posts", response_model=CommunityPostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: CommunityPostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import json
    post = CommunityPost(
        user_id=current_user.id,
        project_id=data.project_id,
        title=data.title,
        description=data.description or data.content,
        story_tags=json.dumps(data.story_tags, ensure_ascii=False) if data.story_tags else '[]',
        is_anonymous=data.is_anonymous,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return _build_post_response(post, current_user.username, viewer=current_user)


@router.get("/posts", response_model=CommunityPostListResponse)
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tag: Optional[str] = Query(None),
    recent_days: Optional[int] = Query(None, ge=1, le=365),
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    query = db.query(CommunityPost)
    if tag:
        query = query.filter(CommunityPost.story_tags.contains(tag))
    if recent_days:
        query = query.filter(CommunityPost.created_at >= datetime.utcnow() - timedelta(days=recent_days))
    if current_user:
        hidden_author_ids = _get_rule_user_ids(db, current_user.id, HIDE_AUTHOR)
        blocked_author_ids = _get_author_ids_blocking_viewer(db, current_user.id)
        excluded_ids = list({*hidden_author_ids, *blocked_author_ids})
        if excluded_ids:
            query = query.filter(~CommunityPost.user_id.in_(excluded_ids))
    total = query.count()
    posts = (
        query.order_by(CommunityPost.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    post_responses = []
    for post in posts:
        author = db.query(User).filter(User.id == post.user_id).first()
        username = author.username if author else "unknown"
        is_liked = False
        if current_user:
            is_liked = db.query(Like).filter(Like.post_id == post.id, Like.user_id == current_user.id).first() is not None
        post_responses.append(_build_post_response(post, username, is_liked=is_liked, viewer=current_user))

    return CommunityPostListResponse(
        posts=post_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/posts/{post_id}", response_model=CommunityPostResponse)
async def get_post(
    post_id: str,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    author = db.query(User).filter(User.id == post.user_id).first()
    username = author.username if author else "unknown"
    if current_user and post.user_id in _get_author_ids_blocking_viewer(db, current_user.id):
        raise HTTPException(status_code=404, detail="动态不存在或不可见")
    is_liked = False
    if current_user:
        is_liked = db.query(Like).filter(Like.post_id == post.id, Like.user_id == current_user.id).first() is not None
    return _build_post_response(post, username, is_liked=is_liked, viewer=current_user)


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(CommunityPost).filter(
        CommunityPost.id == post_id,
        CommunityPost.user_id == current_user.id,
    ).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or not authorized",
        )
    db.query(Comment).filter(Comment.post_id == post_id).delete()
    db.query(Like).filter(Like.post_id == post_id).delete()
    db.query(Collect).filter(Collect.post_id == post_id).delete()
    db.delete(post)
    db.commit()
    return {"detail": "Post deleted successfully"}


@router.get("/settings", response_model=CommunitySettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CommunitySettingsResponse(
        hidden_authors=_rule_users(db, current_user.id, HIDE_AUTHOR),
        blocked_viewers=_rule_users(db, current_user.id, BLOCK_VIEWER),
    )


@router.post("/settings/hidden-authors", response_model=CommunitySettingsResponse)
async def add_hidden_author(
    data: CommunityRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _find_user_by_username(db, data.username)
    _ensure_rule(db, current_user.id, target.id, HIDE_AUTHOR)
    return CommunitySettingsResponse(
        hidden_authors=_rule_users(db, current_user.id, HIDE_AUTHOR),
        blocked_viewers=_rule_users(db, current_user.id, BLOCK_VIEWER),
    )


@router.delete("/settings/hidden-authors/{target_user_id}", response_model=CommunitySettingsResponse)
async def remove_hidden_author(
    target_user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _delete_rule(db, current_user.id, target_user_id, HIDE_AUTHOR)
    return CommunitySettingsResponse(
        hidden_authors=_rule_users(db, current_user.id, HIDE_AUTHOR),
        blocked_viewers=_rule_users(db, current_user.id, BLOCK_VIEWER),
    )


@router.post("/settings/blocked-viewers", response_model=CommunitySettingsResponse)
async def add_blocked_viewer(
    data: CommunityRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _find_user_by_username(db, data.username)
    _ensure_rule(db, current_user.id, target.id, BLOCK_VIEWER)
    return CommunitySettingsResponse(
        hidden_authors=_rule_users(db, current_user.id, HIDE_AUTHOR),
        blocked_viewers=_rule_users(db, current_user.id, BLOCK_VIEWER),
    )


@router.delete("/settings/blocked-viewers/{target_user_id}", response_model=CommunitySettingsResponse)
async def remove_blocked_viewer(
    target_user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _delete_rule(db, current_user.id, target_user_id, BLOCK_VIEWER)
    return CommunitySettingsResponse(
        hidden_authors=_rule_users(db, current_user.id, HIDE_AUTHOR),
        blocked_viewers=_rule_users(db, current_user.id, BLOCK_VIEWER),
    )


@router.post("/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(CommunityPost).filter(
        CommunityPost.id == data.post_id
    ).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    comment = Comment(
        post_id=data.post_id,
        user_id=current_user.id,
        content=data.content,
    )
    db.add(comment)
    post.comments_count += 1
    db.commit()
    db.refresh(comment)
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        user_id=comment.user_id,
        content=comment.content,
        created_at=comment.created_at,
        username=current_user.username,
    )


@router.get("/posts/{post_id}/comments")
async def list_comments(
    post_id: str,
    db: Session = Depends(get_db),
):
    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
        .all()
    )
    result = []
    for c in comments:
        author = db.query(User).filter(User.id == c.user_id).first()
        username = author.username if author else "unknown"
        result.append(
            CommentResponse(
                id=c.id,
                post_id=c.post_id,
                user_id=c.user_id,
                content=c.content,
                created_at=c.created_at,
                username=username,
            )
        )
    return result


@router.post("/likes", status_code=status.HTTP_201_CREATED)
async def toggle_like(
    data: LikeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(CommunityPost).filter(
        CommunityPost.id == data.post_id
    ).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    existing_like = db.query(Like).filter(
        Like.post_id == data.post_id,
        Like.user_id == current_user.id,
    ).first()

    if existing_like:
        db.delete(existing_like)
        post.likes_count = max(0, post.likes_count - 1)
        db.commit()
        return {"detail": "Unliked", "likes_count": post.likes_count}
    else:
        like = Like(post_id=data.post_id, user_id=current_user.id)
        db.add(like)
        post.likes_count += 1
        db.commit()
        return {"detail": "Liked", "likes_count": post.likes_count}


def _build_post_response(
    post: CommunityPost,
    username: str,
    is_liked: bool = False,
    viewer: User | None = None,
) -> CommunityPostResponse:
    anonymous = bool(getattr(post, 'is_anonymous', False))
    return CommunityPostResponse(
        id=post.id,
        user_id=post.user_id,
        project_id=post.project_id,
        title=post.title,
        content=post.description or '',
        description=post.description or '',
        story_tags=getattr(post, 'story_tags', '[]') or '[]',
        likes_count=post.likes_count,
        comments_count=post.comments_count,
        collects_count=getattr(post, 'collects_count', 0) or 0,
        is_liked=is_liked,
        is_anonymous=anonymous,
        can_delete=bool(viewer and post.user_id == viewer.id),
        created_at=post.created_at,
        username="匿名创作者" if anonymous else username,
    )


# ---- Frontend-compatible endpoints ----

@router.post("/posts/{post_id}/comments")
async def create_comment_on_post(
    post_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """前端兼容：POST /api/community/posts/{post_id}/comments"""
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="作品不存在")
    comment = Comment(post_id=post_id, user_id=current_user.id, content=body.get("content", ""))
    db.add(comment)
    post.comments_count += 1
    db.commit()
    return {"id": comment.id, "content": comment.content, "username": current_user.username}


@router.post("/posts/{post_id}/like")
async def toggle_like_on_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """前端兼容：POST /api/community/posts/{post_id}/like"""
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="作品不存在")
    existing = db.query(Like).filter(Like.post_id == post_id, Like.user_id == current_user.id).first()
    if existing:
        db.delete(existing)
        post.likes_count = max(0, post.likes_count - 1)
        db.commit()
        return {"liked": False, "likes_count": post.likes_count}
    else:
        like = Like(post_id=post_id, user_id=current_user.id)
        db.add(like)
        post.likes_count += 1
        db.commit()
        return {"liked": True, "likes_count": post.likes_count}


@router.post("/posts/{post_id}/collect")
async def collect_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """前端兼容：POST /api/community/posts/{post_id}/collect"""
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="作品不存在")
    existing = db.query(Collect).filter(Collect.post_id == post_id, Collect.user_id == current_user.id).first()
    if existing:
        db.delete(existing)
        post.collects_count = max(0, post.collects_count - 1)
        db.commit()
        return {"collected": False, "collects_count": post.collects_count}
    collect = Collect(post_id=post_id, user_id=current_user.id)
    db.add(collect)
    post.collects_count += 1
    db.commit()
    return {"collected": True, "collects_count": post.collects_count}


@router.post("/posts/{post_id}/featured")
async def set_featured(
    post_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Simple demo admin substitute: the post owner can mark/unmark featured."""
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="作品不存在")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能设置自己的作品")
    post.is_featured = bool(body.get("is_featured", True))
    db.commit()
    return {"is_featured": post.is_featured}


@router.get("/featured")
async def featured_posts(db: Session = Depends(get_db)):
    """Weekly featured - top liked posts."""
    posts = db.query(CommunityPost).filter(
        CommunityPost.is_featured == True
    ).order_by(CommunityPost.likes_count.desc()).limit(10).all()
    result = []
    for p in posts:
        author = db.query(User).filter(User.id == p.user_id).first()
        result.append(_build_post_response(p, author.username if author else "匿名"))
    return result
