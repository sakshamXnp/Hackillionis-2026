from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr, declarative_base

Base = declarative_base()

class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(String(100), nullable=False)

    @declared_attr
    def __init__(self, username, email, password_hash, created_at):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at

    def __repr__(self):
        return f'<Account(username={self.username}, email={self.email})>'
