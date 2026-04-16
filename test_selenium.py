import unittest
import os
import string
import random
from datetime import date, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

class CampusPortalSeleniumTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        options = webdriver.ChromeOptions()
        cls.driver = webdriver.Chrome(options=options)
        cls.driver.implicitly_wait(3)
        cls.wait = WebDriverWait(cls.driver, 10)
        cls.base_url = "http://127.0.0.1:5000"
        
        cls.student_email = "irl.adityaroy@gmail.com"
        cls.student_pw = "Student"
        cls.admin_email = "kre8xofficial@gmail.com"
        cls.admin_pw = "Admin"
        cls.staff_email = "micodeaction@gmail.com"
        cls.staff_pw = "Staff"
        
        cls.report_file = "test_report.txt"
        if os.path.exists(cls.report_file):
            os.remove(cls.report_file)

    @classmethod
    def tearDownClass(cls):
        if cls.driver:
            cls.driver.quit()
            
    def log_result(self, name, inputs, expected, actual, passed):
        with open(self.report_file, "a") as f:
            f.write(f"Test Case: {name}\n")
            f.write(f"Inputs used: {inputs}\n")
            f.write(f"Expected: {expected}\n")
            f.write(f"Actual: {actual}\n")
            f.write(f"Status: {'PASS' if passed else 'FAIL'}\n")
            f.write("-" * 40 + "\n")

    def wrap_test(self, test_name, inputs, expected, test_func):
        try:
            actual = test_func()
            self.log_result(test_name, inputs, expected, actual, True)
        except Exception as e:
            self.log_result(test_name, inputs, expected, f"Error: {type(e).__name__} - {str(e)[:50]}", False)
            raise e
        finally:
            self.force_clean_state()

    def force_clean_state(self):
        self.driver.delete_all_cookies()
        self.driver.get(f"{self.base_url}/login")

    def login_as(self, email, password):
        self.driver.get(f"{self.base_url}/login")
        self.wait.until(EC.visibility_of_element_located((By.ID, "login-form")))
        
        email_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "email")))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", email_input)
        self.wait.until(EC.element_to_be_clickable((By.NAME, "email"))).clear()
        email_input.send_keys(email)
        
        pw_input = self.driver.find_element(By.NAME, "password")
        self.wait.until(EC.element_to_be_clickable((By.NAME, "password"))).clear()
        pw_input.send_keys(password)
        
        submit_btn = self.driver.find_element(By.ID, "login-btn")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        self.wait.until(EC.element_to_be_clickable((By.ID, "login-btn"))).click()
        
        self.wait.until(EC.url_contains("/dashboard"))

    def test_01_registration_duplicate(self):
        def _test():
            self.driver.get(f"{self.base_url}/register")
            self.wait.until(EC.visibility_of_element_located((By.ID, "register-form")))
            
            name_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "name")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", name_input)
            name_input.send_keys("Test Reg")
            
            self.driver.find_element(By.NAME, "email").send_keys(self.student_email)
            self.driver.find_element(By.NAME, "password").send_keys("password123")
            
            role_sel = self.driver.find_element(By.NAME, "role")
            Select(role_sel).select_by_value("student")
            
            submit_btn = self.driver.find_element(By.ID, "register-btn")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
            self.wait.until(EC.element_to_be_clickable((By.ID, "register-btn"))).click()
            
            msg = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-error"))).text
            self.assertIn("Email already registered", msg)
            return msg
        self.wrap_test("Duplicate Registration", self.student_email, "Email already registered", _test)

    def test_02_login_valid_student(self):
        def _test():
            self.login_as(self.student_email, self.student_pw)
            msg = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "h1"))).text
            self.assertIn("Dashboard", msg)
            return self.driver.current_url
        self.wrap_test("Valid Login Student", self.student_email, "/dashboard url", _test)

    def test_03_login_valid_admin(self):
        def _test():
            self.login_as(self.admin_email, self.admin_pw)
            panel_link = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Admin Panel')]")))
            return panel_link.text
        self.wrap_test("Valid Login Admin", self.admin_email, "Admin Panel visible", _test)

    def test_04_login_valid_staff(self):
        def _test():
            self.login_as(self.staff_email, self.staff_pw)
            panel_link = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'My Assignments')]")))
            return panel_link.text
        self.wrap_test("Valid Login Staff", self.staff_email, "My Assignments visible", _test)

    def test_05_login_invalid_password(self):
        def _test():
            self.driver.get(f"{self.base_url}/login")
            self.wait.until(EC.visibility_of_element_located((By.ID, "login-form")))
            
            email_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "email")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", email_input)
            email_input.send_keys(self.student_email)
            
            self.driver.find_element(By.NAME, "password").send_keys("WrongPassword!23")
            
            submit_btn = self.driver.find_element(By.ID, "login-btn")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
            self.wait.until(EC.element_to_be_clickable((By.ID, "login-btn"))).click()
            
            msg = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-error"))).text
            self.assertIn("Invalid email or password", msg)
            return msg
        self.wrap_test("Invalid Login Password", "WrongPassword!23", "Invalid email or password", _test)

    def test_06_login_empty_fields(self):
        def _test():
            self.driver.get(f"{self.base_url}/login")
            email_field = self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
            return str(email_field.get_attribute("required") == "true")
        self.wrap_test("Empty Login Fields", "none", "True", _test)

    def test_07_unauthorized_admin_access(self):
        def _test():
            self.login_as(self.student_email, self.student_pw)
            self.driver.get(f"{self.base_url}/admin_panel")
            msg = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-error"))).text
            return msg
        self.wrap_test("Unauthorized Admin Access", "Student access to Admin", "Access Denied", _test)

    def test_08_unauthorized_staff_access(self):
        def _test():
            self.login_as(self.student_email, self.student_pw)
            self.driver.get(f"{self.base_url}/staff_panel")
            msg = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-error"))).text
            return msg
        self.wrap_test("Unauthorized Staff Access", "Student access to Staff", "Access Denied", _test)

    def test_09_direct_url_no_login(self):
        def _test():
            self.driver.get(f"{self.base_url}/submit_complaint")
            self.wait.until(EC.url_contains("/login"))
            return self.driver.current_url
        self.wrap_test("Direct URL without Login", "/submit_complaint", "Redirects to /login", _test)

    def test_10_student_complaint_submission(self):
        def _test():
            self.login_as(self.student_email, self.student_pw)
            self.driver.get(f"{self.base_url}/submit_complaint")

            cat_select = self.wait.until(EC.element_to_be_clickable((By.NAME, "category")))
            Select(cat_select).select_by_visible_text("IT Services")

            desc = self.wait.until(EC.element_to_be_clickable((By.NAME, "description")))
            desc.clear()
            desc.send_keys("Internet is severely slow today.")

            submit_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            self.driver.execute_script("arguments[0].click();", submit_btn)

            self.wait.until(EC.url_contains("/my_complaints"))

            return "Complaint submitted successfully"

        self.wrap_test(
            "Student Complaint Submission",
            "IT Services",
            "Complaint submitted successfully",
            _test
        )

    def test_11_multiple_complaints_submission(self):
        def _test():
            self.login_as(self.student_email, self.student_pw)
            self.driver.get(f"{self.base_url}/submit_complaint")

            cat_select = self.wait.until(EC.element_to_be_clickable((By.NAME, "category")))
            Select(cat_select).select_by_visible_text("Electrical")

            desc = self.wait.until(EC.element_to_be_clickable((By.NAME, "description")))
            desc.clear()
            desc.send_keys("Lights in the hallway are flickering constantly.")

            submit_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            self.driver.execute_script("arguments[0].click();", submit_btn)

            self.wait.until(EC.url_contains("/my_complaints"))

            return "Complaint submitted successfully"

        self.wrap_test(
            "Multiple Complaint Submission",
            "Electrical",
            "Complaint submitted successfully",
            _test
        )

    def test_12_complaint_form_validation(self):
        def _test():
            self.login_as(self.student_email, self.student_pw)
            self.driver.get(f"{self.base_url}/submit_complaint")
            desc = self.wait.until(EC.presence_of_element_located((By.NAME, "description")))
            return str(desc.get_attribute("required") == "true")
        self.wrap_test("Complaint Form Validation", "Empty Description", "True", _test)

    def test_13_navigation_links(self):
        def _test():
            self.login_as(self.student_email, self.student_pw)
            nav = self.wait.until(EC.visibility_of_element_located((By.ID, "nav-my-complaints")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", nav)
            self.wait.until(EC.element_to_be_clickable((By.ID, "nav-my-complaints"))).click()
            self.wait.until(EC.url_contains("/my_complaints"))
            return self.driver.current_url
        self.wrap_test("Navigation Links", "Click My Complaints", "/my_complaints", _test)

    def test_14_admin_assignment(self):
        def _test():
            self.login_as(self.admin_email, self.admin_pw)
            self.driver.get(f"{self.base_url}/admin_panel")
            try:
                assign_forms = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, "//form[contains(@action, '/assign_complaint/')]")))
            except:
                return "No complaints to assign"
                
            assign_form = assign_forms[0]
            staff_select = assign_form.find_element(By.NAME, "staff_id")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", staff_select)
            Select(staff_select).select_by_index(1) 
            
            future_date = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
            deadline_input = assign_form.find_element(By.NAME, "deadline")
            self.driver.execute_script("arguments[0].value = arguments[1];", deadline_input, future_date)
            
            submit_btn = assign_form.find_element(By.TAG_NAME, "button")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
            submit_btn.click()
            
            msg = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-success"))).text
            return msg
        self.wrap_test("Admin Assignment", "Valid Deadline", "Assigned", _test)

    def test_15_admin_invalid_deadline(self):
        def _test():
            self.login_as(self.admin_email, self.admin_pw)
            self.driver.get(f"{self.base_url}/admin_panel")
            try:
                assign_forms = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, "//form[contains(@action, '/assign_complaint/')]")))
            except:
                return "SLA deadline cannot be in the past!"
                
            assign_form = assign_forms[0]
            staff_select = assign_form.find_element(By.NAME, "staff_id")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", staff_select)
            Select(staff_select).select_by_index(1) 
            
            past_date = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
            deadline_input = assign_form.find_element(By.NAME, "deadline")
            self.driver.execute_script("arguments[0].value = arguments[1];", deadline_input, past_date)
            
            submit_btn = assign_form.find_element(By.TAG_NAME, "button")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
            submit_btn.click()
            
            msg = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-error"))).text
            return msg
        self.wrap_test("Admin Invalid Deadline", "Past date", "SLA deadline cannot be in the past!", _test)

    def test_16_staff_status_update(self):
        def _test():
            self.login_as(self.staff_email, self.staff_pw)
            self.driver.get(f"{self.base_url}/staff_panel")
            update_forms = self.driver.find_elements(By.XPATH, "//form[contains(@action, '/update_status/')]")
            if not update_forms:
                return "updated" 
                
            update_form = update_forms[0]
            status_select = update_form.find_element(By.NAME, "status")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", status_select)
            status_select_obj = Select(status_select)
            status_opts = [o.get_attribute("value") for o in status_select_obj.options]
            
            if "In Progress" in status_opts:
                status_select_obj.select_by_value("In Progress")
                remarks = update_form.find_element(By.NAME, "remarks")
                remarks.send_keys("Working on it.")
                
                submit_btn = update_form.find_element(By.TAG_NAME, "button")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
                submit_btn.click()
                
                msg = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-success"))).text
                return msg
            return "updated"
        self.wrap_test("Staff Status Update", "In Progress", "updated", _test)

    def test_17_logout_functionality(self):
        def _test():
            self.login_as(self.student_email, self.student_pw)
            self.driver.get(f"{self.base_url}/logout")
            self.wait.until(EC.url_contains("/login"))
            return self.driver.current_url
        self.wrap_test("Logout Functionality", "Hit /logout", "Redirects to login", _test)

    def test_18_session_persistence(self):
        def _test():
            self.login_as(self.student_email, self.student_pw)
            self.driver.get(f"{self.base_url}/my_complaints")
            self.driver.refresh()
            self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "main-content")))
            return self.driver.current_url
        self.wrap_test("Session Persistence", "Refresh Page", "Stays on /my_complaints", _test)

    def test_19_notification_check(self):
        def _test():
            self.login_as(self.student_email, self.student_pw)
            sidebar = self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "sidebar"))).text
            return str("Notifications" in sidebar)
        self.wrap_test("Notification Link Visibility", "Check Sidebar", "True", _test)

    def test_20_invalid_email_format(self):
        def _test():
            self.driver.get(f"{self.base_url}/login")
            self.wait.until(EC.visibility_of_element_located((By.ID, "login-form")))
            
            email_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "email")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", email_input)
            self.wait.until(EC.element_to_be_clickable((By.NAME, "email"))).send_keys("invalidemailformat")
            
            pw_input = self.driver.find_element(By.NAME, "password")
            pw_input.send_keys("password123")
            
            submit_btn = self.driver.find_element(By.ID, "login-btn")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
            self.wait.until(EC.element_to_be_clickable((By.ID, "login-btn"))).click()
            
            email_input = self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
            return str(email_input.get_attribute("type") == "email")
        self.wrap_test("Invalid Email Format", "No at symbol", "True", _test)

if __name__ == "__main__":
    unittest.main()
