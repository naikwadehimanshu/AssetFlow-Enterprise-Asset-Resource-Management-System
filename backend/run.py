import os
import sys
import subprocess

def main():
    # Ensure working directory is the backend root G:\Programming\odoo back\backend
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    # Check if database exists, or if --seed is specified
    db_name = "assetflow.db"
    db_exists = os.path.exists(os.path.join(backend_dir, db_name))
    
    if not db_exists or "--seed" in sys.argv:
        print("Database not found or --seed flag passed. Initializing & seeding database...")
        # Run seed.py using the current python executable
        result = subprocess.run([sys.executable, "seed.py"], capture_output=False)
        if result.returncode != 0:
            print("Error: Database seeding failed. Exiting.")
            sys.exit(1)
    
    # Run uvicorn app.main:app --reload
    print("Launching FastAPI dev server on http://localhost:8000 (Swagger docs at http://localhost:8000/docs)...")
    try:
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["app"])
    except ImportError:
        print("Error: Uvicorn not installed. Please run: pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()
