from sqlalchemy import Column, ForeignKey, Integer, String, LargeBinary
from sqlalchemy_imageattach.entity import Image, image_attachment
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
 
Base = declarative_base()

class Picture(Base, Image):
    """User picture model."""
    car_id = Column(Integer, ForeignKey('car.id'), primary_key=True)
    car = relationship('Car')
    __tablename__ = 'picture'
    
class Logo(Base, Image):
    """User picture model."""
    brand_id = Column(Integer, ForeignKey('brand.id'), primary_key=True)
    brand = relationship('Brand')
    __tablename__ = 'logo'
        
class User(Base):
    __tablename__ = 'user'
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    id = Column(Integer, primary_key=True)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
           'email'        : self.email,        
       }

class Brand(Base):
    __tablename__ = 'brand'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship(User)
    logo = image_attachment('Logo')

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
           'user_id'        : self.user_id,        
       }

class Car(Base):
    __tablename__ = 'car'
    name = Column(String(250), nullable=False)
    id = Column(Integer, primary_key=True)
    # picture = image_attachment('Picture')
    price = Column(String(8))
    condition = Column(String(8))
    color = Column(String(8))
    description = Column(String(250))
    model = Column(String(250), nullable=False)
    specs = Column(String(250))
    highlights = Column(String(250))
    # picture = image_attachment('Picture')
    image = Column(LargeBinary)
    brand_id = Column(Integer, ForeignKey('brand.id'), nullable=False)
    brand = relationship('Brand')
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
           'email'        : self.email,     
           'price'        : self.price,
           'condition'    : self.condition,
           'description'  : self.description,
           'model'        : self.model,
           'specs'        : self.specs,
           'highlights'   : self.highlights,
           'brand_id'     : self.brand_id,
           'user_id'      : self.user_id,
       }

engine = create_engine('sqlite:///catalogdb.db')
Base.metadata.create_all(engine)