"""
数据库初始化脚本

运行此脚本创建数据库和默认用户。

使用方法:
    python init_db.py
"""

if __name__ == "__main__":
    from db import setup_database
    setup_database()
