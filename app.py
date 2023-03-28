import flask
from flask import Flask, request, session, redirect, url_for, json, render_template, send_from_directory, Response
from flaskext.mysql import MySQL
import pymysql
import re
import os
from datetime import timedelta, datetime
import io
import csv
# from gevent.pywsgi import WSGIServer
from gevent.pywsgi import WSGIServer

from flask import Flask, render_template, jsonify, request
from flask_mysqldb import MySQLdb  # pip install flask-mysqldb https://github.com/alexferl/flask-mysqldb

app = Flask(__name__)

# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = "sarmancode-2023"

mysql = MySQL(app)

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'Dme#aludecor'
app.config['MYSQL_DATABASE_DB'] = 'server_backup'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=15)
    # flask.session.modified = True


# http://localhost:5000/pythonlogin/ - this will be the login page
@app.route('/userlogin/', methods=['GET', 'POST'])
def login():
    # connect
    conn = mysql.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor.execute('SELECT * FROM employee_credential WHERE username = %s AND password = %s', (username, password))
        # Fetch one record and return result
        account = cursor.fetchone()

        # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['fullname'] = account['fullname']

            # Redirect to home page
            # return 'Logged in successfully!'
            return redirect(url_for('home'))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'

    return render_template('loginform.html', msg=msg)


# http://localhost:5000/register - this will be the registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    # connect
    conn = mysql.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'emailid' in request.form:
        # Create variables for easy access
        fullname = request.form['fullname']
        username = request.form['username']
        email = request.form['emailid']
        password = request.form['password']

        # Check if account exists using MySQL
        cursor.execute('SELECT * FROM employee_credential WHERE username = %s', (username))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO employee_credential VALUES ( NULL,%s, %s, %s, %s)',
                           (fullname, username, password, email))
            conn.commit()

            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)


# http://localhost:5000/home - this will be the home page, only accessible for loggedin users
@app.route('/')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        # return render_template('home.html', username=session['username'])
        return render_template('home.html', username=session['username'], fullname=session['fullname'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


# http://localhost:5000/logout - this will be the logout page
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    # Redirect to login page
    return redirect(url_for('login'))


# http://localhost:5000/profile - this will be the profile page, only accessible for loggedin users
@app.route('/profile')
def profile():
    # Check if account exists using MySQL
    conn = mysql.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor.execute('SELECT * FROM employee_credential WHERE username = %s', [session['username']])
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/dailytask', methods=['GET', 'POST'])
def dailytask():
    # Check if account exists using MySQL
    conn = mysql.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    # Check if user is loggedin
    if 'loggedin' in session:
        if request.method == 'GET':
            cursor.execute(
                """SELECT dwm_master.Task_Id,dwm_master.Name,dwm_master.Freq,dwm_master.Task_Name,
dwm_master.Plan_Time,
dwm_completed_master.Actual_Time,dwm_master.Final_Emp_Id
FROM server_backup.dwm_completed_master
RIGHT JOIN server_backup.dwm_master
ON  server_backup.dwm_completed_master.Task_Id= server_backup.dwm_master.Task_Id where dwm_completed_master.Actual_Time is null
AND (server_backup.dwm_master.Final_Emp_Id = %s OR server_backup.dwm_master.Emp_Id = %s)""",
                [session['username'], session['username']])
            employee = cursor.fetchall()
            cursor.execute(
                """Select Final_Emp_Id,name, count(CASE WHEN Freq = 'D' THEN Task_Id ELSE NULL END) AS Daily,
count(CASE WHEN Freq = 'W' THEN Task_Id ELSE NULL END) AS Weekly,
count(CASE WHEN Freq = 'M' THEN Task_Id ELSE NULL END) AS Monthly,
count(CASE WHEN Freq = 'Q' THEN Task_Id ELSE NULL END) AS Quaterly,
count(CASE WHEN Freq = 'Y' THEN Task_Id ELSE NULL END) AS Yearly,
count(Task_Id) AS Total FROM (SELECT dwm_master.Task_Id,dwm_master.Name,dwm_master.Freq,dwm_master.Task_Name,
dwm_master.Plan_Time,dwm_completed_master.user_status,dwm_completed_master.user_remarks,
dwm_completed_master.Actual_Time,dwm_master.Final_Emp_Id
FROM server_backup.dwm_completed_master
RIGHT JOIN server_backup.dwm_master
ON  server_backup.dwm_completed_master.Task_Id= server_backup.dwm_master.Task_Id where dwm_completed_master.Actual_Time is null) as final_table 
where Final_Emp_Id = %s
  GROUP BY Final_Emp_Id,Name order by Final_Emp_Id""",
                [session['username']])
            context = cursor.fetchall()
            return render_template('daily_checklist.html', username=session['username'], employee=employee,
                                   context=context)
        elif request.method == 'POST':
            if 'loggedin' in session:
                form_data = request.form.to_dict()
                task_id = form_data['task_id']
                status = form_data['status']
                remarks = form_data['remarks']
                conn = mysql.connect()
                cur = conn.cursor(pymysql.cursors.DictCursor)
                cur.execute("""
                    Insert into server_backup.dwm_completed_master (Task_Id, Name, Freq,Task_Name, Plan_Time, Actual_Time, 
                    user_status, user_remarks,Submitted_by_E_code,HOD_Emp_Id,Others_Emp_Id) SELECT Task_Id,Name, Freq, 
                    Task_Name, Plan_Time, now(),%s, %s, %s,HOD_Emp_Id, Others_Emp_Id
                    from server_backup.dwm_master where Task_Id=%s""",
                            (status, remarks, session['username'], task_id))
                conn.commit()
                cur.close()
                # return json.dumps({'status': 'OK'})
                return redirect(url_for('dailytask'))
            # User is not loggedin redirect to login page
            return redirect(url_for('login'))
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


##No Work Dashboard
@app.route('/')
def mainn():
    return redirect('/nowork')


@app.route('/nowork', methods=['GET'])
def nowork():
    # Check if account exists using MySQL
    conn = mysql.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Check if user is loggedin
    if 'loggedin' in session:
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        # cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        result = cur.execute(
            "SELECT Task_Id, Name, Freq, Task_Name, Plan_Time, user_status from dwm_completed_master WHERE user_status ='No Work' AND HOD_status is Null AND HOD_Emp_Id = %s",
            [session['username']])
        nowork = cur.fetchall()
        # conn = mysql.connect()
        # cur = conn.cursor(pymysql.cursors.DictCursor)
        # # cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # result = cur.execute("Select Final_Emp_Id,HOD_Emp_Id,name,count(CASE WHEN Freq = 'D' THEN Task_Id ELSE NULL END) AS Daily,count(CASE WHEN Freq = 'W' THEN Task_Id ELSE NULL END) AS Weekly,count(CASE WHEN Freq = 'M' THEN Task_Id ELSE NULL END) AS Monthly,count(CASE WHEN Freq = 'Q' THEN Task_Id ELSE NULL END) AS Quaterly,count(CASE WHEN Freq = 'Y' THEN Task_Id ELSE NULL END) AS Yearly,count(Task_Id) AS Total FROM server_backup.dwm_master WHERE user_status ='No Work' and HOD_Emp_Id = %s GROUP BY HOD_Emp_Id,Final_Emp_Id,name order by HOD_Emp_Id ",[session['username']])
        # summary = cur.fetchall()
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        # cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        result = cur.execute(
            "Select Submitted_by_E_code,HOD_Emp_Id,name,count(CASE WHEN Freq = 'D' THEN Task_Id ELSE NULL END) AS Daily,count(CASE WHEN Freq = 'W' THEN Task_Id ELSE NULL END) AS Weekly,count(CASE WHEN Freq = 'M' THEN Task_Id ELSE NULL END) AS Monthly,count(CASE WHEN Freq = 'Q' THEN Task_Id ELSE NULL END) AS Quaterly,count(CASE WHEN Freq = 'Y' THEN Task_Id ELSE NULL END) AS Yearly,count(Task_Id) AS Total FROM server_backup.dwm_completed_master WHERE user_status ='No Work' and HOD_status is Null and HOD_Emp_Id = %s GROUP BY HOD_Emp_Id,Submitted_by_E_code,name order by HOD_Emp_Id ",
            [session['username']])
        summary = cur.fetchall()
        return render_template('hod_dashboard.html', summary=summary, nowork=nowork, username=session['username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/updatestatus', methods=['POST'])
def updatestatus():
    # Check if user is loggedin
    if 'loggedin' in session:
        pk = request.form['pk']
        name = request.form['name']
        value = request.form['value']
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        if name == 'Status':
            cur.execute(
                "UPDATE dwm_completed_master SET HOD_status = %s , HOD_Action_Time = now(), Hod_Submitted_by_E_code = %s WHERE Task_Id = %s ",
                (value, session['username'], pk))
        elif name == 'Remarks':
            cur.execute("UPDATE dwm_completed_master SET HOD_remarks = %s WHERE Task_Id = %s ", (value, pk))
        conn.commit()
        cur.close()
        return json.dumps({'status': 'OK'})
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


# DWM Pending Dashboard Report
@app.route('/dwmpendingreport', methods=['GET'])
def dwmpendingreport():
    # Check if account exists using MySQL
    conn = mysql.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Check if user is loggedin
    if 'loggedin' in session:
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        # cursor = mysql.connection.cursor()
        # cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""SELECT p1.Dept,p2.Task_Id,p1.Name,p2.Freq,p2.Task_Name,p2.Plan_Time FROM server_backup.dwm_master AS p2 
        INNER JOIN fms_scm.employee_active As p1 ON p2.Final_Emp_Id = p1.E_Code WHERE p2.Task_Id 
        not in (select Task_Id from server_backup.dwm_completed_master) and (p2.Others_Emp_Id like %s 
        OR p2.HOD_Emp_Id like %s OR p2.Final_Emp_Id like %s 
        OR p2.Emp_Id like %s)""", [f"%{session['username']}%", f"%{session['username']}%",
                                   f"%{session['username']}%", f"%{session['username']}%"])
        pcdata = cur.fetchall()
        cur.execute("""
        select ea.Dept, dm.Emp_Id,dm.Name,
    count(CASE WHEN dm.Freq = 'D' THEN dm.Freq ELSE NULL END) AS D,
    count(CASE WHEN dm.Freq = 'W' THEN dm.Freq ELSE NULL END) AS W,
    count(CASE WHEN dm.Freq = 'M' THEN dm.Freq ELSE NULL END) AS M,
    count(CASE WHEN dm.Freq = 'Y' THEN dm.Freq ELSE NULL END) AS Y,
    count(dm.Emp_Id) AS Total_Task
    FROM server_backup.dwm_master as dm left join fms_scm.employee_active as ea 
    on dm.Emp_Id = ea.E_Code where dm.task_id not in (select dc.task_id from 
    server_backup.dwm_completed_master as dc) 
    and (dm.Others_Emp_Id like %s 
        OR dm.HOD_Emp_Id like %s OR dm.Final_Emp_Id like %s 
        OR dm.Emp_Id like %s)
    GROUP BY ea.Dept, dm.Emp_Id, dm.Name """, [f"%{session['username']}%", f"%{session['username']}%",
                                               f"%{session['username']}%", f"%{session['username']}%"])
        pcdatacount = cur.fetchall()
        return render_template('dwm_pending_report.html', pcdata=pcdata, pcdatacount=pcdatacount)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


# Report Download Form
@app.route('/downloadreport', methods=['GET', 'POST'])
def downloadreport():
    try:
        # Check if account exists using MySQL
        conn = mysql.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # Check if user is loggedin
        if 'loggedin' in session:
            if request.method == 'GET':
                logo = '/static/Logo.png'
                body = '/static/body.jpg'
                return render_template('report_download_form.html', username=session['username'], logo=logo, body=body)
            elif request.method == 'POST':
                form_data = request.form.to_dict()
                report_name = form_data['reportname']
                # start_date = form_data['startdate']
                # end_date = form_data['enddate']
                session['report_name'] = report_name
                return redirect(url_for('downloadcsvreport'))

        # User is not loggedin redirect to login page
        return redirect(url_for('login'))
    except Exception as e:
        print(e)


# CSV Report Download
@app.route('/downloadreport/download')
def downloadcsvreport():
    # Check if account exists using MySQL
    conn = mysql.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    # Check if user is loggedin
    if 'loggedin' in session:
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        if session['report_name'] == 'Pending DWM Report':
            session['report_name'] = 'NA'
            report_generate_time = datetime.strftime(datetime.now(), "%d-%m-%Y %I.%M.%S %p")
            cur.execute("""SELECT p1.Dept,p2.Task_Id,p1.Name,p2.Freq,p2.Task_Name,p2.Plan_Time FROM 
                                    server_backup.dwm_master AS p2 
                                    INNER JOIN fms_scm.employee_active As p1 ON p2.Final_Emp_Id = p1.E_Code WHERE p2.Task_Id 
                                    not in (select Task_Id from server_backup.dwm_completed_master) and (p2.Others_Emp_Id like %s 
                                    OR p2.HOD_Emp_Id like %s OR p2.Final_Emp_Id like %s 
                                    OR p2.Emp_Id like %s)""", [f"%{session['username']}%", f"%{session['username']}%",
                                                               f"%{session['username']}%", f"%{session['username']}%"])
            download_data = cur.fetchall()
            output = io.StringIO()
            writer = csv.writer(output)
            line = ['Department', 'Name', 'Task Id', 'Task Name', 'Freq', 'Plan Time']
            writer.writerow(line)
            for row in download_data:
                line = [row['Dept'], row['Name'], row['Task_Id'], row['Task_Name'], row['Freq'], row['Plan_Time']]
                writer.writerow(line)

            output.seek(0)
            return Response(
                output, mimetype="text/csv",
                headers={
                    "Content-Disposition": f"attachment;filename=Pending DWM Report as on {report_generate_time}.csv"}
            )
        elif session['report_name'] == 'Completed DWM Report':
            session['report_name'] = 'NA'
            report_generate_time = datetime.strftime(datetime.now(), "%d-%m-%Y %I.%M.%S %p")
            cur.execute(""" 
                            select ea.Dept, cd.Task_Id, cd.Name, cd.Freq, cd.Task_Name, cd.Plan_Time, 
                            cd.Actual_Time,
                            if(
                            SEC_TO_TIME(TIME_TO_SEC(timediff(date_format(cd.Actual_Time, '%%Y-%%m-%%d'), 
                            str_to_date(cd.Plan_Time, '%%d/%%m/%%Y')))) = '00:00:00', null, 
                            SEC_TO_TIME(TIME_TO_SEC(timediff(date_format(cd.Actual_Time, '%%Y-%%m-%%d'), 
                            str_to_date(cd.Plan_Time, '%%d/%%m/%%Y'))))
                            ) as Time_Delay, 
                            cd.user_status, cd.user_remarks, cd.Submitted_by_E_code, 
                            ea.Name as Submitted_by_Name from 
                            server_backup.dwm_completed_master as cd left join 
                            fms_scm.employee_active as ea on cd.submitted_by_e_code = ea.E_code where 
                            cd.Task_Id is not null and 
                            (cd.Submitted_by_E_code LIKE %s OR 
                            cd.HOD_Emp_Id LIKE %s OR 
                            cd.Others_Emp_Id LIKE %s)
                        """,
                        [f"%{session['username']}%", f"%{session['username']}%",
                         f"%{session['username']}%"])
            download_data = cur.fetchall()
            output = io.StringIO()
            writer = csv.writer(output)
            line = ['Department', 'Name', 'Task Id', 'Task Name', 'Freq', 'Plan Time', 'Actual Time', 'Time Delay',
                    'User Status', 'User Remarks', 'Submitted by E_Code', 'Submitted by E_Name']
            writer.writerow(line)
            for row in download_data:
                line = [row['Dept'], row['Name'], row['Task_Id'], row['Task_Name'], row['Freq'], row['Plan_Time'],
                        row['Actual_Time'], row['Time_Delay'], row['user_status'], row['user_remarks'],
                        row['Submitted_by_E_code'], row['Submitted_by_Name']]
                writer.writerow(line)

            output.seek(0)
            return Response(
                output, mimetype="text/csv",
                headers={
                    "Content-Disposition": f"attachment;filename=Completed DWM Report as on {report_generate_time}.csv"}
            )

        else:
            return redirect(url_for('downloadreport'))
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


# Change Password Form
@app.route('/changepassword', methods=['GET', 'POST'])
def changepassword():
    try:
        # Check if account exists using MySQL
        conn = mysql.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # Check if user is loggedin
        if 'loggedin' in session:
            if request.method == 'GET':
                logo = '/static/Logo.png'
                # body = '/static/body.jpg'
                message = ''
                return render_template('change_Password_form.html', username=session['username'], logo=logo,
                                       message=message)
            elif request.method == 'POST':
                cur = conn.cursor(pymysql.cursors.DictCursor)
                form_data = request.form.to_dict()
                new_pwd = form_data['newpwd']
                confrim_pwd = form_data['confirmpwd']
                # username = session['username']
                message = ''
                if new_pwd == confrim_pwd:
                    cur.execute("""
                    Update server_backup.employee_credential set password = %s where username = %s;
                    """, [new_pwd, session['username']])
                    conn.commit()
                    message = 'Password has been changed successfully.'
                    logo = '/static/Logo.png'
                    return render_template('change_Password_form.html', username=session['username'], logo=logo,
                                           message=message)

        # User is not loggedin redirect to login page
        return redirect(url_for('login'))
    except Exception as e:
        print(e)


# ----------------------------------- FMS Project ----------------------------------------
# FMS: SCM Home Page
@app.route('/fms_scm_home')
def fms_scm_home():
    # Check if account exists using MySQL
    conn = mysql.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        # cursor.execute('SELECT * FROM employee_credential WHERE username = %s', [session['username']])
        # account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('fms_scm_home.html', username=session['username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


# FMS: SCM ZH/SH Approval
@app.route('/fms_scm_rh_gm_approval', methods=['GET', 'POST'])
def fms_scm_rh_gm_approval():
    # Check if account exists using MySQL
    conn = mysql.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        if request.method == 'GET':
            # cursor.execute('SELECT * FROM employee_credential WHERE username = %s', [session['username']])
            cursor.execute(
                """SELECT SO_No, Customer_Name, Planned_Time, Branch_Name, Inter_Branch_Name from fms_scm.collect_receipt 
                where SO_No not in (select SO_No from fms_scm.rh_gm_approval where SO_No is not null) limit 20""")
            rh_gm_data = cursor.fetchall()
            # print(rh_gm_data)
            # Show the profile page with account info
            return render_template('fms_scm_rh_gm_approval.html', username=session['username'], rh_gm_data=rh_gm_data)
        elif request.method == 'POST':
            # Check if user is loggedin
            if 'loggedin' in session:
                form_data = request.form.to_dict()
                print(form_data)
                so_no = form_data['so_no']
                print(so_no)
                status = form_data['status']
                print(status)
                remarks = form_data['remarks']
                print(remarks)
                conn = mysql.connect()
                cur = conn.cursor(pymysql.cursors.DictCursor)
                cur.execute("""
                    Insert into fms_scm.rh_gm_approval (SO_No, Customer_Name, Branch_Name,
                Inter_Branch_Name, Planned_Time, Actual_Time, Status, Remarks, Submitted_by_E_code) SELECT SO_No,
                Customer_Name, Branch_Name, Inter_Branch_Name, Planned_Time, now(), %s, %s,
                %s from fms_scm.collect_receipt where SO_No=%s""",
                            (status, remarks, session['username'], so_no))
                conn.commit()
                cur.close()
                # return json.dumps({'status': 'OK'})
                return redirect(url_for('fms_scm_rh_gm_approval'))
            # User is not loggedin redirect to login page
            return redirect(url_for('login'))
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True,host='127.0.0.1', port=5001)
