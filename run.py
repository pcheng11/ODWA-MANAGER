from src import app
from src import celery

if __name__ == "__main__":
    # app = create_app(debug=True)
    app.run(port=5000)
