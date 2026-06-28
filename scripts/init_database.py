#!/usr/bin/env python3
"""
数据库初始化脚本

运行此脚本可以创建或更新数据库表结构
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.database import init_db, engine
from src.database.models import Base, Conversation, Message

def main():
    """初始化数据库"""
    print("=" * 60)
    print("🗄️  初始化数据库...")
    print("=" * 60)
    
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功！")
        print("\n已创建的表：")
        print("  - conversations (对话会话表)")
        print("  - messages (消息历史表)")
        print("\n💡 提示：如果表已存在，此操作不会影响现有数据")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
