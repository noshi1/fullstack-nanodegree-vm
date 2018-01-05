from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime

from models import User, Categories, Items, Base

engine = create_engine('sqlite:///catalog2.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Delete Categories if exisitng.
session.query(Categories).delete()
# Delete Items if exisitng.
session.query(Items).delete()
# Delete Users if exisitng.
session.query(User).delete()

User1 = User(name="Ibrahim Ashraf",
             email="ibrahim@gmail.com",
             picture='http://dummyimage.com/200x200.png/ff4444/ffffff')
session.add(User1)
session.commit()

category1 = Categories(name='Soccer', user_id=1)
session.add(category1)
session.commit()

Category2 = Categories(name="Football",
                       user_id=1)
session.add(Category2)
session.commit()


item1 = Items(name='Soccer Cleats',
              date=datetime.datetime.now(),
              description='Soccer shoes, soccer cleats, soccer boots',
              category_id=1,
              user_id=1)
session.add(item1)
session.commit()

item2 = Items(name="Football Boots",
              date=datetime.datetime.now(),
              description="Shoes to play football in.",
              category_id=2,
              user_id=1)
session.add(item2)
session.commit()

item3 = Items(name="Football Shirt",
              date=datetime.datetime.now(),
              description="Shirt to play football in.",
              category_id=2,
              user_id=1)
session.add(item3)
session.commit()

print('data is added')
