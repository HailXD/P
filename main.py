import csv
import datetime

class User:
    """
    Base class for all users (Applicant, HDBOfficer, HDBManager).
    """
    def __init__(self, user_id, password, age, marital_status, name):
        self.userID = user_id
        self.password = password
        self.age = age
        self.marital_status = marital_status
        self.name = name

    def changePassword(self, new_password):
        self.password = new_password
        print("Password changed successfully.")

    def viewProjects(self, projects):
        """
        Default: show all projects (including hidden).
        Subclasses can override or filter if desired.
        """
        print("==== All Projects ====")
        for p in projects:
            p.displayInfo()


class Applicant(User):
    """
    Applicant extends User.
    """
    def __init__(self, user_id, password, age, marital_status, name):
        super().__init__(user_id, password, age, marital_status, name)
        self.applications = []
        self.enquiries = []

    def applyForProject(self, project, flat_type, application_controller):
        """
        Singles (35+ years) can ONLY apply for 2-Room.
        Married (21+ years) can apply for 2-Room or 3-Room.
        Cannot apply for multiple projects at once (only one active application).
        """
        active_app = [app for app in self.applications 
                      if app.applicationStatus in ["Pending","Successful"]]
        if active_app:
            print("You already have an active application. Cannot apply again.")
            return

        if self.marital_status.lower() == "single":
            if self.age < 35:
                print("Single applicants must be at least 35 years old.")
                return
            if flat_type != "2-Room":
                print("Single (≥35) can ONLY apply for 2-Room.")
                return
        else:
            if self.age < 21:
                print("Married applicants must be at least 21 years old.")
                return
            if flat_type not in ["2-Room", "3-Room"]:
                print("Married applicants can apply for 2-Room or 3-Room only.")
                return

        if project.flatTypes[flat_type]["units"] <= 0:
            print(f"No available units for {flat_type} in project '{project.projectName}'.")
            return

        app = Application(self, project, flat_type)
        application_controller.createApplication(app)
        self.applications.append(app)
        print(f"Application for '{project.projectName}' as {flat_type} submitted (Pending).")

    def viewApplicationStatus(self):
        if not self.applications:
            print("You have no applications.")
            return
        print("==== Your BTO Applications ====")
        for app in self.applications:
            print(f"- Project: {app.BTOProject.projectName} "
                  f"| Status: {app.applicationStatus} "
                  f"| Flat Type: {app.chosen_flat_type}")

    def requestWithdrawal(self):
        """
        Request to withdraw from an existing application (if it exists).
        This will be approved or rejected by the HDB Manager later.
        """
        if not self.applications:
            print("No applications to withdraw.")
            return
        
        print("Select an application to request withdrawal:")
        for idx, app in enumerate(self.applications):
            print(f"{idx+1}. {app.BTOProject.projectName}, Status: {app.applicationStatus}")
        choice = input("Enter choice number: ")
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(self.applications):
                app_to_withdraw = self.applications[choice_idx]
                if app_to_withdraw.applicationStatus in ["Unsuccessful","Booked"]:
                    print("This application is either unsuccessful or booked; cannot withdraw.")
                    return
                app_to_withdraw.requested_withdrawal = True
                print("Withdrawal request submitted. Awaiting Manager's approval.")
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input.")

    def submitEnquiry(self, message, inquiry_controller):
        new_inquiry = Inquiry(self, None, message)
        inquiry_controller.createInquiry(new_inquiry)
        self.enquiries.append(new_inquiry)
        print("Enquiry submitted successfully.")

    def viewEnquiries(self):
        if not self.enquiries:
            print("You have no enquiries.")
            return
        print("==== Your Enquiries ====")
        for i, enq in enumerate(self.enquiries, start=1):
            print(f"{i}. {enq.message}")
            if enq.response:
                print(f"   Response: {enq.response}")

    def deleteEnquiry(self, inquiry_controller):
        if not self.enquiries:
            print("You have no enquiries to delete.")
            return
        print("Select an enquiry to delete:")
        for i, enq in enumerate(self.enquiries, start=1):
            print(f"{i}. {enq.message} (Response: {enq.response if enq.response else 'None'})")
        choice = input("Enter choice number: ")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.enquiries):
                to_remove = self.enquiries[idx]
                inquiry_controller.deleteInquiry(to_remove)
                self.enquiries.remove(to_remove)
                print("Enquiry deleted.")
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input.")

    def viewProjects(self, projects):
        """
        Override to display only the projects that this Applicant is eligible for,
        and that have > 0 units in the relevant flat type(s), and are visible.
        """
        eligible_projects = []

        if self.marital_status.lower() == "single" and self.age < 35:
            print("You are under 35 and single; no projects are eligible.")
            return

        if self.marital_status.lower() != "single" and self.age < 21:
            print("You are under 21 and married; no projects are eligible.")
            return

        if self.marital_status.lower() == "single":
            can_apply_types = ["2-Room"]
        else:
            can_apply_types = ["2-Room", "3-Room"]

        for p in projects:
            if not p.visibility:
                continue

            has_available_type = False
            for t in can_apply_types:
                if t in p.flatTypes and p.flatTypes[t]["units"] > 0:
                    has_available_type = True
                    break

            if has_available_type:
                eligible_projects.append(p)

        if not eligible_projects:
            print("No projects available based on your eligibility and current unit availability.")
            return

        print("==== Eligible Projects ====")
        for p in eligible_projects:
            print(f"[ProjectID={p.projectID}] {p.projectName} | Neighborhood: {p.neighborhood} | Visible: {p.visibility}")
            if p.applicationOpenDate and p.applicationCloseDate:
                print(f"   Application Period: {p.applicationOpenDate} to {p.applicationCloseDate}")
            for ft, info in p.flatTypes.items():
                print(f"   {ft}: {info['units']} units, Price: {info['price']}")
            print()


class HDBOfficer(Applicant):
    """
    HDBOfficer now inherits from Applicant, so it has
    all applicant methods (applyForProject, viewApplicationStatus, etc.)
    plus the extra Officer methods.
    """
    def __init__(self, user_id, password, age, marital_status, name):
        super().__init__(user_id, password, age, marital_status, name)
        self.handling_project = None
        self.registration_status = None
        self.registered_project = None

    def registerToProject(self, project):
        """
        Officer cannot register if:
          - They have already applied for that project as an Applicant
          - Already an HDB Officer (approved) for another project in the same period
        For simplicity, we do a basic check that they are not currently handling any project.
        """
        if self.handling_project:
            print("You are already handling another project. Cannot register.")
            return

        for app in self.applications:
            if app.BTOProject == project:
                print("You have already applied for this project as an Applicant. Cannot register as Officer.")
                return

        self.registered_project = project
        self.registration_status = "Pending"
        print(f"Registration to handle project '{project.projectName}' submitted (Pending).")

    def viewApplicantStatusInProject(self, applicant):
        """
        Officer can check an applicant’s status in the project they handle.
        """
        if not self.handling_project:
            print("You are not handling any project currently.")
            return
        for app in applicant.applications:
            if app.BTOProject == self.handling_project:
                print(f"{applicant.name} has status {app.applicationStatus} in {app.BTOProject.projectName}.")
                return
        print("No application found for this applicant in your project.")

    def updateFlatAvailability(self, project, flat_type, number_booked):
        if self.handling_project != project:
            print("You are not handling this project.")
            return
        project.reduceUnits(flat_type, number_booked)
        print(f"Updated availability for {flat_type} in project '{project.projectName}'.")

    def retrieveApplication(self, applicant_nric, application_controller):
        if not self.handling_project:
            print("You are not handling any project currently.")
            return None
        found_app = application_controller.findApplicationByNRIC_Project(applicant_nric, self.handling_project)
        if found_app:
            print(f"Found application: {found_app.applicant.name}, Status: {found_app.applicationStatus}")
            return found_app
        else:
            print("No application found for that NRIC in this project.")
            return None

    def generateReceipt(self, applicant):
        """
        Generate a booking receipt if applicant’s application is 'Booked'.
        """
        for app in applicant.applications:
            if app.applicationStatus == "Booked":
                print("======== FLAT BOOKING RECEIPT ========")
                print(f"Applicant Name: {applicant.name}")
                print(f"NRIC: {applicant.userID}")
                print(f"Age: {applicant.age}")
                print(f"Marital Status: {applicant.marital_status}")
                print(f"Project Name: {app.BTOProject.projectName}")
                print(f"Flat Type Booked: {app.chosen_flat_type}")
                print("======================================")
                return
        print("No 'Booked' application found for this applicant.")


class HDBManager(User):
    """
    HDBManager extends User.
    """
    def __init__(self, user_id, password, age, marital_status, name):
        super().__init__(user_id, password, age, marital_status, name)
        self.projects_handling = []

    def createBTOProject(self, name, neighborhood, flat_types, open_date, close_date, slot):
        return BTOProject(name, neighborhood, flat_types, open_date, close_date, self, slot)

    def editBTOProject(self, project, new_name=None, new_neighborhood=None, new_flat_types=None):
        if project.manager != self:
            print("You are not the manager of this project.")
            return
        if new_name:
            project.projectName = new_name
        if new_neighborhood:
            project.neighborhood = new_neighborhood
        if new_flat_types:
            project.flatTypes = new_flat_types
        print(f"Project '{project.projectName}' updated successfully.")

    def toggleProjectVisibility(self, project, isVisible):
        if project.manager != self:
            print("You are not the manager of this project.")
            return
        project.visibility = isVisible
        print(f"Project '{project.projectName}' visibility set to {isVisible}.")

    def approveOrRejectApplication(self, application, decision):
        if application.BTOProject.manager != self:
            print("You are not the manager of this project.")
            return
        if application.applicationStatus != "Pending":
            print("This application is not Pending. Cannot approve/reject.")
            return

        if decision:
            ft = application.chosen_flat_type
            if application.BTOProject.flatTypes[ft]["units"] > 0:
                application.updateStatus("Successful")
                print(f"Application for {application.applicant.name} approved.")
            else:
                print("Not enough units left for that flat type! Cannot approve.")
        else:
            application.updateStatus("Unsuccessful")
            print(f"Application for {application.applicant.name} rejected.")

    def approveOrRejectWithdrawal(self, application, decision):
        if application.BTOProject.manager != self:
            print("You are not the manager of this project.")
            return
        if not application.requested_withdrawal:
            print("No withdrawal requested.")
            return

        if decision:
            if application.applicationStatus in ["Pending","Successful"]:
                application.updateStatus("Unsuccessful")
                application.requested_withdrawal = False
                print("Withdrawal approved. Application set to 'Unsuccessful'.")
            else:
                print("Application cannot be withdrawn from this state.")
        else:
            application.requested_withdrawal = False
            print("Withdrawal request rejected.")

    def approveOrRejectHDBOfficerRegistration(self, officer, decision):
        if not officer.registered_project:
            print("Officer has no project registration pending.")
            return
        project = officer.registered_project
        if project.manager != self:
            print("You are not the manager of this project.")
            return
        if officer.registration_status != "Pending":
            print("Officer's registration is not pending.")
            return

        if decision:
            if len(project.officers) >= project.officerSlot:
                print("No more officer slots available.")
                return
            project.officers.append(officer)
            officer.handling_project = project
            officer.registration_status = "Approved"
            print(f"Officer {officer.name} approved for '{project.projectName}'.")
        else:
            officer.registration_status = "Rejected"
            print(f"Officer {officer.name} rejected for '{project.projectName}'.")

    def generateApplicantReport(self, applications):
        print("=== Applicant Report (Booked Applications) ===")
        for app in applications:
            if app.applicationStatus == "Booked":
                print(f"Applicant: {app.applicant.name} ({app.applicant.userID}) | "
                      f"Age: {app.applicant.age} | Marital: {app.applicant.marital_status} | "
                      f"Project: {app.BTOProject.projectName} | Flat Type: {app.chosen_flat_type}")


class BTOProject:
    project_counter = 1

    def __init__(self, project_name, neighborhood, flat_types,
                 open_date, close_date, manager, officerSlot):
        self.projectID = BTOProject.project_counter
        BTOProject.project_counter += 1
        self.projectName = project_name
        self.neighborhood = neighborhood
        self.flatTypes = flat_types
        self.applicationOpenDate = open_date
        self.applicationCloseDate = close_date
        self.manager = manager
        self.officers = []
        self.visibility = True
        self.officerSlot = officerSlot

    def toggleVisibility(self, isVisible):
        self.visibility = isVisible

    def registerHDBOfficer(self, officer):
        if len(self.officers) < self.officerSlot:
            self.officers.append(officer)
        else:
            print("No slots left for this project.")

    def reduceUnits(self, flat_type, num):
        if flat_type in self.flatTypes:
            self.flatTypes[flat_type]["units"] -= num
            if self.flatTypes[flat_type]["units"] < 0:
                self.flatTypes[flat_type]["units"] = 0

    def displayInfo(self):
        print(f"[ProjectID={self.projectID}] {self.projectName} | Neighborhood: {self.neighborhood} | Visible: {self.visibility}")
        if self.applicationOpenDate and self.applicationCloseDate:
            print(f"   Application Period: {self.applicationOpenDate} to {self.applicationCloseDate}")
        for ft, info in self.flatTypes.items():
            print(f"   {ft}: {info['units']} units, Price: {info['price']}")
        print()


class Application:
    """
    BTO Application linking Applicant to Project
    """
    def __init__(self, applicant, BTOProject, chosen_flat_type):
        self.applicant = applicant
        self.BTOProject = BTOProject
        self.applicationStatus = "Pending"
        self.chosen_flat_type = chosen_flat_type
        self.requested_withdrawal = False

    def updateStatus(self, new_status):
        self.applicationStatus = new_status


class Inquiry:
    """
    Inquiry from Applicant.
    """
    def __init__(self, applicant, officer, message):
        self.applicant = applicant
        self.officer = officer
        self.message = message
        self.response = None

    def reply(self, response):
        self.response = response


class ApplicationController:
    def __init__(self):
        self.applications = []

    def createApplication(self, app):
        self.applications.append(app)

    def findApplicationByNRIC_Project(self, nric, project):
        for app in self.applications:
            if app.applicant.userID == nric and app.BTOProject == project:
                return app
        return None


class InquiryController:
    def __init__(self):
        self.inquiries = []

    def createInquiry(self, inquiry):
        self.inquiries.append(inquiry)

    def deleteInquiry(self, inquiry):
        if inquiry in self.inquiries:
            self.inquiries.remove(inquiry)

    def getAllInquiries(self):
        return self.inquiries

    def replyInquiry(self, inquiry, response):
        inquiry.reply(response)


class ProjectController:
    def __init__(self):
        self.projects = []

    def addProject(self, project):
        self.projects.append(project)

    def findProjectByID(self, pid):
        for p in self.projects:
            if p.projectID == pid:
                return p
        return None


def parse_date(date_str):
    """Expect YYYY-MM-DD. Return date or None if invalid."""
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None

def load_applicants(filename):
    """Load Applicant data from CSV -> List[Applicant]."""
    applicants = []
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Name"]
            nric = row["NRIC"]
            age = int(row["Age"])
            m_status = row["Marital Status"]
            password = row["Password"]
            applicants.append(Applicant(nric, password, age, m_status, name))
    return applicants

def load_managers(filename):
    """Load HDBManager data from CSV -> List[HDBManager]."""
    managers = []
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Name"]
            nric = row["NRIC"]
            age = int(row["Age"])
            m_status = row["Marital Status"]
            password = row["Password"]
            managers.append(HDBManager(nric, password, age, m_status, name))
    return managers

def load_officers(filename):
    """
    Load HDBOfficer data from CSV -> List[HDBOfficer].
    Note that HDBOfficer extends Applicant in this code.
    """
    officers = []
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Name"]
            nric = row["NRIC"]
            age = int(row["Age"])
            m_status = row["Marital Status"]
            password = row["Password"]
            officers.append(HDBOfficer(nric, password, age, m_status, name))
    return officers

def load_projects(filename, manager_list, officer_list):
    projects = []
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pname = row["Project Name"]
            neighborhood = row["Neighborhood"]
            t1 = row["Type 1"]
            t1_units = int(row["Number of units for Type 1"])
            t1_price = int(row["Selling price for Type 1"])
            t2 = row["Type 2"]
            t2_units = int(row["Number of units for Type 2"])
            t2_price = int(row["Selling price for Type 2"])
            open_date = parse_date(row["Application opening date"])
            close_date = parse_date(row["Application closing date"])
            manager_str = row["Manager"]
            slot = int(row["Officer Slot"])
            officer_str = row["Officer"]

            manager_obj = None
            for m in manager_list:
                if m.name == manager_str or m.userID == manager_str:
                    manager_obj = m
                    break

            ft_dict = {
                t1: {"units": t1_units, "price": t1_price},
                t2: {"units": t2_units, "price": t2_price}
            }
            new_project = BTOProject(pname, neighborhood, ft_dict, open_date, close_date, manager_obj, slot)

            if officer_str.strip():
                off_names = [o.strip() for o in officer_str.split(",")]
                for oname in off_names:
                    for off in officer_list:
                        if off.name == oname or off.userID == oname:
                            new_project.officers.append(off)
                            off.handling_project = new_project
                            off.registration_status = "Approved"
            projects.append(new_project)
    return projects


def main():
    print("=== HDB BTO Application System (Python) ===")

    app_controller = ApplicationController()
    inq_controller = InquiryController()
    proj_controller = ProjectController()

    applicants = load_applicants("ApplicantList.csv")
    managers = load_managers("ManagerList.csv")
    officers = load_officers("OfficerList.csv")
    loaded_projects = load_projects("ProjectList.csv", managers, officers)

    for p in loaded_projects:
        proj_controller.addProject(p)

    for p in loaded_projects:
        if p.manager and (p.manager not in p.manager.projects_handling):
            p.manager.projects_handling.append(p)

    all_users = applicants + managers + officers

    def login():
        nric = input("Enter NRIC: ")
        pw = input("Enter Password: ")
        for user in all_users:
            if user.userID == nric and user.password == pw:
                return user
        return None

    def convert_flat_input(user_input):
        if user_input == '2':
            return "2-Room"
        elif user_input == '3':
            return "3-Room"
        else:
            return None

    while True:
        if not globals().get('current_user'):
            print("\n1. Login")
            print("0. Exit")
            choice = input("Choice: ")
            if choice == '1':
                user = login()
                if user:
                    globals()['current_user'] = user
                    print(f"Welcome, {user.name} ({user.__class__.__name__})!")
                else:
                    print("Invalid NRIC or password.")
            elif choice == '0':
                print("Goodbye!")
                break
            else:
                print("Invalid choice.")
        else:
            current_user = globals()['current_user']

            if isinstance(current_user, Applicant) and not isinstance(current_user, HDBOfficer):
                print("\nApplicant Menu")
                print("1. View All Projects")
                print("2. Apply for a Project")
                print("3. View Application Status")
                print("4. Request Application Withdrawal")
                print("5. Submit Enquiry")
                print("6. View My Enquiries")
                print("7. Delete an Enquiry")
                print("8. Change Password")
                print("9. Logout")
                choice = input("Choice: ")
                
                if choice == '1':
                    current_user.viewProjects(proj_controller.projects)
                elif choice == '2':
                    pid = input("Enter Project ID to apply: ")
                    if not pid.isdigit():
                        print("Invalid project ID.")
                        continue
                    project = proj_controller.findProjectByID(int(pid))
                    if not project:
                        print("Project not found.")
                        continue
                    if not project.visibility:
                        print("Project is not visible.")
                        continue
                    today = datetime.date.today()
                    if project.applicationOpenDate and project.applicationCloseDate:
                        if not (project.applicationOpenDate <= today <= project.applicationCloseDate):
                            print("Not within application period.")
                            continue
                    ft_input = input("Enter flat type (2 or 3): ")
                    ft_converted = convert_flat_input(ft_input)
                    if not ft_converted:
                        print("Invalid flat type choice.")
                        continue
                    current_user.applyForProject(project, ft_converted, app_controller)
                
                elif choice == '3':
                    current_user.viewApplicationStatus()
                
                elif choice == '4':
                    current_user.requestWithdrawal()
                
                elif choice == '5':
                    msg = input("Enter enquiry: ")
                    current_user.submitEnquiry(msg, inq_controller)
                
                elif choice == '6':
                    current_user.viewEnquiries()
                
                elif choice == '7':
                    current_user.deleteEnquiry(inq_controller)
                
                elif choice == '8':
                    new_pw = input("Enter new password: ")
                    current_user.changePassword(new_pw)
                
                elif choice == '9':
                    globals()['current_user'] = None
                else:
                    print("Invalid choice.")

            elif isinstance(current_user, HDBOfficer):
                print("\nHDB Officer Menu")
                print("1. View All Projects")
                print("2. Apply for a Project")
                print("3. View My Application Status")
                print("4. Request Application Withdrawal")
                print("5. Submit Enquiry")
                print("6. View My Enquiries")
                print("7. Delete an Enquiry")
                print("8. Register to handle a Project")
                print("9. View an Applicant's Status in My Project")
                print("10. Update Flat Availability")
                print("11. Retrieve an Application by NRIC")
                print("12. Generate Booking Receipt")
                print("13. Change Password")
                print("14. Logout")
                choice = input("Choice: ")

                if choice == '1':
                    current_user.viewProjects(proj_controller.projects)
                elif choice == '2':
                    pid = input("Enter Project ID to apply: ")
                    if not pid.isdigit():
                        print("Invalid project ID.")
                        continue
                    project = proj_controller.findProjectByID(int(pid))
                    if not project:
                        print("Project not found.")
                        continue
                    today = datetime.date.today()
                    if project.applicationOpenDate and project.applicationCloseDate:
                        if not (project.applicationOpenDate <= today <= project.applicationCloseDate):
                            print("Not within application period.")
                            continue
                    ft_input = input("Enter flat type (2 or 3): ")
                    ft_converted = convert_flat_input(ft_input)
                    if not ft_converted:
                        print("Invalid flat type choice.")
                        continue
                    current_user.applyForProject(project, ft_converted, app_controller)

                elif choice == '3':
                    current_user.viewApplicationStatus()

                elif choice == '4':
                    current_user.requestWithdrawal()

                elif choice == '5':
                    msg = input("Enter your enquiry: ")
                    current_user.submitEnquiry(msg, inq_controller)

                elif choice == '6':
                    current_user.viewEnquiries()

                elif choice == '7':
                    current_user.deleteEnquiry(inq_controller)

                elif choice == '8':
                    pid = input("Enter Project ID to register as Officer: ")
                    if not pid.isdigit():
                        print("Invalid project ID.")
                        continue
                    project = proj_controller.findProjectByID(int(pid))
                    if not project:
                        print("Project not found.")
                        continue
                    current_user.registerToProject(project)

                elif choice == '9':
                    anric = input("Enter Applicant NRIC: ")
                    found_applicant = None
                    for a in applicants:
                        if a.userID == anric:
                            found_applicant = a
                            break
                    if found_applicant:
                        current_user.viewApplicantStatusInProject(found_applicant)
                    else:
                        print("Applicant not found.")

                elif choice == '10':
                    if not current_user.handling_project:
                        print("You are not currently assigned to any project.")
                        continue
                    ft_input = input("Enter flat type to update (2 or 3): ")
                    ft_converted = convert_flat_input(ft_input)
                    if not ft_converted:
                        print("Invalid flat type choice.")
                        continue
                    num = input("Enter number of units booked: ")
                    try:
                        nb = int(num)
                        current_user.updateFlatAvailability(current_user.handling_project, ft_converted, nb)
                    except ValueError:
                        print("Invalid number.")

                elif choice == '11':
                    anric = input("Enter Applicant NRIC: ")
                    current_user.retrieveApplication(anric, app_controller)

                elif choice == '12':
                    anric = input("Enter Applicant NRIC to generate receipt: ")
                    found_applicant = None
                    for a in applicants:
                        if a.userID == anric:
                            found_applicant = a
                            break
                    if found_applicant:
                        current_user.generateReceipt(found_applicant)
                    else:
                        print("Applicant not found.")

                elif choice == '13':
                    new_pw = input("Enter new password: ")
                    current_user.changePassword(new_pw)

                elif choice == '14':
                    globals()['current_user'] = None
                else:
                    print("Invalid choice.")

            elif isinstance(current_user, HDBManager):
                print("\nHDB Manager Menu")
                print("1. View All Projects")
                print("2. Create BTO Project")
                print("3. Edit BTO Project")
                print("4. Toggle Project Visibility")
                print("5. Approve/Reject Application")
                print("6. Approve/Reject Withdrawal Request")
                print("7. Approve/Reject Officer Registration")
                print("8. Generate Applicant Report (Booked)")
                print("9. View All Enquiries")
                print("10. Reply to an Enquiry")
                print("11. Change Password")
                print("12. Logout")
                choice = input("Choice: ")

                if choice == '1':
                    current_user.viewProjects(proj_controller.projects)

                elif choice == '2':
                    pname = input("Project name: ")
                    nbhd = input("Neighborhood: ")
                    t1_units = input("Number of 2-Room units: ")
                    t1_price = input("Selling price for 2-Room: ")
                    t2_units = input("Number of 3-Room units: ")
                    t2_price = input("Selling price for 3-Room: ")
                    open_d = input("Open date (YYYY-MM-DD): ")
                    close_d = input("Close date (YYYY-MM-DD): ")
                    slot = input("Officer slots (max 10): ")
                    try:
                        t1u = int(t1_units)
                        t1p = int(t1_price)
                        t2u = int(t2_units)
                        t2p = int(t2_price)
                        s = int(slot)
                        od = parse_date(open_d)
                        cd = parse_date(close_d)
                        ft = {
                            "2-Room": {"units": t1u, "price": t1p},
                            "3-Room": {"units": t2u, "price": t2p}
                        }
                        new_p = current_user.createBTOProject(pname, nbhd, ft, od, cd, s)
                        proj_controller.addProject(new_p)
                        current_user.projects_handling.append(new_p)
                        print(f"Project '{pname}' created.")
                    except ValueError:
                        print("Invalid numeric input.")

                elif choice == '3':
                    pid = input("Project ID to edit: ")
                    if not pid.isdigit():
                        print("Invalid project ID.")
                        continue
                    proj = proj_controller.findProjectByID(int(pid))
                    if not proj:
                        print("Project not found.")
                        continue
                    new_name = input("New project name (blank to skip): ")
                    new_nbhd = input("New neighborhood (blank to skip): ")
                    current_user.editBTOProject(proj, 
                                                new_name if new_name else None,
                                                new_nbhd if new_nbhd else None,
                                                None)

                elif choice == '4':
                    pid = input("Project ID to toggle: ")
                    if not pid.isdigit():
                        print("Invalid project ID.")
                        continue
                    proj = proj_controller.findProjectByID(int(pid))
                    if not proj:
                        print("Project not found.")
                        continue
                    vis = input("Set visibility (1 for True, 0 for False): ")
                    if vis == '1':
                        current_user.toggleProjectVisibility(proj, True)
                    else:
                        current_user.toggleProjectVisibility(proj, False)

                elif choice == '5':
                    pending_apps = [a for a in app_controller.applications
                                    if a.applicationStatus == "Pending"
                                    and a.BTOProject.manager == current_user]
                    if not pending_apps:
                        print("No pending apps for your projects.")
                    else:
                        print("Pending Applications:")
                        for i, a in enumerate(pending_apps, start=1):
                            print(f"{i}. Applicant: {a.applicant.name}, "
                                  f"Project: {a.BTOProject.projectName}, "
                                  f"Flat: {a.chosen_flat_type}")
                        c = input("Select an application to approve/reject: ")
                        try:
                            idx = int(c) - 1
                            if 0 <= idx < len(pending_apps):
                                sel_app = pending_apps[idx]
                                d = input("Approve or Reject? (1 for Approve, 0 for Reject): ")
                                decision = (d == '1')
                                current_user.approveOrRejectApplication(sel_app, decision)
                            else:
                                print("Invalid choice.")
                        except:
                            print("Invalid input.")

                elif choice == '6':
                    w_apps = [a for a in app_controller.applications 
                              if a.requested_withdrawal 
                              and a.BTOProject.manager == current_user]
                    if not w_apps:
                        print("No withdrawal requests.")
                    else:
                        print("Withdrawal Requests:")
                        for i, a in enumerate(w_apps, start=1):
                            print(f"{i}. {a.applicant.name}, Project: {a.BTOProject.projectName}, Status: {a.applicationStatus}")
                        c = input("Select to approve/reject: ")
                        try:
                            idx = int(c) - 1
                            if 0 <= idx < len(w_apps):
                                sel_app = w_apps[idx]
                                d = input("Approve or Reject? (1 for Approve, 0 for Reject): ")
                                decision = (d == '1')
                                current_user.approveOrRejectWithdrawal(sel_app, decision)
                            else:
                                print("Invalid choice.")
                        except:
                            print("Invalid input.")

                elif choice == '7':
                    pending_officers = []
                    for off in officers:
                        if off.registered_project and off.registered_project.manager == current_user:
                            if off.registration_status == "Pending":
                                pending_officers.append(off)
                    if not pending_officers:
                        print("No pending officer registrations.")
                    else:
                        print("Pending Officer Registrations:")
                        for i, o in enumerate(pending_officers, start=1):
                            print(f"{i}. Officer: {o.name}, Project: {o.registered_project.projectName}")
                        c = input("Select to approve/reject: ")
                        try:
                            idx = int(c) - 1
                            if 0 <= idx < len(pending_officers):
                                sel_off = pending_officers[idx]
                                d = input("Approve or Reject? (1 for Approve, 0 for Reject): ")
                                decision = (d == '1')
                                current_user.approveOrRejectHDBOfficerRegistration(sel_off, decision)
                            else:
                                print("Invalid choice.")
                        except:
                            print("Invalid input.")

                elif choice == '8':
                    current_user.generateApplicantReport(app_controller.applications)

                elif choice == '9':
                    all_inqs = inq_controller.getAllInquiries()
                    if not all_inqs:
                        print("No enquiries.")
                    else:
                        for i, enq in enumerate(all_inqs, start=1):
                            print(f"{i}. From {enq.applicant.name}: {enq.message}")
                            if enq.response:
                                print(f"   Response: {enq.response}")

                elif choice == '10':
                    all_inqs = inq_controller.getAllInquiries()
                    if not all_inqs:
                        print("No enquiries to reply to.")
                    else:
                        for i, enq in enumerate(all_inqs, start=1):
                            print(f"{i}. From {enq.applicant.name}: {enq.message} (response: {enq.response})")
                        c = input("Select an enquiry to reply: ")
                        try:
                            idx = int(c) - 1
                            if 0 <= idx < len(all_inqs):
                                sel_enq = all_inqs[idx]
                                resp = input("Enter reply: ")
                                inq_controller.replyInquiry(sel_enq, resp)
                                print("Replied successfully.")
                            else:
                                print("Invalid choice.")
                        except:
                            print("Invalid input.")

                elif choice == '11':
                    new_pw = input("Enter new password: ")
                    current_user.changePassword(new_pw)

                elif choice == '12':
                    globals()['current_user'] = None
                else:
                    print("Invalid choice.")

            else:
                print("Unknown user type. Logging out.")
                globals()['current_user'] = None


if __name__ == "__main__":
    main()
