from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from azure.data.tables import TableServiceClient
from dotenv import load_dotenv
import os

# Load environment variables (for local dev)
load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ================================
# 🚦 SAFE AZURE TABLE INITIALIZATION
# ================================

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
table_client = None  # Default to None — we'll try to initialize below

if not connection_string:
    print("❌ ERROR: AZURE_STORAGE_CONNECTION_STRING is not set!")
    print("💡 Set it in:")
    print("   Azure Portal → Your Web App → Configuration → Application Settings")
else:
    try:
        # Initialize Azure Table Service
        table_service = TableServiceClient.from_connection_string(conn_str=connection_string)
        table_client = table_service.get_table_client(table_name="UserData")

        # Create table if not exists
        try:
            table_client.create_table()
            print("✅ Table 'UserData' created successfully.")
        except Exception as e:
            if "TableAlreadyExists" in str(e):
                print("ℹ️ Table 'UserData' already exists.")
            else:
                print("⚠️ Unexpected error while creating table:", e)

    except Exception as e:
        print("❌ Failed to connect to Azure Table Storage:", e)
        print("💡 Check your connection string and network permissions.")


# ================================
# 🏠 HOME PAGE
# ================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ================================
# 💾 SAVE USER (POST)
# ================================

@app.post("/save_user", response_class=HTMLResponse)
async def save_user(
    request: Request,
    user_id: str = Form(...),
    name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...)
):
    # If table_client is not ready, show error
    if table_client is None:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "⚠️ Database is not configured. Please contact administrator."
        })

    # Prepare entity
    entity = {
        "PartitionKey": "Users",  # Simple design — all users in one partition
        "RowKey": user_id,        # Unique user ID
        "Name": name,
        "Phone": phone,
        "Address": address
    }

    try:
        table_client.create_entity(entity=entity)
        saved_message = f"✅ User '{user_id}' saved successfully!"
    except Exception as e:
        if "EntityAlreadyExists" in str(e):
            saved_message = f"⚠️ User ID '{user_id}' already exists. Use a different ID."
        else:
            saved_message = f"❌ Failed to save user: {str(e)}"

    return templates.TemplateResponse("index.html", {
        "request": request,
        "saved": saved_message
    })


# ================================
# 🔍 GET USER (GET)
# ================================

@app.get("/get_user", response_class=HTMLResponse)
async def get_user(request: Request, user_id: str = ""):
    if not user_id:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "📝 Please enter a User ID to search."
        })

    # If table_client is not ready, show error
    if table_client is None:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "⚠️ Database is not configured. Please contact administrator."
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
            "error": f"🔍 User ID '{user_id}' not found in database."
        })


# ================================
# ▶️ START SERVER (FOR AZURE & LOCAL)
# ================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Azure sets PORT, fallback to 8000 locally
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
