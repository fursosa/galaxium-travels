"""User service — registration and lookup of traveller accounts.

All public functions return a Union type (``SomeModel | ErrorResponse``)
rather than raising exceptions.
"""

import re

from sqlalchemy.orm import Session

from models import User
from schemas import ErrorResponse, UserOut


def is_valid_email(email: str) -> bool:
    """Validate email address format."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None


def register_user(db: Session, name: str, email: str) -> UserOut | ErrorResponse:
    """Register a new user with a name and unique email address.

    The email is normalised to lowercase before storage and uniqueness check.

    Args:
        db: SQLAlchemy database session.
        name: Display name for the new user.
        email: Email address — normalised to lowercase; must be unique.

    Returns:
        ``UserOut`` with the newly assigned ``user_id`` on success.
        ``ErrorResponse`` with error code ``INVALID_EMAIL`` or
        ``EMAIL_EXISTS`` on failure.
    """
    email = email.lower()
    
    if not is_valid_email(email):
        return ErrorResponse(
            error="Invalid email format",
            error_code="INVALID_EMAIL",
            details=f"Email '{email}' is not a valid email address. Please provide a valid email in the format: example@domain.com"
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return ErrorResponse(
            error="Email already registered",
            error_code="EMAIL_EXISTS",
            details=f"Email '{email}' is already registered. A user with this email already exists in our system. If you're trying to access an existing account, use get_user with the correct name and email to get the user_id."
        )

    new_user = User(name=name, email=email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserOut.model_validate(new_user)


def get_user(db: Session, name: str, email: str) -> UserOut | ErrorResponse:
    """Retrieve a user's information by name and email.

    Both ``name`` and ``email`` must match a single record.  Email is
    normalised to lowercase before the query.

    Args:
        db: SQLAlchemy database session.
        name: The user's display name.
        email: The user's email address (case-insensitive).

    Returns:
        ``UserOut`` on success.
        ``ErrorResponse`` with error code ``INVALID_EMAIL`` or
        ``USER_NOT_FOUND`` on failure.
    """
    email = email.lower()
    
    if not is_valid_email(email):
        return ErrorResponse(
            error="Invalid email format",
            error_code="INVALID_EMAIL",
            details=f"Email '{email}' is not a valid email address. Please provide a valid email in the format: example@domain.com"
        )
    
    user = db.query(User).filter(User.name == name, User.email == email).first()
    if not user:
        return ErrorResponse(
            error="User not found",
            error_code="USER_NOT_FOUND",
            details=f"User not found with name '{name}' and email '{email}'. The user may not be registered in our system. Please check the spelling of both name and email, or register the user first."
        )
    return UserOut.model_validate(user)
    

def update_user(db: Session, user_id: int, name: str, email: str) -> UserOut | ErrorResponse:
    """Update an existing user's name and email address.

    Email is normalised to lowercase.  No format validation is performed
    on update — the caller is responsible for validation if required.

    Args:
        db: SQLAlchemy database session.
        user_id: ID of the user to update.
        name: New display name.
        email: New email address — normalised to lowercase.

    Returns:
        ``UserOut`` with updated fields on success.
        ``ErrorResponse`` with error code ``USER_NOT_FOUND`` if no user
        with the given ID exists.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return ErrorResponse(
            error="User not found",
            error_code="USER_NOT_FOUND",
            details=f"User with ID {user_id} not found"
        )
    
    # Update user fields without validation
    user.name = name
    user.email = email.lower()
    
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
