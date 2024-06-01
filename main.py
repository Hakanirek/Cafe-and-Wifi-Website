import os
import smtplib
from functools import wraps

from forms import CafeForm, LoginForm, RegisterForm, ContactForm, UpdateCafeForm
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, URL
import csv
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

'''
Red underlines? Install the required packages first: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = "8BYkEfBA6O6donzWlSihBXox7C0sKR6b"
ckeditor = CKEditor(app)
Bootstrap5(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///cafes.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class Cafes(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cafe_name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(250), nullable=False)
    open_time: Mapped[str] = mapped_column(String(250), nullable=False)
    close_time: Mapped[str] = mapped_column(String(250), nullable=False)
    coffee: Mapped[str] = mapped_column(Text, nullable=False)
    wifi: Mapped[str] = mapped_column(Text, nullable=False)
    power: Mapped[str] = mapped_column(Text, nullable=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))


with app.app_context():
    db.create_all()


def admin_only(f):  # https://flask.palletsprojects.com/en/2.3.x/patterns/viewdecorators/
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def home():
    return render_template("index.html", current_user=current_user)


@app.route('/cafes')
def cafes():
    with app.app_context():
        result = db.session.execute(db.select(Cafes))

        all_cafes = result.scalars().all()

        return render_template('cafes.html', cafes=all_cafes)


@app.route('/add', methods=["GET", "POST"])
def add_cafe():
    form = CafeForm()
    if form.validate_on_submit():
        with app.app_context():
            new_book = Cafes(cafe_name=form.cafe_name.data, location=form.location.data, open_time=form.open.data,
                             close_time=form.close.data,
                             coffee=form.coffee_rating.data, wifi=form.wifi_rating.data, power=form.power_rating.data)
            db.session.add(new_book)
            db.session.commit()

        return redirect(url_for('cafes'))

    return render_template('add.html', form=form, current_user=current_user)


@app.route('/update/<int:cafe_id>', methods=["GET", "POST"])
def update_cafe(cafe_id):
    cafe = db.get_or_404(Cafes, cafe_id)
    form = UpdateCafeForm(
        cafe_name=cafe.cafe_name,
        location=cafe.location,
        open_time=cafe.open_time,
        close_time=cafe.close_time,
        coffee_rating=cafe.coffee,
        wifi_rating=cafe.wifi,
        power_rating=cafe.power
    )
    if form.validate_on_submit():
        cafe.cafe_name = form.cafe_name.data
        cafe.location = form.location.data
        cafe.open_time = form.open_time.data
        cafe.close_time = form.close_time.data
        cafe.coffee = form.coffee_rating.data
        cafe.wifi = form.wifi_rating.data
        cafe.power = form.power_rating.data
        db.session.commit()
        return redirect(url_for('cafes'))
    return render_template('update.html', form=form, cafe=cafe, current_user=current_user)


@app.route("/delete/<int:cafe_id>", methods=["POST"])
@admin_only
def delete_cafe(cafe_id):
    post_to_delete = db.get_or_404(Cafes, cafe_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('cafes'))


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Find user by email entered.
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for("login"))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Find user by email entered.
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()

        if not user:
            flash('Email does not exist. Please try again!')
            return redirect(url_for("login"))

        elif not check_password_hash(user.password, password):
            flash('Passwort incorrect. Please try again!')
            return redirect(url_for("login"))

        else:
            login_user(user)
        return redirect(url_for("home"))

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('cafes'))


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


MAIL_ADDRESS = "hakan134134@gmail.com"
MAIL_APP_PW = "opadnfhokuraotsx"


@app.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        name = form.email.data
        email = form.email.data
        phone = form.phone.data
        message = form.message.data

        send_email(name, email, phone, message)
        return render_template("contact.html", msg_sent=True, form=form)
    return render_template("contact.html", msg_sent=False, form=form)


def send_email(name, email, phone, message):
    email_message = f"Subject:New Message\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage:{message}"
    with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
        connection.starttls()
        connection.login(MAIL_ADDRESS, MAIL_APP_PW)
        connection.sendmail(MAIL_ADDRESS, MAIL_ADDRESS, email_message)


if __name__ == '__main__':
    app.run(debug=True, port=5002)
