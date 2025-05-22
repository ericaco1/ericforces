from flask import Flask
from extensions import db
from models import User, File, Folder, StorageClass

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'cle-secrete-a-changer'

db.init_app(app)

@app.route('/')
def home():
    return "<h1>Bienvenue sur EFORICE - Site prêt à déployer !</h1>"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)