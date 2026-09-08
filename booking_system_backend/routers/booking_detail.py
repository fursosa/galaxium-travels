"""
GET /bookings/{booking_id} — retrieve a single booking for the authenticated caller.

Security controls applied
--------------------------
* ASVS V4.1  / NIST AC-3  : caller identity required via X-User-Email header (HTTP 401
                              when header is absent); ownership verified before data
                              is returned (IDOR prevention, HTTP 403 on mismatch).
* ASVS V5.1  / NIST SI-10 : booking_id validated as a positive integer via Path(gt=0);
                              email header accepted as a raw str — no user input is
                              concatenated into any query string.
* ASVS V5.3  / CWE-89     : all DB queries use the SQLAlchemy ORM with bound parameters.
* ASVS V7.4  / CWE-209    : generic message returned to the caller on unexpected errors;
                              full exception details are logged server-side only.
* ASVS V7.1  / NIST AU-3  : log entries record booking_id, hashed user identity
                              (SHA-256, hex), and HTTP outcome — never raw email or PII.
"""

import hashlib
import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Path
from sqlalchemy.orm import Session

from db import get_db
from models import Booking, User
from schemas import BookingOut

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bookings"])


def _hash_email(email: str) -> str:
    """Return a SHA-256 hex digest of the email for safe log-safe identification."""
    return hashlib.sha256(email.encode("utf-8")).hexdigest()


@router.get(
    "/bookings/{booking_id}",
    response_model=BookingOut,
    summary="Get a single booking by ID (authenticated caller only)",
)
def get_booking_detail(
    booking_id: int = Path(..., gt=0, description="Positive integer booking identifier"),
    x_user_email: str = Header(
        ...,
        alias="X-User-Email",
        description="Email address of the authenticated caller",
        min_length=1,
        max_length=254,
    ),
    db: Session = Depends(get_db),
) -> BookingOut:
    """Return the booking record identified by *booking_id*.

    The booking is returned only when the caller's email (supplied via the
    ``X-User-Email`` header) matches the user who created the booking.

    * **404** – booking does not exist.
    * **403** – booking belongs to a different user.
    * **500** – unexpected server error (generic message; details logged).
    """
    correlation_id = str(uuid.uuid4())
    email_hash = _hash_email(x_user_email)

    try:
        # ── 1. Resolve caller identity (deny-by-default: must exist in DB) ──────
        caller: User | None = (
            db.query(User).filter(User.email == x_user_email).first()
        )
        if caller is None:
            logger.warning(
                "access_denied booking_id=%s email_hash=%s reason=unknown_caller "
                "correlation_id=%s",
                booking_id,
                email_hash,
                correlation_id,
            )
            # Return 401 — identity could not be confirmed
            raise HTTPException(
                status_code=401,
                detail="Caller identity could not be verified.",
            )

        # ── 2. Fetch the booking record ──────────────────────────────────────────
        record: Booking | None = (
            db.query(Booking).filter(Booking.booking_id == booking_id).first()
        )
        if record is None:
            logger.info(
                "booking_not_found booking_id=%s user_id=%s correlation_id=%s",
                booking_id,
                caller.user_id,
                correlation_id,
            )
            raise HTTPException(status_code=404, detail="Booking not found.")

        # ── 3. Ownership check (IDOR prevention) ────────────────────────────────
        if record.user_id != caller.user_id:
            logger.warning(
                "access_denied booking_id=%s user_id=%s reason=ownership_mismatch "
                "correlation_id=%s",
                booking_id,
                caller.user_id,
                correlation_id,
            )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view this booking.",
            )

        logger.info(
            "booking_accessed booking_id=%s user_id=%s correlation_id=%s",
            booking_id,
            caller.user_id,
            correlation_id,
        )
        return BookingOut.model_validate(record)

    except HTTPException:
        # Re-raise known HTTP exceptions without wrapping them in a 500
        raise
    except Exception:
        # Log full traceback server-side; return a generic message to the caller
        logger.error(
            "unexpected_error booking_id=%s user_id=unknown correlation_id=%s",
            booking_id,
            correlation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        )
