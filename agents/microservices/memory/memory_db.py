from peewee import SqliteDatabase

agent_memory = SqliteDatabase('agent_memory.db', pragmas={
                                                        'foreign_keys': True
                                                        }
                            )
