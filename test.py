from assistant import database

database.initialize_database()

with database.get_connection() as connection:
    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'memory_embeddings'
        """
    ).fetchone()
    
print(dict(row) if row else None)