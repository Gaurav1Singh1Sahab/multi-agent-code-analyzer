from datetime import datetime


def generate_project_id(db_project_count: int) -> str:
    today = datetime.now().strftime("%Y%m%d")
    serial = str(db_project_count + 1).zfill(4)
    return f"PROJ-{today}-{serial}"