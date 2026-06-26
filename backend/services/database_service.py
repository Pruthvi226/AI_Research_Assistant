from database import DBManager


class DatabaseService:
    def __init__(self, db: DBManager):
        self.db = db

    def list_documents(self):
        return self.db.list_documents()

    def list_agent_logs(self, limit: int = 100):
        return self.db.list_agent_logs(limit=limit)

    def list_generated_outputs(self, limit: int = 100):
        return self.db.list_generated_outputs(limit=limit)
