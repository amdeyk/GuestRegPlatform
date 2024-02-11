# FastAPI application for managing guest registrations and updates in a conference or event.
# This application uses FastAPI for the backend, Jinja2 for templating, and CSV files for data storage.

from datetime import datetime
from fastapi import FastAPI, Request, Form, HTTPException, Response, Query, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import csv
import os
import re
from barcode import EAN13, Code128
from barcode.writer import ImageWriter
import io
import configparser
import shutil
from datetime import datetime
from fastapi.responses import FileResponse
from pydantic import BaseModel,  ClassVar
from typing import Optional
import codecs
import json
from urllib.parse import parse_qs
from fastapi import File, UploadFile
from typing import Tuple
from fastapi.responses import JSONResponse
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import random

#/home/ubuntu/guest/GuestRegPlatform   /home/ubuntu/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8002
# Initialize FastAPI app, configure template directory, and serve static files.
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models define the structure of requests for data validation and serialization.
# These models ensure valid data is received and sent in API requests, enhancing data integrity.

class UpdateGuestInfo(BaseModel):
    # A model representing the schema for updating guest information.
    # It includes fields that can be updated post-registration like check-in status, payment status, etc.
    # It's used in routes handling the update operations to ensure only allowed data is processed.
    guest_id: str
    isCheckedIn: bool = False
    isPaymentReceived: bool = False
    isGiftReceived: bool = False
    isCarReceived: bool = False
    carNumber: str = ""
    isLunchDay1: bool = False
    isDinnerDay1: bool = False
    isLunchDay2: bool = False
    isDinnerDay2: bool = False
    isLunchDay3: bool = False
    isFaculty: bool = False
    isIndustry: bool = False
    isResidential: bool = False
    isEligibleCar: bool = False
    hotelName: str = ""
    recordCheck = str = "N"
    
class GuestRegistrationForm(BaseModel):
    # A model for guest registration form data capturing essential guest information.
    # This model ensures that all required fields are included in the request for a new registration.
    # It's used in the guest registration route to validate incoming data.
    name: str = Form(...)
    email: str = Form(...)
    phone: str = Form(...)
    type: str = Form(...)
    residential_status: str = Form(...)
    check_in: Optional[str] = Form(None)
    check_out: Optional[str] = Form(None)
    amount_given: Optional[float] = Form(None)
    
class GuestUpdate(BaseModel):
    # A model for updating guest information via barcode scan.
    # It contains fields that are likely to be updated in a quick action, such as checking in a guest or confirming payment.
    # This model simplifies processing and validating these quick updates, linking barcode actions directly to data updates.
    guestId: str
    updateType: str
    
# Read config.ini file
config = configparser.ConfigParser()
config.read('config.ini')

# Accessing the values from config.ini
admin_password = config['DEFAULT']['AdminPassword']
software_version = config['DEFAULT']['SoftwareVersion']



# Define a dictionary to map form field names to your guest record field names
FORM_TO_GUEST_FIELD_MAPPING = {
    'isCheckedIn': 'IsCheckedIn',
    'isPaymentReceived': 'IsPaymentReceived',
    'isGiftReceived': 'IsGiftReceived',
    'isCarReceived': 'IsCarReceived',
    'isLunchDay1': 'IsLunchDay1',
    'isDinnerDay1': 'IsDinnerDay1',
    'isLunchDay2': 'IsLunchDay2',
    'isDinnerDay2': 'IsDinnerDay2',
    'isLunchDay3': 'IsLunchDay3',
    'isResidential': 'IsResidential',
    'isEligibleCar': 'IsEligibleCar',
    'guestType': 'GuestType',  # Assuming this field should map to 'GuestType'
    'check_in': 'CheckIn',
    'check_out': 'CheckOut',
    'hotel_name': 'HotelName',
    'carNumber': 'CarNumber'
    # Add other form-to-guest field mappings as needed
}



def integrity_test_passed(original_guests, updated_guests):
    # Define which fields are allowed to change
    allowed_changes = {
        "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
        "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
        "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
        "HotelName", "CheckIn", "CheckOut", "RecordCheck"
    }
    
    # Compare each guest in the original list with the updated list
    for original, updated in zip(original_guests, updated_guests):
        # Ensure the IDs are the same - we are comparing the same guest
        if original["ID"] != updated["ID"]:
            print('Failed Integrity Test - Guest IDs do not match.')
            return False
        
        # Check each field in the original guest
        for field in allowed_changes:
            original_value = original.get(field, '')
            updated_value = updated.get(field, '')
            
            # Fail the test if an original value set to 'True' has been changed to 'False'
            if original_value == 'True' and updated_value == 'False':
                print(f'Failed Integrity Test - {field} was changed from True to False.')
                return False
    
    # If all checks pass, return True
    return True




@app.get("/static/style.css")
async def get_css():
    response = Response(content=await app.get("/static/style.css"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"  # Prevent caching
    return response

# CSV file paths
CSV_FILE_GUESTS = "./data/guests.csv"

# Utility Functions
def read_csv_data(file_path):
    """
    Reads guest data from a CSV file and returns it as a list of dictionaries.
    Each dictionary represents a guest with keys as column headers and values as the guest information.
    This function is a critical component for data retrieval, used across various routes to fetch and display guest data.
    Input:
        file_path (str): The path to the CSV file containing guest data.
    Output:
        data (list): A list of dictionaries, each representing a guest's information.
    Dependencies:
        csv: For reading CSV file format.
    """
    data = []
    print("Reading CSV file:", file_path)  # Debugging
    if os.path.exists(file_path):
        with open(file_path, mode='r', newline='', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if '\ufeffID' in row:
                    row['ID'] = row.pop('\ufeffID')
                #print(row)  # Debugging
                data.append(row)
    else:
        print("CSV file not found!")  # Debugging
    return data

def write_csv_data(file_path, data, fieldnames):
    # Generate a timestamped backup file name
    """
    Writes guest data to a CSV file, creating a timestamped backup of the existing file before overwriting.
    This ensures data integrity by maintaining backups of guest data at each write operation.
    It's linked to routes that modify guest data, providing a unified function for data writing and backup.
    Input:
        file_path (str): The path to the CSV file to write data to.
        data (list): A list of dictionaries, each representing a guest's information to be written.
        fieldnames (list): A list of strings representing the CSV column headers.
    Output:
        None, but creates or updates a CSV file on disk.
    Dependencies:
        csv: For writing CSV file format.
        shutil, datetime: For creating timestamped backup files.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Format: YYYYMMDDHHMMSS
    backup_path = f"{file_path}_backup_{timestamp}.csv"

    # Create a backup of the current CSV file
    if os.path.exists(file_path):
        shutil.copy(file_path, backup_path)
        
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        # Update fieldnames to include all necessary fields
        fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
            "HotelName", "RecordCheck"
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

# def write_csv_data_update(file_path, data, fieldnames):
#     try:
#         with open(file_path, mode='w', newline='', encoding='utf-8') as file:
#             writer = csv.DictWriter(file, fieldnames=fieldnames)
#             writer.writeheader()
#             for row in data:
#                 writer.writerow(row)
#     except Exception as e:
#         print(f"Error writing CSV data: {e}")
def validate_phone_number(phone: str) -> bool:
    """Validate the phone number to be 10 digits."""
    return re.fullmatch(r'\d{10}', phone) is not None

def normalize_phone_number(phone: str) -> str:
    """Remove any non-numeric characters from the phone number."""
    return re.sub(r'\D', '', phone)

def validate_email(email: str) -> bool:
    """Validate the email address using a regular expression."""
    return re.fullmatch(r'[^@]+@[^@]+\.[^@]+', email) is not None

def generate_id(name: str, phone: str) -> str:
    """Generate a unique ID based on the first two letters of the name and a random 5-digit number."""
    # Extract the first two letters of the name, defaulting to 'XX' if name is too short
    prefix = re.sub(r'[^A-Za-z]', '', name[:2].upper()) if len(name) >= 2 else 'XX'
    # Generate a random 5-digit number as a string
    random_number = f"{random.randint(100, 999999):06d}"
    return prefix + random_number

def validate_and_normalize_row(row: dict, row_index: int) -> Tuple[bool, dict, list]:
    """Validate and normalize a row of CSV data."""
    errors = []
    normalized_row = {}

    # Validate and normalize Name
    name = row.get("Name", "").strip().title()
    if not name:
        errors.append({"row": row_index, "field": "Name", "value": name, "error": "Name is required."})
    else:
        # Remove prefixes and adjust name
        normalized_name = re.sub(r'^(Dr\.?|Mr\.?|Mrs\.?|Prof\.?)\s*', '', name).strip().title()
        normalized_row["Name"] = normalized_name

    # Validate and normalize Phone
    phone = normalize_phone_number(row.get("Phone", ""))
    if phone and not validate_phone_number(phone):
        errors.append({"row": row_index, "field": "Phone", "value": phone, "error": "Invalid phone number format."})
    else:
        normalized_row["Phone"] = phone

    # Validate and normalize Email
    email = row.get("Email", "").strip().lower()
    # Validate email only if it's not blank
    if email and not validate_email(email):
        errors.append({"row": row_index, "field": "Email", "value": email, "error": "Invalid email format."})
    elif email:
        normalized_row["Email"] = email  # Already normalized (lowercased)

    # Generate ID if no errors found
    if not errors:
        normalized_row["ID"] = generate_id(normalized_name, phone)

    return not errors, normalized_row, errors



async def process_uploaded_csv(temp_file_path: str):
    processed_data = []
    all_errors = []
    
    with open(temp_file_path, mode='r', newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for index, row in enumerate(reader, start=1):
            valid, normalized_row, errors = validate_and_normalize_row(row, index)
            if valid:
                processed_data.append(normalized_row)
            else:
                all_errors.extend(errors)

    if all_errors:
        raise HTTPException(status_code=422, detail=all_errors)

    # Sort data by name field (or any other criteria you choose)
    sorted_data = sorted(processed_data, key=lambda x: x['Name'])
    return sorted_data, all_errors



def reset_database():
    # Path to your CSV file
    csv_file_path = CSV_FILE_GUESTS

    # Check if the file exists
    if os.path.exists(csv_file_path):
        # Generate a timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_file_path = f"{csv_file_path}_backup_{timestamp}"

        # Copy the existing CSV file to a new file with the timestamp
        shutil.copy(csv_file_path, backup_file_path)

        # Delete the existing CSV file
        os.remove(csv_file_path)

    # Create a new CSV file with the same structure
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=["ID", "Name", "Email", "Phone"])
        writer.writeheader()

def textsize(text, font, draw):
    """Calculates the width and height of the given text using the specified font."""
    _, _, width, height = draw.textbbox((0, 0), text, font=font)
    return width, height



@app.get("/view-guest-details", response_class=HTMLResponse)
async def view_guest_details(request: Request, guest_query: str):
    # Assuming you have a function to get guest data by ID
    print(guest_query)
    guests = read_csv_data(CSV_FILE_GUESTS)
    # Try to match by ID first, then by name
    
    guest_details = next((guest for guest in guests if guest['ID'].strip() == guest_query.strip()), None)
    if not guest_details:
        # If no ID match, try partial name match
        guest_details = next((guest for guest in guests if guest_query.lower() in guest['Name'].lower()), None)
    if guest_details:
        return templates.TemplateResponse("guest_view.html", {"request": request, "guest": guest_details})
    else:
        return templates.TemplateResponse("guest_view.html", {"request": request, "message": "Guest not found. Please try again."})
    
    

@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    """
    Serves the home page of the application.
    It's the entry point for users, providing links to registration, admin dashboard, etc.
    Dependencies:
        templates: Jinja2Templates for rendering the homepage template.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/guest_registration", response_class=HTMLResponse)
async def guest_registration(request: Request):
    """
    Displays the guest registration form, allowing new guests to register for the event.
    This route serves the front-end form which captures essential guest information.
    Dependencies:
        - templates: Utilizes Jinja2 templates to render the guest registration form.
    Input:
        - request: The request object used to generate the HTTP response.
    Output:
        - HTMLResponse: Renders the guest registration page with the form for users to fill out.
    """
    return templates.TemplateResponse("guest_registration.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Renders an upload page with a form."""
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload-file")   
async def handle_file_upload(file: UploadFile = File(...)):
    # Validate file type
    if not file.filename.endswith('.csv'):
        return JSONResponse(status_code=400, content={"success": False, "errors": ["File type not supported. Please upload a CSV file."]})

    # Save the file temporarily
    temp_file_path = "temp_upload.csv"
    with open(temp_file_path, 'wb+') as temp_file:
        content = await file.read()  # Read the content of the uploaded file
        temp_file.write(content)

    try:
        # Process the uploaded CSV to validate and sort the data, returning any errors found
        sorted_data, errors = await process_uploaded_csv(temp_file_path)

        if errors:
            # Return errors without writing to the database file
            return JSONResponse(status_code=422, content={"success": False, "errors": errors})
        
        # Here, write the sorted and validated data back to the guests.csv file
        write_csv_data(CSV_FILE_GUESTS, sorted_data, fieldnames=sorted_data[0].keys() if sorted_data else [])
        
        # Return success response after writing data
        return JSONResponse(status_code=200, content={"success": True, "message": "File processed and saved successfully."})

    except HTTPException as exc:
        # If a validation error occurs, return the error details
        return JSONResponse(status_code=exc.status_code, content={"success": False, "errors": exc.detail})
    
    finally:
        # Cleanup: remove the temporary file
        os.remove(temp_file_path)

# POST route for guest registration
@app.post("/submit-guest-registration", response_class=HTMLResponse)
async def submit_guest_registration(request: Request, 
                                    name: str = Form(...), 
                                    email: str = Form(...), 
                                    phone: str = Form(...), 
                                    type1: str = Form(...), 
                                    residential_status: str = Form(...),
                                    check_in: Optional[str] = Form(None),
                                    check_out: Optional[str] = Form(None),
                                    amount_given: Optional[float] = Form(None)):
    """
    Handles submission of the guest registration form.
    Validates input data using Pydantic models, writes new guest data to CSV, and returns a success message.
    It's linked to the guest registration form page and directly interacts with CSV file operations.
    Input:
        request: FastAPI Request object containing form data.
    Output:
        HTMLResponse: The guest registration page with a success or error message.
    Dependencies:
        Pydantic models for data validation, `write_csv_data` for updating CSV files.
    """
    print(name, email, phone, type, residential_status, check_in, check_out, amount_given)
    # Check if the phone number is at least 10 digits long
    if len(phone) < 10:
        return templates.TemplateResponse("guest_registration.html", {"request": request, "message": "Phone number must be at least 10 digits long"})

    # Validate email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return templates.TemplateResponse("guest_registration.html", {"request": request, "message": "Invalid email format"})

    # Logic to determine isFaculty, isIndustry, and isResidential
    is_faculty = type1 == 'faculty'
    is_industry = type1 == 'industry'
    is_residential = residential_status == 'residential'

    # Validate check-in and check-out dates if residential
    if is_residential:
        try:
            check_in_date = datetime.fromisoformat(check_in)
            check_out_date = datetime.fromisoformat(check_out)
        except ValueError:
            return templates.TemplateResponse("guest_registration.html", {"request": request, "message": "Invalid date format. Please use the proper date format."})
        
        if check_out_date <= check_in_date:
            return templates.TemplateResponse("guest_registration.html", {"request": request, "message": "Check-out date must be later than check-in date"})

    # Prevent re-registration with the same phone number
    guests = read_csv_data(CSV_FILE_GUESTS)
    if any(guest['Phone'] == phone for guest in guests):
        return templates.TemplateResponse("guest_registration.html", {"request": request, "message": "This phone number has already been registered"})

    # Create a dictionary for the new guest including the new fields (isFaculty, isIndustry, isResidential)
    guest_id = name[:2] + phone if len(name) >= 2 else name + phone
    new_guest = {
        "ID": guest_id,
        "Name": name,
        "Email": email,
        "Phone": phone,
        "CheckIn": check_in if is_residential else "",
        "CheckOut": check_out if is_residential else "",
        "AmountGiven": amount_given if not is_residential else 0.0,
        "IsFaculty": is_faculty,
        "IsIndustry": is_industry,
        "IsResidential": is_residential
    }

    guests.append(new_guest)
    fieldnames = ["ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven", "IsFaculty", "IsIndustry", "IsResidential"]
    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)

    return templates.TemplateResponse("guest_registration.html", {"request": request, "message": "Guest registered successfully"})


@app.get("/admin_dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    # Fetch user list from the database
    """
    Serves the admin dashboard page, which displays a list of all registered guests and provides administrative actions.
    This page is crucial for event organizers to oversee guest registrations and perform batch operations.
    Dependencies:
        - read_csv_data: To fetch the current list of all guests for display.
        - templates: Jinja2Templates for rendering the admin dashboard template with guest data.
    Input:
        - request: FastAPI Request object, used for template rendering.
    Output:
        - HTMLResponse: The admin dashboard page populated with guest registration data.
    """
    users = read_csv_data(CSV_FILE_GUESTS)  # Modify as needed to fit your data fetching logic
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": users})

@app.get("/employee_dashboard", response_class=HTMLResponse)
async def employee_dashboard(request: Request):
    """
    Serves the employee dashboard page, allowing event staff to view guest information and perform guest-related actions.
    This dashboard provides a simplified view focusing on tasks relevant to event staff, such as check-in status and guest updates.
    Dependencies:
        - read_csv_data: To fetch the current list of all guests for display.
        - templates: Jinja2Templates for rendering the employee dashboard template with guest data.
    Input:
        - request: FastAPI Request object, used for template rendering.
    Output:
        - HTMLResponse: The employee dashboard page populated with guest registration data.
    """
    guests = read_csv_data(CSV_FILE_GUESTS)
    return templates.TemplateResponse("employee_dashboard.html", {"request": request, "guests": guests})


@app.post("/update-guest-info")
async def update_guest_info(request: Request):
    """
    Endpoint for updating guest information based on form submissions from the admin or employee dashboard.
    It processes submitted form data to update specific guest records in the CSV storage.
    This route is essential for maintaining up-to-date guest information and supports various guest management operations.
    Dependencies:
        - FORM_TO_GUEST_FIELD_MAPPING: A dictionary mapping form fields to guest record fields for accurate data updates.
        - read_csv_data and write_csv_data: For reading current guest data and writing updates back to the CSV.
    Input:
        - request: FastAPI Request object containing form data for guest updates.
    Output:
        - RedirectResponse: Redirects to the dashboard page with a success message, indicating the update was processed.
    """
    form_data = await request.form()
    data = {key: value for key, value in form_data.items()}
    print("Received form data:", data)  # Log the received form data

    # Define the list of checkbox field names
    checkbox_fields = ['IsCheckedIn', 'IsPaymentReceived', 'IsGiftReceived', 'IsCarReceived', 
                       'IsLunchDay1', 'IsDinnerDay1', 'IsLunchDay2', 'IsDinnerDay2', 'IsLunchDay3', 
                       'IsResidential', 'IsEligibleCar', 'guestType']

    # Handle checkboxes and map form fields to guest record fields
    for form_field, guest_field in FORM_TO_GUEST_FIELD_MAPPING.items():
        if guest_field in checkbox_fields:
            # Explicitly check for 'on' value for checkboxes
            data[guest_field] = form_data.get(form_field, 'off') == 'on'
        else:
            data[guest_field] = data.get(form_field, '')
        print(f"Processed {form_field} to {guest_field}: {data[guest_field]}")  # Log field processing

    # Handling Guest Type
    if 'guestType' in data:
        if data['guestType'] == 'faculty':
            data['IsFaculty'] = 'True'
            data['IsIndustry'] = 'False'
        elif data['guestType'] == 'industry':
            data['IsFaculty'] = 'False'
            data['IsIndustry'] = 'True'
        else: # delegate
            data['IsFaculty'] = 'False'
            data['IsIndustry'] = 'False'
    print("Guest Type - IsFaculty:", data['IsFaculty'], "IsIndustry:", data['IsIndustry'])  # Log guest type

    # Read all guest data
    guests = read_csv_data(CSV_FILE_GUESTS)

    # Create a copy of the original data
    original_guests = [guest.copy() for guest in guests]

    # Update logic
    guest_found = False
    for guest in guests:
        if guest['ID'] == data['guest_id']:
            print(f"Found guest with ID {data['guest_id']} for update.")  # Log when guest is found
            
            # Preserve original values of IsFaculty and IsIndustry
            original_is_faculty = guest['IsFaculty']
            original_is_industry = guest['IsIndustry']
    
            # Update fields only if they are present in the form submission
            for guest_field in FORM_TO_GUEST_FIELD_MAPPING.values():
                if guest_field in guest:
                    if guest_field in checkbox_fields:
                        if guest_field in data:
                            if guest[guest_field] == 'False' or data[guest_field]:
                                print(f"Updating {guest_field} from {guest[guest_field]} to {data[guest_field]}")  # Log updates
                                guest[guest_field] = data[guest_field]
                            else:
                                print(f"Skipping update for {guest_field} as it would change True to False")
                        else:
                            print(f"Checkbox field {guest_field}: No change (not in form data)")
                    else:
                        # Update other fields if new value is not empty
                        if data.get(guest_field, '') != '':
                            print(f"Updating {guest_field} from {guest[guest_field]} to {data[guest_field]}")  # Log updates
                            guest[guest_field] = data[guest_field]
    
            # Handle GuestType - prevent change if already set
            if original_is_faculty == 'True':
                guest['IsFaculty'] = 'True'
                guest['IsIndustry'] = 'False'
            elif original_is_industry == 'True':
                guest['IsFaculty'] = 'False'
                guest['IsIndustry'] = 'True'
            else:
                # Only update if not already set
                guest['IsFaculty'] = 'True' if data['IsFaculty'] == 'True' else 'False'
                guest['IsIndustry'] = 'True' if data['IsIndustry'] == 'True' else 'False'
    
            # Handle residential-specific fields
            if guest['IsResidential']:
                if 'CheckIn' in data and data['CheckIn'] != '':
                    guest['CheckIn'] = data['CheckIn']
                if 'CheckOut' in data and data['CheckOut'] != '':
                    guest['CheckOut'] = data['CheckOut']
                if 'HotelName' in data and data['HotelName'] != '':
                    guest['HotelName'] = data['HotelName']
    
            guest_found = True
            break

    if not guest_found:
        print(f"Guest ID {data['guest_id']} not found.")
        return {"message": "Guest ID not found"}

    # Integrity test: Compare original_guests with guests to ensure only intended updates are made
    if not integrity_test_passed(original_guests, guests):
        print("Integrity test failed.")
        return {"message": "Data integrity check failed"}

    fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
            "HotelName", "RecordCheck"
        ]

    # Writing the updated data to CSV
    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
    print("Data successfully written to CSV.")
    return RedirectResponse(url="/employee_dashboard?update_success=true", status_code=303)


##







# @app.post("/update-guest-info")
# async def update_guest_info(update_info: UpdateGuestInfo):
#     print(update_info)
#     guests = read_csv_data(CSV_FILE_GUESTS)
#     # async def update_guest_info(request: Request):
#     # raw_body = await request.body()

#     for guest in guests:
#         if guest['ID'] == update_info.guest_id:
#             guest['IsCheckedIn'] = update_info.isCheckedIn
#             guest['IsPaymentReceived'] = update_info.isPaymentReceived
#             guest['IsGiftReceived'] = update_info.isGiftReceived
#             guest['IsCarReceived'] = update_info.isCarReceived
#             guest['CarNumber'] = update_info.carNumber if update_info.isCarReceived else ""
#             guest['IsLunchDay1'] = update_info.isLunchDay1
#             guest['IsDinnerDay1'] = update_info.isDinnerDay1
#             guest['IsLunchDay2'] = update_info.isLunchDay2
#             guest['IsDinnerDay2'] = update_info.isDinnerDay2
#             guest['IsLunchDay3'] = update_info.isLunchDay3
#             # Add any additional fields you need to update
#             break
#     else:
#         return {"message": "Guest ID not found"}

#     write_csv_data(CSV_FILE_GUESTS, guests)
#     return {"message": "Guest information updated successfully"}

# #return RedirectResponse(url="/employee_dashboard", status_code=303)


@app.post("/fetch-guest-details", response_class=HTMLResponse)
async def fetch_guest_details(request: Request, guest_id: str = Form(...)):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)

    if guest_details:
        return templates.TemplateResponse("view_guest.html", {"request": request, "guest": guest_details})
    else:
        raise HTTPException(status_code=404, detail="Guest not found")


@app.get("/view_guest", response_class=HTMLResponse)
async def view_guest(request: Request):
    guests = read_csv_data(CSV_FILE_GUESTS)
    #print(guests)  # Debugging: Print the guests data
    return templates.TemplateResponse("view_guest.html", {"request": request, "guests": guests})

@app.get("/guest_view", response_class=HTMLResponse)
async def guest_view(request: Request, query: str = None):
    """
    Displays guests in a read-only format based on a partial name or guest ID.
    If no query is provided, all guests are displayed.

    :param request: The FastAPI request object.
    :param query: Optional; a partial name or guest ID to filter the guests.
    :return: The guest_view.html template populated with guest details.
    """
    guests = read_csv_data(CSV_FILE_GUESTS)
    
    # If a query is provided, filter the guests accordingly
    if query:
        filtered_guests = [guest for guest in guests if query.lower() in guest["Name"].lower() or query.lower() in guest["ID"].lower()]
    else:
        filtered_guests = guests

    return templates.TemplateResponse("guest_view.html", {"request": request, "guests": filtered_guests})


@app.get("/report", response_class=HTMLResponse)
async def report(request: Request):
    """
    Displays the report generation page, allowing administrators to generate various reports about the event's guests.
    This includes registration counts, check-in status, payment status, and more.
    Dependencies:
        - templates: Utilizes Jinja2 templates for rendering the report generation page.
    Input:
        - request: The request object used to generate the HTTP response.
    Output:
        - HTMLResponse: Renders the report generation page with options for different types of reports.
    """
    return templates.TemplateResponse("report.html", {"request": request})

@app.get("/fetch-guest-details-by-barcode")
async def fetch_guest_details_by_barcode(barcode: str):
    """
    Fetches guest details based on a scanned barcode, facilitating quick check-in or information retrieval at the event.
    This route is linked with barcode scanning functionality, allowing event staff to scan a guest's barcode to retrieve their information.
    Dependencies:
        - read_csv_data: To fetch the current list of all guests and match the barcode.
    Input:
        - barcode: The barcode string that corresponds to a guest ID.
    Output:
        - JSON response with guest details if found, or an error message if not found.
    """
    print(barcode)
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == barcode), None)

    if guest_details:
        return guest_details  # Ensure this returns JSON
    else:
        return {"error": "Guest not found"}, 404  # Returning a JSON response with error message

@app.post("/generate-report", response_class=HTMLResponse)
async def generate_report(request: Request, report_type: str = Form(...)):
    """
    Generates and displays a report based on the selected type, such as guest info, payment status, or check-in status.
    It queries the event's database (CSV file) and filters or aggregates data according to the report requirements.
    Dependencies:
        - read_csv_data: To read the guest data from the CSV file.
        - templates: To render the report results in an HTML template.
    Input:
        - report_type: Specifies the type of report to generate, captured from the user's selection.
    Output:
        - HTMLResponse: Renders a page displaying the requested report's results.
    """
    guests = read_csv_data(CSV_FILE_GUESTS)

    if report_type == "guestInfo":
        report_data = guests

    elif report_type == "paymentStatus":
        report_data = [
            {
                "ID": guest["ID"], 
                "Name": guest["Name"], 
                "PaymentStatus": "Paid" if guest.get('IsPaymentReceived', 'False') == 'True' else "Unpaid"
            }
            for guest in guests
        ]

    elif report_type == "checkinStatus":
        report_data = [
            {
                "ID": guest["ID"], 
                "Name": guest["Name"], 
                "CheckInStatus": "Checked-In" if guest.get('IsCheckedIn', 'False') == 'True' else "Not Checked-In"
            }
            for guest in guests
        ]

    elif report_type == "giftStatus":
        report_data = [
            {
                "ID": guest["ID"],
                "Name": guest["Name"],
                "GiftStatus": "Received" if guest.get('IsGiftReceived', 'False') == 'True' else "Not Received"
            }
            for guest in guests
        ]

    elif report_type == "carStatus":
        report_data = [
            {
                "ID": guest["ID"],
                "Name": guest["Name"],
                "CarStatus": "Received" if guest.get('IsCarReceived', 'False') == 'True' else "Not Received",
                "CarNumber": guest.get('CarNumber', 'N/A')
            }
            for guest in guests
        ]

    elif report_type == "lunchCouponStatus":
        report_data = [
            {
                "ID": guest["ID"],
                "Name": guest["Name"],
                "LunchCoupon": "Given" if guest.get('IsLunch', 'False') == 'True' else "Not Given"
            }
            for guest in guests
        ]

    elif report_type == "lunchDay1Status":
        report_data = [
            {
                "ID": guest["ID"],
                "Name": guest["Name"],
                "LunchDay1": "Given" if guest.get('IsLunchDay1', 'False') == 'True' else "Not Given"
            }
            for guest in guests
        ]
    elif report_type == "dinnerDay1Status":
        report_data = [
            {
                "ID": guest["ID"],
                "Name": guest["Name"],
                "DinnerDay1": "Given" if guest.get('IsDinnerDay1', 'False') == 'True' else "Not Given"
            }
            for guest in guests
        ]
    elif report_type == "lunchDay2Status":
        report_data = [
            {
                "ID": guest["ID"],
                "Name": guest["Name"],
                "LunchDay2": "Given" if guest.get('IsLunchDay2', 'False') == 'True' else "Not Given"
            }
            for guest in guests
        ]
    elif report_type == "dinnerDay2Status":
        report_data = [
            {
                "ID": guest["ID"],
                "Name": guest["Name"],
                "DinnerDay2": "Given" if guest.get('IsDinnerDay2', 'False') == 'True' else "Not Given"
            }
            for guest in guests
        ]
    elif report_type == "lunchDay3Status":
        report_data = [
            {
                "ID": guest["ID"],
                "Name": guest["Name"],
                "LunchDay3": "Given" if guest.get('IsLunchDay3', 'False') == 'True' else "Not Given"
            }
            for guest in guests
        ]

    else:
        raise HTTPException(status_code=400, detail="Invalid report type")

    return templates.TemplateResponse("report.html", {"request": request, "report_data": report_data, "report_type": report_type})


@app.get("/scan-barcode", response_class=HTMLResponse)
async def scan_barcode(request: Request):
    return templates.TemplateResponse("scan_barcode.html", {"request": request})


@app.post("/delete-database", response_class=HTMLResponse)
async def delete_database(request: Request, password: str = Form(...)):
    """
    Allows administrators to reset the event's database, deleting all guest records after confirming the admin password.
    This is a critical operation intended for use in resetting the event's data post-conclusion or during testing.
    Dependencies:
        - admin_password: The administrator password for authentication, loaded from config.
    Input:
        - password: The admin password submitted through the form for verification.
    Output:
        - HTMLResponse: Redirects to the admin dashboard with a success or error message based on the operation's outcome.
    """
    print(f"Received password: {password}")
    print(f"Expected admin password: {admin_password}")
    # Check if the provided password matches the admin password
    if password == admin_password:
        # Logic to reset the database
        try:
            reset_database()  # Call the function to reset the database
            return templates.TemplateResponse("admin_dashboard.html", {"request": request, "message": "Database reset successfully."})
        except Exception as e:
            return templates.TemplateResponse("admin_dashboard.html", {"request": request, "message": f"Error resetting database: {e}"})
    else:
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "message": "Incorrect admin password."})


@app.get("/generate-report-download")
async def generate_report_download():
    # Path to your CSV file
    """
    Allows users to download a CSV report of all guest information.
    This route is particularly useful for administrative purposes, enabling the export of guest data for offline analysis or record-keeping.
    Dependencies:
        - CSV_FILE_GUESTS: Path to the CSV file used for storing guest data.
    Output:
        - FileResponse: Triggers a download of the guest data CSV file in the user's browser.
    """
    csv_file_path = CSV_FILE_GUESTS

    # Check if the file exists
    if os.path.exists(csv_file_path):
        # Return the CSV file as a downloadable response
        headers = {
            'Content-Disposition': 'attachment; filename=guest_report.csv'
        }
        return FileResponse(path=csv_file_path, headers=headers)
    else:
        # Handle the case where the file does not exist
        return {"error": "CSV file not found"}, 404

@app.post("/generate-barcode")
async def generate_barcode(request: Request, user_id: str = Form(...)):
    # Read guest data from CSV
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest = next((g for g in guests if g['ID'] == user_id), None)

    if guest is None:
        # Handle case where guest ID is not found
        return {"error": "Guest ID not found"}

    # Create an image
    image_width = 500  # Approx 5 inches, assuming 100 pixels per inch
    image_height = 700  # Approx 3 inches
    image = Image.new('RGB', (image_width, image_height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Define fonts
    try:
        # Adjust the path to your font file
        font_regular = ImageFont.truetype("arial.ttf", 24)
        font_large = ImageFont.truetype("arial.ttf", 48)  # Conference name font size doubled
    except IOError:
        font_regular = ImageFont.load_default()
        font_large = ImageFont.load_default()

    # Calculate text sizes and positions
    conference_text = "AROI Conference"
    name_text = f"Name: {guest['Name']}"
    phone_text = f"Phone: {guest['Phone']}"
    id_text = f"ID: {guest['ID']}"

    # Draw blue strip for conference name
    padding = int(font_large.size * 0.2)  # 20% padding around font height
    text_width, text_height = textsize(conference_text, font_large, draw)
    strip_height = text_height + padding * 2
    strip_top = 50
    draw.rectangle([(0, strip_top), (image_width, strip_top + strip_height)], fill="blue")

    # Draw conference text in white on the blue strip
    text_x = (image_width - text_width) / 2
    text_y = strip_top + padding
    draw.text((text_x, text_y), conference_text, fill="white", font=font_large)

    # Adjust current_height for next texts
    current_height = strip_top + strip_height + 20  # Adding some space below the strip

    # Drawing other texts
    draw.text(((image_width - text_width) / 2, current_height), name_text, fill="black", font=font_regular)
    current_height += 40
    draw.text(((image_width - text_width) / 2, current_height), phone_text, fill="black", font=font_regular)
    current_height += 40
    draw.text(((image_width - text_width) / 2, current_height), id_text, fill="black", font=font_regular)
    current_height += 160  # Increase space before barcode for visual separation

    # Generate and add barcode
    barcode_io = BytesIO()
    barcode = Code128(user_id, writer=ImageWriter())
    barcode.write(barcode_io)
    barcode_io.seek(0)
    barcode_image = Image.open(barcode_io)
    
    # Using default resampling for simplicity
    barcode_image = barcode_image.resize((image_width - 40, 100))
    image.paste(barcode_image, (20, current_height))
    
    # Save final image to BytesIO object and prepare for response
    final_io = BytesIO()
    image.save(final_io, 'PNG')
    final_io.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename={user_id}_barcode.png'
    }
    return StreamingResponse(final_io, media_type="image/png", headers=headers)

@app.post("/update-guest-info-scan")
async def update_guest_information(update_data: GuestUpdate):
    # Retrieve the existing guests' data
    guests = read_csv_data(CSV_FILE_GUESTS)
    
    # Find the guest by ID
    for guest in guests:
        if guest['ID'] == update_data.guestId:
            updated = False  # Flag to check if an update was made
            already_updated_message = "This information is already updated for the guest."

            if update_data.updateType == "paymentUpdateButton" and guest.get('IsPaymentReceived') != 'True':
                guest['IsPaymentReceived'] = 'True'
                updated = True
            elif update_data.updateType == "checkinUpdateButton" and guest.get('IsCheckedIn') != 'True':
                guest['IsCheckedIn'] = 'True'
                updated = True
            elif update_data.updateType == "giftUpdateButton" and guest.get('IsGiftReceived') != 'True':
                guest['IsGiftReceived'] = 'True'
                updated = True
            elif update_data.updateType == "lunchDay1Button" and guest.get('IsLunchDay1') != 'True':
                guest['IsLunchDay1'] = 'True'
                updated = True
            elif update_data.updateType == "dinnerDay1Button" and guest.get('IsDinnerDay1') != 'True':
                guest['IsDinnerDay1'] = 'True'
                updated = True
            elif update_data.updateType == "lunchDay2Button" and guest.get('IslunchDay2') != 'True':
                guest['IslunchDay2'] = 'True'
                updated = True
            elif update_data.updateType == "dinnerDay2Button" and guest.get('IsDinnerDay2') != 'True':
                guest['IsDinnerDay2'] = 'True'
                updated = True
            elif update_data.updateType == "lunchDay3Button" and guest.get('IslunchDay3') != 'True':
                guest['IslunchDay3'] = 'True'
                updated = True

            if updated:
                # Write updated data back to CSV
                fieldnames = [
                        "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
                        "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
                        "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
                        "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
                        "HotelName", "RecordCheck"
                    ]

                write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
                return {"message": "Guest information updated successfully"}
            else:
                return {"message": already_updated_message}

    # Guest ID not found
    raise HTTPException(status_code=404, detail="Guest not found")

@app.get("/manage_guest", response_class=HTMLResponse)
async def manage_guest(request: Request):
    # You might want to pass any necessary data to the template
    return templates.TemplateResponse("manage_guest.html", {"request": request})


@app.get("/fetch-guest")
async def fetch_guest(request: Request):
    guest_id = request.query_params.get("guest_id")
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    #print('the guest details : '. guest_details)
    if guest_details:
        return templates.TemplateResponse("employee_dashboard.html", {"request": request, "guest": guest_details, "guests": guests})
    else:
        return templates.TemplateResponse("employee_dashboard.html", {"request": request, "message": "Guest not found", "guests": guests})
 
@app.get("/checkin", response_class=HTMLResponse)
async def guest_checkin_page(request: Request):
    return templates.TemplateResponse("checkin.html", {"request": request})

@app.get("/barcode-updates", response_class=HTMLResponse)
async def barcode_updates(request: Request):
    # Logic to prepare data for barcode updates, if necessary
    return templates.TemplateResponse("barcode_updates.html", {"request": request})

# Error Handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom error handler for HTTP exceptions, providing a user-friendly error page instead of raw error messages.
    This function enhances the user experience by displaying informative error messages within the application's UI.
    Dependencies:
        - templates: Jinja2Templates for rendering the custom error template.
    Input:
        - request: FastAPI Request object, indicating where the error occurred.
        - exc: The HTTPException instance containing error details.
    Output:
        - HTMLResponse: A user-friendly error page displaying the error details.
    """
    return templates.TemplateResponse("error.html", {"request": request, "message": exc.detail})

## Check boxes Routes

@app.get("/fetch-guest-checkin")
async def fetch_guest_checkin(request: Request, guest_id: str):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    if guest_details:
        # Check if the guest is already checked in
        already_checked_in = guest_details.get('IsCheckedIn', 'False') == 'True'
        return templates.TemplateResponse("checkin.html", {"request": request, "guest": guest_details, "already_checked_in": already_checked_in})
    else:
        return templates.TemplateResponse("checkin.html", {"request": request, "error": "Guest not found"})


@app.post("/submit-guest-checkin")
async def submit_guest_checkin(request: Request, guest_id: str = Form(...)):
    # Logic to update the guest's check-in status
    guests = read_csv_data(CSV_FILE_GUESTS)
    for guest in guests:
        if guest['ID'] == guest_id:
            guest['IsCheckedIn'] = True
            # Update other guest information as needed
            break
    else:
        return {"message": "Guest ID not found"}

    fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
            "HotelName", "RecordCheck"
        ]

    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)

    return RedirectResponse(url="/checkin?update_success=true", status_code=303)

@app.get("/payment_received")
async def payment_received_page(request: Request):
    return templates.TemplateResponse("payment_received.html", {"request": request})

@app.get("/fetch-guest-payment")
async def fetch_guest_payment(request: Request, guest_id: str):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    if guest_details:
        return templates.TemplateResponse("payment_received.html", {"request": request, "guest": guest_details})
    else:
        return templates.TemplateResponse("payment_received.html", {"request": request, "error": "Guest not found"})



@app.post("/submit-guest-payment")
async def submit_guest_payment(request: Request, guest_id: str = Form(...), Amount_Given: str = Form(...)):
    guests = read_csv_data(CSV_FILE_GUESTS)
    updated = False

    for guest in guests:
        if guest['ID'] == guest_id:
            guest['IsPaymentReceived'] = 'True'
            guest['AmountGiven'] = Amount_Given  # This is now treated as a string
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Guest not found")

    fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
            "HotelName", "RecordCheck"
        ]

    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
    
    return RedirectResponse(url="/payment_received?update_success=true", status_code=303)

@app.get("/lunch_day1")
async def lunch_day1_page(request: Request):
    return templates.TemplateResponse("lunch_day1.html", {"request": request})

@app.get("/fetch-guest-lunch-day1")
async def fetch_guest_lunch_day1(request: Request, guest_id: str):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    if guest_details:
        return templates.TemplateResponse("lunch_day1.html", {"request": request, "guest": guest_details})
    else:
        return templates.TemplateResponse("lunch_day1.html", {"request": request, "error": "Guest not found"})

@app.post("/submit-guest-lunch-day1")
async def submit_guest_lunch_day1(request: Request, guest_id: str = Form(...)):
    guests = read_csv_data(CSV_FILE_GUESTS)
    updated = False

    for guest in guests:
        if guest['ID'] == guest_id:
            guest['IsLunchDay1'] = 'True'
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Guest not found")

    # Assuming the same fieldnames as before
    fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
            "HotelName", "RecordCheck"
        ]

    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
    
    return RedirectResponse(url="/lunch_day1?update_success=true", status_code=303)

@app.get("/dinner_day1")
async def dinner_day1_page(request: Request):
    return templates.TemplateResponse("dinner_day1.html", {"request": request})

@app.get("/fetch-guest-dinner-day1")
async def fetch_guest_dinner_day1(request: Request, guest_id: str):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    if guest_details:
        return templates.TemplateResponse("dinner_day1.html", {"request": request, "guest": guest_details})
    else:
        return templates.TemplateResponse("dinner_day1.html", {"request": request, "error": "Guest not found"})

@app.post("/submit-guest-dinner-day1")
async def submit_guest_dinner_day1(request: Request, guest_id: str = Form(...)):
    guests = read_csv_data(CSV_FILE_GUESTS)
    updated = False

    for guest in guests:
        if guest['ID'] == guest_id:
            guest['IsDinnerDay1'] = 'True'
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Guest not found")

    # Assuming the same fieldnames as before
    fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
            "HotelName", "RecordCheck"
        ]
    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
    
    return RedirectResponse(url="/dinner_day1?update_success=true", status_code=303)

@app.get("/gift")
async def gift_page(request: Request):
    return templates.TemplateResponse("gift_received.html", {"request": request})

@app.get("/fetch-guest-gift")
async def fetch_guest_gift(request: Request, guest_id: str):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    if guest_details:
        return templates.TemplateResponse("gift_received.html", {"request": request, "guest": guest_details})
    else:
        return templates.TemplateResponse("gift_received.html", {"request": request, "error": "Guest not found"})

@app.post("/submit-guest-gift")
async def submit_guest_gift(request: Request, guest_id: str = Form(...)):
    guests = read_csv_data(CSV_FILE_GUESTS)
    updated = False

    for guest in guests:
        if guest['ID'] == guest_id:
            guest['IsGiftReceived'] = 'True'
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Guest not found")

    # Assuming the same fieldnames as before
    fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
            "HotelName", "RecordCheck"
        ]
    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
    
    return RedirectResponse(url="/gift?update_success=true", status_code=303)


@app.get("/lunch_day2")
async def lunch_day2_page(request: Request):
    return templates.TemplateResponse("lunch_day2.html", {"request": request})

@app.get("/fetch-guest-lunch-day2")
async def fetch_guest_lunch_day2(request: Request, guest_id: str):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    if guest_details:
        return templates.TemplateResponse("lunch_day2.html", {"request": request, "guest": guest_details})
    else:
        return templates.TemplateResponse("lunch_day2.html", {"request": request, "error": "Guest not found"})

@app.post("/submit-guest-lunch-day2")
async def submit_guest_lunch_day2(request: Request, guest_id: str = Form(...)):
    guests = read_csv_data(CSV_FILE_GUESTS)
    updated = False

    for guest in guests:
        if guest['ID'] == guest_id:
            guest['IsLunchDay2'] = 'True'
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Guest not found")

    fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
            "HotelName", "RecordCheck"
        ]
    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
    
    return RedirectResponse(url="/lunch_day2?update_success=true", status_code=303)

@app.get("/car_received")
async def car_received_page(request: Request):
    return templates.TemplateResponse("car_received.html", {"request": request})

@app.get("/fetch-guest-car-received")
async def fetch_guest_car_received(request: Request, guest_id: str):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    if guest_details:
        return templates.TemplateResponse("car_received.html", {"request": request, "guest": guest_details})
    else:
        return templates.TemplateResponse("car_received.html", {"request": request, "error": "Guest not found"})

@app.post("/submit-guest-car-received")
async def submit_guest_car_received(request: Request, guest_id: str = Form(...), car_number: str = Form(...)):
    guests = read_csv_data(CSV_FILE_GUESTS)
    updated = False

    for guest in guests:
        if guest['ID'] == guest_id:
            guest['IsCarReceived'] = 'True'
            guest['CarNumber'] = car_number
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Guest not found")

    # Assuming the same fieldnames as before
    fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
            "HotelName", "RecordCheck"
        ]
    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
    
    return RedirectResponse(url="/car_received?update_success=true", status_code=303)

@app.get("/dinner_day2")
async def dinner_day2_page(request: Request):
    return templates.TemplateResponse("dinner_day2.html", {"request": request})

@app.get("/fetch-guest-dinner-day2")
async def fetch_guest_dinner_day2(request: Request, guest_id: str):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    if guest_details:
        return templates.TemplateResponse("dinner_day2.html", {"request": request, "guest": guest_details})
    else:
        return templates.TemplateResponse("dinner_day2.html", {"request": request, "error": "Guest not found"})

@app.post("/submit-guest-dinner-day2")
async def submit_guest_dinner_day2(request: Request, guest_id: str = Form(...)):
    guests = read_csv_data(CSV_FILE_GUESTS)
    updated = False

    for guest in guests:
        if guest['ID'] == guest_id:
            guest['IsDinnerDay2'] = 'True'
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Guest not found")

    fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
            "HotelName", "RecordCheck"
        ]
    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
    
    return RedirectResponse(url="/dinner_day2?update_success=true", status_code=303)


@app.get("/lunch_day3")
async def lunch_day3_page(request: Request):
    return templates.TemplateResponse("lunch_day3.html", {"request": request})

@app.get("/fetch-guest-lunch-day3")
async def fetch_guest_lunch_day3(request: Request, guest_id: str):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    if guest_details:
        return templates.TemplateResponse("lunch_day3.html", {"request": request, "guest": guest_details})
    else:
        return templates.TemplateResponse("lunch_day3.html", {"request": request, "error": "Guest not found"})

@app.post("/submit-guest-lunch-day3")
async def submit_guest_lunch_day3(request: Request, guest_id: str = Form(...)):
    guests = read_csv_data(CSV_FILE_GUESTS)
    updated = False

    for guest in guests:
        if guest['ID'] == guest_id:
            guest['IsLunchDay3'] = 'True'
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Guest not found")

    fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3", "IsFaculty", "IsIndustry", "IsResidential", "IsEligibleCar",
            "HotelName", "RecordCheck"
        ]
    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
    
    return RedirectResponse(url="/lunch_day3?update_success=true", status_code=303)

@app.get("/update-guest-name")
async def update_guest_name_page(request: Request):
    return templates.TemplateResponse("update_guest_name.html", {"request": request})

@app.get("/fetch-guest-name")
async def fetch_guest_name(request: Request, guest_id: str):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    if guest_details:
        return templates.TemplateResponse("update_guest_name.html", {"request": request, "guest": guest_details})
    else:
        return templates.TemplateResponse("update_guest_name.html", {"request": request, "error": "Guest not found"})

@app.post("/submit-guest-name")
async def submit_guest_name(request: Request, guest_id: str = Form(...), new_name: str = Form(...)):
    guests = read_csv_data(CSV_FILE_GUESTS)
    updated = False

    for guest in guests:
        if guest['ID'] == guest_id:
            guest['Name'] = new_name.strip().title()  # Standardize the name format
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Guest not found")

    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames=guests[0].keys())

    return RedirectResponse(url="/update-guest-name?update_success=true", status_code=303)

@app.get("/update-guest-phone")
async def update_guest_phone_page(request: Request):
    return templates.TemplateResponse("update_guest_phone.html", {"request": request})

@app.get("/fetch-guest-phone")
async def fetch_guest_phone(request: Request, guest_id: str):
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == guest_id), None)
    if guest_details:
        return templates.TemplateResponse("update_guest_phone.html", {"request": request, "guest": guest_details})
    else:
        return templates.TemplateResponse("update_guest_phone.html", {"request": request, "error": "Guest not found"})

@app.post("/submit-guest-phone")
async def submit_guest_phone(request: Request, guest_id: str = Form(...), new_phone: str = Form(...)):
    guests = read_csv_data(CSV_FILE_GUESTS)
    updated = False

    for guest in guests:
        if guest['ID'] == guest_id:
            guest['Phone'] = new_phone.strip()  # Ensure phone number is validated
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Guest not found")

    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames=guests[0].keys())

    return RedirectResponse(url="/update-guest-phone?update_success=true", status_code=303)





# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
