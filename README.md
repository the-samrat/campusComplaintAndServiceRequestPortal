# Campus Complaint & Service Request Portal

A Flask-based portal for students and faculty to raise complaints,
admin to assign tasks, and staff to resolve them.

## Features
- Role-based login (Student/Faculty/Admin/Staff)
- Complaint submission & tracking
- Assignment with SLA
- Notifications + Email alerts
- Audit logs + Report export

Setup
git clone https://github.com/the-samrat/Campus-Complaint-Portal.git
cd Campus-Complaint-Portal
pip install -r requirements.txt
python app.py


## Database Setup

1. Open MySQL Workbench  
2. Go to Server → Data Import  
3. Select `database/complaint_portal.sql`  
4. Click Start Import  
5. Database will be created automatically
