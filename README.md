# AssetFlow — Enterprise Asset & Resource Management System

AssetFlow is a robust Enterprise Resource Planning (ERP) backend API designed to track, audit, allocate, and maintain company assets and resources. Built with high-performance modern web technologies, it features role-based access control, dynamic asset attributes, custom category fields, booking reservations, transfer workflows, maintenance ticketing, and scheduled audit cycles.

---

## 🚀 Key Features

*   **🏢 Organization & Departments**: Hierarchical parent-child department mapping, status tracking (Active/Inactive), and Department Head designations.
*   **🔒 Authentication & Role-Based Access Control (RBAC)**: Secure access using JWT tokens with tailored permissions for `admin`, `asset_manager`, `department_head`, and `employee`.
*   **📦 Asset Inventory**:
    *   Dynamic category classification with custom category-specific JSON fields.
    *   Unique asset tags, serial numbers, locations, and condition tracking.
    *   QR code mapping for physical asset identification.
*   **🔄 Allocation & Transfer Workflows**:
    *   Check-out and check-in history tracking return conditions and dates.
    *   Secure transfer requests to pass assets directly between employees, requiring manager or department head approval.
*   **📅 Booking & Scheduling**: Reserve shared assets (such as conference rooms, vehicles, or test equipment) with conflict prevention.
*   **🔧 Maintenance Ticketing**: Maintenance request lifecycles (Pending, Approved, In Progress, Resolved) with priority levels, technician assignments, and resolution notes.
*   **🔍 Audit Cycles**: Plan and execute structural audits. Assign auditors to inspect assets and record status verification (Pending, Verified, Missing, Damaged).
*   **🔔 Notifications & Activity Logs**: System alerts (Asset Assigned, Overdue Returns, Maintenance Updates) and system-wide activity logs.

---

## 🛠️ Tech Stack

*   **Language**: Python 3.8+
*   **Framework**: FastAPI
*   **Database**: SQLite (via SQLAlchemy ORM)
*   **Server**: Uvicorn
*   **Authentication**: PyJWT & Passlib (bcrypt)
*   **Validation**: Pydantic v2

---

## 📂 Project Structure

```text
AssetFlow/
├── backend/
│   ├── app/
│   │   ├── routers/            # API Endpoints (Modular Routers)
│   │   │   ├── auth.py         # Login & Registration
│   │   │   ├── organization.py # Departments & Users
│   │   │   ├── assets.py       # Inventory Management
│   │   │   ├── allocations.py  # Check-in/out & Transfer workflow
│   │   │   ├── bookings.py     # Asset Reservations
│   │   │   ├── maintenance.py  # Repair tickets
│   │   │   ├── audits.py       # Auditing & Verification
│   │   │   ├── reports.py      # Summary & Analytics
│   │   │   └── notifications.py# User Notifications
│   │   ├── config.py           # Application Settings
│   │   ├── crud.py             # Database Operations (CRUD)
│   │   ├── database.py         # SQLAlchemy connection & Session
│   │   ├── dependencies.py     # FastAPI Dependencies (Auth, DB)
│   │   ├── main.py             # FastAPI App Entrypoint
│   │   ├── models.py           # SQLAlchemy Database Models
│   │   └── schemas.py          # Pydantic Schemas for Validation
│   ├── assetflow.db            # SQLite database (Git-ignored/Auto-generated)
│   ├── requirements.txt        # Python package requirements
│   ├── run.py                  # Dev Server Launcher & Seeder
│   └── seed.py                 # Initial data seeding script
└── frontend/                   # Frontend Workspace Placeholder
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.8+** installed on your system.

### 2. Navigate to the Backend Directory
```bash
cd backend
```

### 3. Create and Activate a Virtual Environment
*   **Windows (PowerShell)**:
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```
*   **macOS / Linux**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Application
The `run.py` helper script automatically handles database generation and initial data seeding if no database is found.

Run standard development server:
```bash
python run.py
```

To force-reseed the database, pass the `--seed` flag:
```bash
python run.py --seed
```

The FastAPI application will start on **`http://localhost:8000`**.

---

## 📖 API Documentation & Testing

FastAPI automatically generates interactive documentation. Once the server is running, you can access:

*   **Swagger UI (Interactive Docs)**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **ReDoc (Clean API Reference)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 👥 Seed Accounts for Development

When initialized, the database is seeded with several test accounts having the password **`password123`**:

| Name | Email | Role | Department |
| :--- | :--- | :--- | :--- |
| **Admin User** | `admin@company.com` | `admin` | *None* |
| **Asset Manager** | `manager@company.com` | `asset_manager` | *None* |
| **Aditi Rao** | `aditi@company.com` | `department_head` | Engineering |
| **Rohan Mehta** | `rohan@company.com` | `department_head` | Facilities |
| **Priya Shah** | `priya@company.com` | `employee` | Engineering |
| **Raj Patel** | `raj@company.com` | `employee` | Engineering |
