
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    average_service_time = db.Column(db.Integer, default=5)
    next_token_number = db.Column(db.Integer, default=1)

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Counter(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    service_id = db.Column(
        db.Integer, db.ForeignKey("service.id"), nullable=False
    )

    is_active = db.Column(db.Boolean, default=True)

    service = db.relationship("Service", backref="counters")


class QueueToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    token_number = db.Column(db.Integer, nullable=False)

    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )

    service_id = db.Column(
        db.Integer, db.ForeignKey("service.id"), nullable=False
    )

    counter_id = db.Column(
        db.Integer, db.ForeignKey("counter.id"), nullable=True
    )

    status = db.Column(
        db.String(20), default="Waiting", nullable=False
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    called_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref="tokens")
    service = db.relationship("Service", backref="tokens")
    counter = db.relationship("Counter", backref="tokens")

    __table_args__ = (
        db.UniqueConstraint(
            "service_id", "token_number",
            name="unique_service_token"
        ),
    )
