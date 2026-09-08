from typing import Literal

from pydantic import BaseModel, ConfigDict

# Seat class type definition
SeatClass = Literal['economy', 'business', 'galaxium']


class FlightQueryParams(BaseModel):
    """Query parameters for filtering and sorting flights."""
    # Location filters (case-insensitive partial match)
    origin: str | None = None
    destination: str | None = None
    
    # Date range filters (format: YYYY-MM-DD)
    departure_date_from: str | None = None
    departure_date_to: str | None = None
    
    # Price range filters
    min_price: int | None = None
    max_price: int | None = None
    
    # Seat availability filters (at least 1 seat available)
    has_economy: bool | None = None
    has_business: bool | None = None
    has_galaxium: bool | None = None
    
    # Sorting
    sort: Literal['price', 'departure_time', 'duration'] | None = None
    order: Literal['asc', 'desc'] | None = 'asc'


class FlightOut(BaseModel):
    """Serialised flight returned from the API.

    Prices for all three seat classes are computed from ``base_price``
    and included so that clients don't need to know the multipliers.
    """

    flight_id: int
    origin: str
    destination: str
    departure_time: str  # Format: YYYY-MM-DD HH:MM
    arrival_time: str    # Format: YYYY-MM-DD HH:MM
    base_price: int  # Economy price (1x)
    economy_seats_available: int
    business_seats_available: int
    galaxium_seats_available: int
    # Computed prices for all classes
    economy_price: int
    business_price: int
    galaxium_price: int

    model_config = ConfigDict(from_attributes=True)


class BookingRequest(BaseModel):
    """Request body for ``POST /book``.

    Both ``user_id`` and ``name`` are required.  The backend validates that
    ``name`` matches the account registered for ``user_id`` — a mismatch
    returns a ``NAME_MISMATCH`` error.
    """

    user_id: int
    name: str
    flight_id: int
    seat_class: SeatClass = 'economy'  # Default to economy


class BookingOut(BaseModel):
    """Serialised booking returned from the API."""

    booking_id: int
    user_id: int
    flight_id: int
    status: str
    booking_time: str
    seat_class: str
    price_paid: int

    model_config = ConfigDict(from_attributes=True)


class UserRegistration(BaseModel):
    """Request body for ``POST /register``."""

    name: str
    email: str


class UserOut(BaseModel):
    """Serialised user returned from the API."""

    user_id: int
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Structured error returned by all service functions on failure.

    Service functions return ``SomeModel | ErrorResponse`` instead of raising
    exceptions.  Callers use ``isinstance(result, ErrorResponse)`` to detect
    failures.  The REST layer then maps ``error_code`` to an HTTP status code.

    Attributes:
        success: Always ``False`` — lets clients distinguish errors from
            successful responses with a simple ``result.success`` check.
        error: Short human-readable message (e.g. ``"User not found"``).
        error_code: Machine-readable identifier for branching logic
            (e.g. ``"USER_NOT_FOUND"``, ``"NAME_MISMATCH"``).
        details: Optional extended explanation useful for debugging or
            surfacing to end users.
    """

    success: bool = False
    error: str
    error_code: str
    details: str | None = None
