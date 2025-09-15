from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
from app.config import DB_PATH


SQLALCHEMY_DATABASE_URL = "sqlite:///./db.sqlite3"

#import pdb; pdb.set_trace()
engine=create_engine(SQLALCHEMY_DATABASE_URL,connect_args={'check_same_thread':False})
#engine=create_engine(f'sqlite:///{DB_PATH}',connect_args={'check_same_thread':False})
SessionLocal=sessionmaker(bind=engine,autocommit=False,autoflush=False)
Base=declarative_base()
