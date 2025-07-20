from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["AgentDB"]

def get_async_collections():
    return {
        "users": db["users"],
        "student_data": db["student_data"],
        "company_data": db["company_data"],
        "job_data": db["job_data"],
        "compatibility_results": db["compatibility_results"]
    }