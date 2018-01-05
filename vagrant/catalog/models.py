import sys
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine

Base = declarative_base()


"""this class will map user table in the database"""


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(250))
    picture = Column(String(250))

    @property
    def serialize(self):
        """ We added this serialize function to be able to send JSON objects in a
        serializable format"""
        return {
                'id': self.id,
                'name': self.name,
                'email': self.email,
                'picture': self.picture
        }


"""this class will map to categories table in database"""


class Categories(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship(User, backref="categories")

    @property
    def serialize(self):
        """ We added this serialize function to be able to send
        JSON objects in a serializable format"""
        return {
                'id': self.id,
                'name': self.name
        }


"""this Items class will map items table in the database"""


class Items(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(String(255))
    date = Column(DateTime, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship(Categories, backref=backref('items', cascade='all, delete'))
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """ We added this serialize function to be able to send
        JSON objects in a serializable format"""
        return {
                'id': self.id,
                'name': self.name,
                'date': self.date,
                'description': self.description,
                'category': self.category.name
        }


engine = create_engine('sqlite:///catalog2.db')

Base.metadata.create_all(engine)
