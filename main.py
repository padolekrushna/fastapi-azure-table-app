from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from azure.data.tables import TableServiceClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize Table Service
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
table_service = TableServiceClient.from_connection_string(conn_str=connection_string)
table_client = table_service.get_table_client(table_name="UserData")

# Create table if not exists
try:
    table_client.create_table()
    print("✅ Table 'UserData' created.")
except Exception as e:
    print("ℹ️ Table already exists or error:", e)


# 🏠 Home Page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# 💾 Save User (Handles POST from Save Form)
@app.post("/save_user", response_class=HTMLResponse)
async def save_user(
    request: Request,
    user_id: str = Form(...),
    name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...)
):
    # Prepare entity (row) to save
    entity = {
        "PartitionKey": "Users",  # All users in same partition (simple design)
        "RowKey": user_id,        # Unique ID for each user
        "Name": name,
        "Phone": phone,
        "Address": address
    }

    try:
        table_client.create_entity(entity=entity)
        saved_message = f"User '{user_id}' saved successfully!"
    except Exception as e:
        # If user ID already exists
        saved_message = f"Error: User ID '{user_id}' already exists or failed to save."

    # Show home page again with success message
    return templates.TemplateResponse("index.html", {
        "request": request,
        "saved": saved_message
    })


# 🔍 Get User (Handles GET from Retrieve Form)
@app.get("/get_user", response_class=HTMLResponse)
async def get_user(request: Request, user_id: str = ""):
    if not user_id:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "Please enter a User ID"
        })

    try:
        entity = table_client.get_entity(partition_key="Users", row_key=user_id)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": dict(entity)
        })
    except Exception:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": f"User ID '{user_id}' not found."
        })