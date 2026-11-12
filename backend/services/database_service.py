from database import DBManager


class DatabaseService:
    def __init__(self, db: DBManager):
        self.db = db

    def list_documents(self, owner_id: str):
        return self.db.list_documents(owner_id)

    def list_agent_logs(self, owner_id: str, limit: int = 100):
        return self.db.list_agent_logs(owner_id, limit=limit)

    def list_generated_outputs(self, owner_id: str, limit: int = 100):
        return self.db.list_generated_outputs(owner_id, limit=limit)
