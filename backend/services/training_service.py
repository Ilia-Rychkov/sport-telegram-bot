class TrainingService:
    def __init__(self, db_session):
        self.db = db_session

    def generate_plan(self, user_id: int, goal: str):
        return "Сгенерированный план"