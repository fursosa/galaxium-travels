from enum import Enum

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BookingStatus(str, Enum):
    """Valid booking status values stored in the ``bookings.status`` column.

    ``CANCELLED`` and ``CANCELED`` are aliases so that both British and
    American spellings are accepted when querying or comparing values.
    """

    BOOKED = "booked"
    CANCELLED = "cancelled"
    CANCELED = "cancelled"  # American spelling alias  # noqa: PIE796
    COMPLETED = "completed"


class User(Base):
    """ORM model for the ``users`` table.

    Attributes:
        user_id: Auto-incremented primary key.
        name: Display name — not required to be unique.
        email: Unique email address; normalised to lowercase before storage.
    """

    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)


class Flight(Base):
    """ORM model for the ``flights`` table.

    Seat counts are tracked per class independently.  Decrementing one class
    counter does not affect the others.

    Attributes:
        flight_id: Auto-incremented primary key.
        origin: Departure location (e.g. ``"Earth"``).
        destination: Arrival location (e.g. ``"Mars"``).
        departure_time: ISO-like string ``"YYYY-MM-DD HH:MM"``.
        arrival_time: ISO-like string ``"YYYY-MM-DD HH:MM"``.
        base_price: Economy (1×) price in credits.
        economy_seats_available: Remaining economy seats (≈60% of total).
        business_seats_available: Remaining business seats (≈30% of total).
        galaxium_seats_available: Remaining galaxium seats (≈10% of total).
    """

    __tablename__ = 'flights'
    flight_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_time = Column(String, nullable=False)
    arrival_time = Column(String, nullable=False)
    base_price = Column(Integer, nullable=False)  # Economy price (1x)
    economy_seats_available = Column(Integer, nullable=False)  # 60% of total
    business_seats_available = Column(Integer, nullable=False)  # 30% of total
    galaxium_seats_available = Column(Integer, nullable=False)  # 10% of total


class Booking(Base):
    """ORM model for the ``bookings`` table.

    ``price_paid`` stores the price at booking time so that later changes to
    ``Flight.base_price`` don't retroactively alter what a user paid.

    Attributes:
        booking_id: Auto-incremented primary key.
        user_id: Foreign key to ``users.user_id``.
        flight_id: Foreign key to ``flights.flight_id``.
        status: One of ``"booked"``, ``"cancelled"``, ``"completed"``.
        booking_time: UTC ISO-8601 timestamp string.
        seat_class: ``"economy"``, ``"business"``, or ``"galaxium"``.
        price_paid: Actual credits charged at booking time.
    """

    __tablename__ = 'bookings'
    booking_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    flight_id = Column(Integer, ForeignKey('flights.flight_id'), nullable=False)
    status = Column(String, nullable=False)
    booking_time = Column(String, nullable=False)
    seat_class = Column(String, nullable=False, default='economy')  # economy/business/galaxium
    price_paid = Column(Integer, nullable=False)  # Actual price at booking time