"""
数据库配置和连接
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator

# MySQL 数据库配置
DATABASE_URL = "mysql+pymysql://root:123456@localhost/langgraph_agent_rag?charset=utf8mb4"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # 连接前检查连接是否有效
    connect_args={"connect_timeout": 3},
    echo=False  # 设置为 True 可以看到 SQL 语句
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库，创建所有表
    """
    from src.database.models import Base
    Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    init_db()
