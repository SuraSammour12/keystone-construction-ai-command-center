from dotenv import load_dotenv
load_dotenv()

from api.app import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 50)
    print("Construction AI Command Center")
    print("API running at: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)