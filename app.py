
from flask import render_template, request, flash, redirect, Flask, send_file, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import smtplib
import os
from flask_login import login_manager, login_user, login_required, logout_user, current_user, UserMixin, LoginManager
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash

# >>>> DEFINING FUNCTIONS TO CALL <<<<

#setting up the send email function with smtplib
def email_alert(subject, body, to):
    msg = EmailMessage()
    msg.set_content(body)
    msg['subject'] = subject
    msg['to'] = to

    user = "bramptonsquashbot@gmail.com"
    msg['from'] = user
    email_password = os.getenv("bot_password")

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(user, email_password)
    server.send_message(msg)

    server.quit()

# >>>> SETTING UP CONFIGS/APP/DB <<<<

app = Flask(__name__)
load_dotenv()

ENV = 'dev'

if ENV == 'dev':
        app.debug = True
        DB_NAME = "database.db"
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'

else:
    app.debug = False
    data_base_url = os.getenv("database_link")
    app.config['SQLALCHEMY_DATABASE_URI'] = data_base_url


the_secret_key = os.getenv("secret_key")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = the_secret_key


db = SQLAlchemy(app)


# >>>> CREATING DATABASE MODELS <<<<

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))

class Announcements(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    announcement_item = db.Column(db.String(2000))
    date_created = db.Column(db.String(1000))
    rank = db.Column(db.Integer)

class League_Information(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_number = db.Column(db.Integer, unique=True)
    league_name = db.Column(db.String(500))
    contact_name = db.Column(db.String(500))
    email = db.Column(db.String(500))
    link = db.Column(db.String(2000))

class Resources(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    heading = db.Column(db.String(1000))
    description = db.Column(db.String(2000))
    link = db.Column(db.String(2000))
    rank = db.Column(db.Integer)

class Quick_Links(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(2000))
    link = db.Column(db.String(2000))
    rank = db.Column(db.Integer)

# >>>> HOME PAGE <<<<

@app.route('/',methods=['GET','POST'])
def home():
    try:
        page_title = 'Brampton Squash'
        announcement_items = Announcements.query.order_by(Announcements.rank)
        leagues = League_Information.query.order_by(League_Information.league_number)
        resources = Resources.query.order_by(Resources.rank)
        quick_links = Quick_Links.query.order_by(Quick_Links.rank)
        return render_template("home.html",page_title=page_title, user=current_user,announcement_items=announcement_items,leagues=leagues,resources=resources,quick_links=quick_links)
    except:
        redirect('/error')

@app.route('/error',methods=['GET','POST'])
def error():
    page_title = 'Brampton Squash - Site Error'
    return render_template("error.html", page_title=page_title)

# >>>> ADMIN SECTION <<<<

@app.route('/admin_login', methods=['GET','POST'])
def admin_login():
    page_title = 'Brampton Squash - Admin Login'
    return render_template("admin_login.html",page_title=page_title, user=current_user)

@app.route('/create_admin', methods=['GET','POST'])
def create_admin():
    page_title = 'Brampton Squash'
    if request.method == 'POST':
        name = request.form.get('name')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        secret_code = request.form.get('secret_code')

        the_secret_code = os.getenv("secret_code")

        user = User.query.filter_by(name=name).first()
        if user:
            flash('Name already exists', category='error')
        elif password1 != password2:
            flash('Passwords did not match', category='error')
        elif len(password1) < 5:
            flash('Password is too short... Must be at least 5 characters long', category='error')
        elif secret_code != the_secret_code:
            flash('Contact an admin to get the secret code to create an account', category='error')
        else:
            new_user = User(name=name, password=generate_password_hash(password1, method='sha256'))
            db.session.add(new_user)
            db.session.commit()
            flash('Account Created! Please remember your password, there is currently no way to find your password if forgotten', category='success')
        return redirect('/admin_login')
    else:
        return render_template("create_admin.html",user=current_user,page_title=page_title)

@app.route('/delete-admin/<int:id>', methods=['GET','POST'])
@login_required
def delete_admin(id):
    to_delete = User.query.get_or_404(id)
    db.session.delete(to_delete)
    db.session.commit()
    return redirect('/')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        user = User.query.filter_by(name=name).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember=True)
                return redirect('/admin_page')
            else:
                flash('Incorrect Password',category='error')
        else:
            flash('Name does not exist',category='error')
        return redirect('/admin_login')
    else:
        return redirect('/')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

@app.route('/admin_page', methods=['GET','POST'])
@login_required
def admin_page():
    page_title = 'Brampton Squash - Admin Page'
    announcement_items = Announcements.query.order_by(Announcements.rank)
    leagues = League_Information.query.order_by(League_Information.league_number)
    resources = Resources.query.order_by(Resources.rank)
    quick_links = Quick_Links.query.order_by(Quick_Links.rank)
    all_users = User.query.order_by(User.name)
    secret_code = os.getenv("secret_code")

    return render_template("admin_page.html",page_title=page_title, user=current_user,announcement_items=announcement_items,leagues=leagues,all_users=all_users,secret_code=secret_code,resources=resources,quick_links=quick_links)


# >>>> LEAGUES <<<<

@app.route('/add_league_info', methods=['GET','POST'])
@login_required
def add_league_info():
    if request.method == 'POST':
        league_number = request.form.get('league_number')
        league_name = request.form.get('league_name')
        contact_name = request.form.get('contact_name')
        email = request.form.get('email')
        link = request.form.get('link')
        new_league = League_Information(league_number=league_number,league_name=league_name,contact_name=contact_name,email=email,link=link)
        db.session.add(new_league)
        db.session.commit()
        return redirect('/admin_page')

@app.route('/delete-league/<int:id>', methods=['GET','POST'])
@login_required
def delete_league(id):
    to_delete = League_Information.query.get_or_404(id)
    db.session.delete(to_delete)
    db.session.commit()
    return redirect('/admin_page')

@app.route('/update-league/<int:id>', methods=['GET','POST'])
@login_required
def update_league(id):
    page_title = "Brampton Squash - Update League"
    l = League_Information.query.get_or_404(id)
    if request.method == 'POST':
        l.league_number = request.form['update_number']
        l.league_name = request.form['update_league_name']
        l.contact_name = request.form['update_contact_name']
        l.email = request.form['update_email']
        l.link = request.form['update_link']
        db.session.commit()
        return redirect('/admin_page')
    else:
        return render_template("update_league.html",page_title=page_title, l=l,user=current_user)


# >>>> ANNOUNCEMENTS <<<<

@app.route('/add_announcement_item', methods=['GET','POST'])
@login_required
def add_announcement_item():
    if request.method == 'POST':
        announcement_item = request.form.get('item')
        date_created = request.form.get('date')
        rank = request.form.get('rank')
        new_announcement = Announcements(announcement_item=announcement_item, date_created=date_created,rank=rank)
        db.session.add(new_announcement)
        db.session.commit()
        return redirect('/admin_page')

@app.route('/delete-announcement/<int:id>', methods=['GET','POST'])
@login_required
def delete_announcement(id):
    to_delete = Announcements.query.get_or_404(id)
    db.session.delete(to_delete)
    db.session.commit()
    return redirect('/admin_page')

@app.route('/update-announcement/<int:id>', methods=['GET','POST'])
@login_required
def update_announcement(id):
    page_title = "Brampton Squash - Update Announcement"
    a = Announcements.query.get_or_404(id)
    if request.method == 'POST':
        a.announcement_item = request.form['update_announcement']
        a.date_created = request.form['update_date']
        a.rank = request.form['update_rank']
        db.session.commit()
        return redirect('/admin_page')
    else:
        return render_template("update_announcement.html",page_title=page_title, a=a,user=current_user)


# >>>> RESOURCES <<<<

@app.route('/add_resource', methods=['GET','POST'])
@login_required
def add_resource():
    if request.method == 'POST':
        heading = request.form.get('heading')
        description = request.form.get('description')
        link = request.form.get('link')
        rank = request.form.get('rank')
        new_resource = Resources(heading=heading,description=description,link=link,rank=rank)
        db.session.add(new_resource)
        db.session.commit()
        return redirect('/admin_page')

@app.route('/delete-resource/<int:id>', methods=['GET','POST'])
@login_required
def delete_resource(id):
    to_delete = Resources.query.get_or_404(id)
    db.session.delete(to_delete)
    db.session.commit()
    return redirect('/admin_page')

@app.route('/update-resource/<int:id>', methods=['GET','POST'])
@login_required
def update_resource(id):
    page_title = "Brampton Squash - Update Resource"
    r = Resources.query.get_or_404(id)
    if request.method == 'POST':
        r.heading = request.form['update_heading']
        r.description = request.form['update_description']
        r.link = request.form['update_link']
        r.rank = request.form['update_rank']
        db.session.commit()
        return redirect('/admin_page')
    else:
        return render_template("update_resource.html",page_title=page_title, r=r,user=current_user)


# >>>> QUICK LINKS <<<<

@app.route('/add_quick_link', methods=['GET','POST'])
@login_required
def add_quick_link():
    if request.method == 'POST':
        description = request.form.get('description')
        link = request.form.get('link')
        rank = request.form.get('rank')
        new_quick_link = Quick_Links(description=description,link=link,rank=rank)
        db.session.add(new_quick_link)
        db.session.commit()
        return redirect('/admin_page')

@app.route('/delete-quick_link/<int:id>', methods=['GET','POST'])
@login_required
def delete_quick_link(id):
    to_delete = Quick_Links.query.get_or_404(id)
    db.session.delete(to_delete)
    db.session.commit()
    return redirect('/admin_page')

@app.route('/update-quick_link/<int:id>', methods=['GET','POST'])
@login_required
def update_quick_link(id):
    page_title = "Brampton Squash - Update Quick Link"
    q = Quick_Links.query.get_or_404(id)
    if request.method == 'POST':
        q.description = request.form['update_description']
        q.link = request.form['update_link']
        q.rank = request.form['update_rank']
        db.session.commit()
        return redirect('/admin_page')
    else:
        return render_template("update_quick_link.html",page_title=page_title, q=q,user=current_user)


# >>>> LOADING LEAGUE PAGES <<<<

# >>>> SUBMIT SCORES PAGES <<<<

@app.route('/1-submit_scores')
def submit_scores1():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("1-submit_scores.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/2-submit_scores')
def submit_scores2():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("2-submit_scores.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/3-submit_scores')
def submit_scores3():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("3-submit_scores.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/4-submit_scores')
def submit_scores4():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("4-submit_scores.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/5-submit_scores')
def submit_scores5():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("5-submit_scores.html",page_title=page_title,user=current_user,leagues=leagues)


# >>>> SIGNUP PAGES <<<<

@app.route('/1-sign_up')
def sign_up1():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("1-sign_up.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/2-sign_up')
def sign_up2():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("2-sign_up.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/3-sign_up')
def sign_up3():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("3-sign_up.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/4-sign_up')
def sign_up4():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("4-sign_up.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/5-sign_up')
def sign_up5():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("5-sign_up.html",page_title=page_title,user=current_user,leagues=leagues)


# >>>> REQUEST INFORMATION PAGES <<<<

@app.route('/1-request_info')
def request_info1():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("1-request_info.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/2-request_info')
def request_info2():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("2-request_info.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/3-request_info')
def request_info3():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("3-request_info.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/4-request_info')
def request_info4():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("4-request_info.html",page_title=page_title,user=current_user,leagues=leagues)

@app.route('/5-request_info')
def request_info5():
    page_title = 'Brampton Squash'
    leagues = League_Information.query.order_by(League_Information.league_number)
    return render_template("5-request_info.html",page_title=page_title,user=current_user,leagues=leagues)


# >>>> SENDING SCORES EMAILS <<<<

@app.route('/1-send_scores', methods=['GET','POST'])
def send_scores1():
    leagues = League_Information.query.filter_by(league_number=1)
    if request.method == 'POST':
        p1_name = request.form.get('p1_name')
        p1_score = request.form.get('p1_score')
        p2_name = request.form.get('p2_name')
        p2_score = request.form.get('p2_score')
        user_email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Score Submission')
            body = (f'Player 1 - Name: {p1_name}\nPlayer 1 - Score: {p1_score}\nPlayer 2 - Name: {p2_name}\nPlayer 2 - Score: {p2_score}\nYour Email: {user_email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Score submitted successfully!', category='success')
        return redirect('/1-submit_scores')

@app.route('/2-send_scores', methods=['GET','POST'])
def send_scores2():
    leagues = League_Information.query.filter_by(league_number=2)
    if request.method == 'POST':
        p1_name = request.form.get('p1_name')
        p1_score = request.form.get('p1_score')
        p2_name = request.form.get('p2_name')
        p2_score = request.form.get('p2_score')
        user_email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Score Submission')
            body = (f'Player 1 - Name: {p1_name}\nPlayer 1 - Score: {p1_score}\nPlayer 2 - Name: {p2_name}\nPlayer 2 - Score: {p2_score}\nYour Email: {user_email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Score submitted successfully!', category='success')
        return redirect('/2-submit_scores')

@app.route('/3-send_scores', methods=['GET','POST'])
def send_scores3():
    leagues = League_Information.query.filter_by(league_number=3)
    if request.method == 'POST':
        p1_name = request.form.get('p1_name')
        p1_score = request.form.get('p1_score')
        p2_name = request.form.get('p2_name')
        p2_score = request.form.get('p2_score')
        user_email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Score Submission')
            body = (f'Player 1 - Name: {p1_name}\nPlayer 1 - Score: {p1_score}\nPlayer 2 - Name: {p2_name}\nPlayer 2 - Score: {p2_score}\nYour Email: {user_email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Score submitted successfully!', category='success')
        return redirect('/3-submit_scores')

@app.route('/4-send_scores', methods=['GET','POST'])
def send_scores4():
    leagues = League_Information.query.filter_by(league_number=4)
    if request.method == 'POST':
        p1_name = request.form.get('p1_name')
        p1_score = request.form.get('p1_score')
        p2_name = request.form.get('p2_name')
        p2_score = request.form.get('p2_score')
        user_email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Score Submission')
            body = (f'Player 1 - Name: {p1_name}\nPlayer 1 - Score: {p1_score}\nPlayer 2 - Name: {p2_name}\nPlayer 2 - Score: {p2_score}\nYour Email: {user_email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Score submitted successfully!', category='success')
        return redirect('/4-submit_scores')

@app.route('/5-send_scores', methods=['GET','POST'])
def send_scores5():
    leagues = League_Information.query.filter_by(league_number=5)
    if request.method == 'POST':
        p1_name = request.form.get('p1_name')
        p1_score = request.form.get('p1_score')
        p2_name = request.form.get('p2_name')
        p2_score = request.form.get('p2_score')
        user_email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Score Submission')
            body = (f'Player 1 - Name: {p1_name}\nPlayer 1 - Score: {p1_score}\nPlayer 2 - Name: {p2_name}\nPlayer 2 - Score: {p2_score}\nYour Email: {user_email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Score submitted successfully!', category='success')
        return redirect('/5-submit_scores')


# >>>>  SENDING SIGN UP <<<<

@app.route('/1-send_info', methods=['GET','POST'])
def send_info1():
    leagues = League_Information.query.filter_by(league_number=1)
    if request.method == 'POST':
        full_name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Sign Up Inquiry')
            body = (f'Full Name: {full_name}\nPhone Number: {phone_number}\nEmail: {email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Message sent successfully!', category='success')
        return redirect('/1-sign_up')

@app.route('/2-send_info', methods=['GET','POST'])
def send_info2():
    leagues = League_Information.query.filter_by(league_number=2)
    if request.method == 'POST':
        full_name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Sign Up Inquiry')
            body = (f'Full Name: {full_name}\nPhone Number: {phone_number}\nEmail: {email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Message sent successfully!', category='success')
        return redirect('/2-sign_up')

@app.route('/3-send_info', methods=['GET','POST'])
def send_info3():
    leagues = League_Information.query.filter_by(league_number=3)
    if request.method == 'POST':
        full_name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Sign Up Inquiry')
            body = (f'Full Name: {full_name}\nPhone Number: {phone_number}\nEmail: {email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Message sent successfully!', category='success')
        return redirect('/3-sign_up')

@app.route('/4-send_info', methods=['GET','POST'])
def send_info4():
    leagues = League_Information.query.filter_by(league_number=4)
    if request.method == 'POST':
        full_name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Sign Up Inquiry')
            body = (f'Full Name: {full_name}\nPhone Number: {phone_number}\nEmail: {email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Message sent successfully!', category='success')
        return redirect('/4-sign_up')

@app.route('/5-send_info', methods=['GET','POST'])
def send_info5():
    leagues = League_Information.query.filter_by(league_number=5)
    if request.method == 'POST':
        full_name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Sign Up Inquiry')
            body = (f'Full Name: {full_name}\nPhone Number: {phone_number}\nEmail: {email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Message sent successfully!', category='success')
        return redirect('/5-sign_up')


# >>>> SENDING INFORMATION REQUESTS <<<<

@app.route('/1-send_info_request', methods=['GET','POST'])
def sent_request_info1():
    leagues = League_Information.query.filter_by(league_number=1)
    if request.method == 'POST':
        full_name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Information Request')
            body = (f'Full Name: {full_name}\nPhone Number: {phone_number}\nEmail: {email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Message sent successfully!', category='success')
        return redirect('/1-request_info')

@app.route('/2-send_info_request', methods=['GET','POST'])
def sent_request_info2():
    leagues = League_Information.query.filter_by(league_number=2)
    if request.method == 'POST':
        full_name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Information Request')
            body = (f'Full Name: {full_name}\nPhone Number: {phone_number}\nEmail: {email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Message sent successfully!', category='success')
        return redirect('/2-request_info')

@app.route('/3-send_info_request', methods=['GET','POST'])
def sent_request_info3():
    leagues = League_Information.query.filter_by(league_number=3)
    if request.method == 'POST':
        full_name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Information Request')
            body = (f'Full Name: {full_name}\nPhone Number: {phone_number}\nEmail: {email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Message sent successfully!', category='success')
        return redirect('/3-request_info')

@app.route('/4-send_info_request', methods=['GET','POST'])
def sent_request_info4():
    leagues = League_Information.query.filter_by(league_number=4)
    if request.method == 'POST':
        full_name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Information Request')
            body = (f'Full Name: {full_name}\nPhone Number: {phone_number}\nEmail: {email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Message sent successfully!', category='success')
        return redirect('/4-request_info')

@app.route('/5-send_info_request', methods=['GET','POST'])
def sent_request_info5():
    leagues = League_Information.query.filter_by(league_number=5)
    if request.method == 'POST':
        full_name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        comments = request.form.get('comments')

        for league in leagues:
            to = league.email
            subject = (f'{league.league_name} - Information Request')
            body = (f'Full Name: {full_name}\nPhone Number: {phone_number}\nEmail: {email}\nComments: {comments}')
            email_alert(subject,body,to)
            flash('Message sent successfully!', category='success')
        return redirect('/5-request_info')


# >>>> SETTING UP LOGIN MANAGER <<<<

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# >>>> ACTUALLY RUNNING THE APP <<<<

if __name__ == '__main__':
    app.run(host='192.168.56.1')