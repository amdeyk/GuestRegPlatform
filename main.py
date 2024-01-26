from datetime import datetime
from fastapi import FastAPI, Request, Form, HTTPException, Response, Query
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
from pydantic import BaseModel
from typing import Optional
import codecs
import json
from urllib.parse import parse_qs



class UpdateGuestInfo(BaseModel):
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

class GuestUpdate(BaseModel):
    guestId: str
    updateType: str
    
# Read config.ini file
config = configparser.ConfigParser()
config.read('config.ini')

# Accessing the values from config.ini
admin_password = config['DEFAULT']['AdminPassword']
software_version = config['DEFAULT']['SoftwareVersion']



app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/static/style.css")
async def get_css():
    response = Response(content=await app.get("/static/style.css"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"  # Prevent caching
    return response

# CSV file paths
CSV_FILE_GUESTS = "./data/guests.csv"

# Utility Functions
def read_csv_data(file_path):
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
    backup_1_path = file_path + "_backup_1.csv"
    backup_2_path = file_path + "_backup_2.csv"

    # Create a backup of the current CSV file
    if os.path.exists(file_path):
        if os.path.exists(backup_1_path):
            # Move existing backup_1 to backup_2
            shutil.copy(backup_1_path, backup_2_path)
        # Move existing main file to backup_1
        shutil.copy(file_path, backup_1_path)
        
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        # Update fieldnames to include all necessary fields
        fieldnames = [
            "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
            "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
            "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
            "IsLunchDay3"
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

def write_csv_data_update(file_path, data, fieldnames):
    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
    except Exception as e:
        print(f"Error writing CSV data: {e}")



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
        writer = csv.DictWriter(file, fieldnames=["ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven"])
        writer.writeheader()


@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/guest_registration", response_class=HTMLResponse)
async def guest_registration(request: Request):
    return templates.TemplateResponse("guest_registration.html", {"request": request})

# POST route for guest registration
@app.post("/submit-guest-registration", response_class=HTMLResponse)
async def submit_guest_registration(request: Request, name: str = Form(...), email: str = Form(...), 
                                     phone: str = Form(...), check_in: str = Form(...), 
                                     check_out: str = Form(...), amount_given: float = Form(0.0)):
    # Check if the phone number is at least 10 digits long
    if len(phone) < 10:
        return templates.TemplateResponse("guest_registration.html", {"request": request, "message": "Phone number must be at least 10 digits long"})

    # Validate email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return templates.TemplateResponse("guest_registration.html", {"request": request, "message": "Invalid email format"})

    # Check-out date later than check-in date
    check_in_date = datetime.fromisoformat(check_in)
    check_out_date = datetime.fromisoformat(check_out)
    if check_out_date <= check_in_date:
        return templates.TemplateResponse("guest_registration.html", {"request": request, "message": "Check-out date must be later than check-in date"})

    # Prevent re-registration with the same phone number
    guests = read_csv_data(CSV_FILE_GUESTS)
    if any(guest['Phone'] == phone for guest in guests):
        return templates.TemplateResponse("guest_registration.html", {"request": request, "message": "This phone number has already been registered"})

    # Create a dictionary for the new guest
    guest_id = name[:2] + phone if len(name) >= 2 else name + phone
    new_guest = {
        "ID": guest_id,
        "Name": name,
        "Email": email,
        "Phone": phone,
        "CheckIn": check_in,
        "CheckOut": check_out,
        "AmountGiven": amount_given
    }

    guests.append(new_guest)
    fieldnames = ["ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven"]
    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)

    return templates.TemplateResponse("guest_registration.html", {"request": request, "message": "Guest registered successfully"})

@app.get("/admin_dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    # Fetch user list from the database
    users = read_csv_data(CSV_FILE_GUESTS)  # Modify as needed to fit your data fetching logic
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": users})

@app.get("/employee_dashboard", response_class=HTMLResponse)
async def employee_dashboard(request: Request):
    guests = read_csv_data(CSV_FILE_GUESTS)
    return templates.TemplateResponse("employee_dashboard.html", {"request": request, "guests": guests})


@app.post("/update-guest-info")
async def update_guest_info(request: Request):
    body = await request.body()
    body_str = body.decode('utf-8')
    print(body_str)  # For debugging

    # Parse the URL-encoded body
    data = parse_qs(body_str)

    # Convert the values from lists to single values
    data = {k: v[0] if len(v) == 1 else v for k, v in data.items()}
    print(data)
    # Convert string "on" to boolean True for checkboxes
    for key in ['isCheckedIn', 'isPaymentReceived', 'isGiftReceived', 'isCarReceived', 'isLunchDay1', 'isDinnerDay1', 'isLunchDay2', 'isDinnerDay2', 'isLunchDay3']:
        data[key] = data.get(key, '') == 'on'

    # Your logic to update the guest information
    guests = read_csv_data(CSV_FILE_GUESTS)

    for guest in guests:
        if guest['ID'] == data['guest_id']:
            guest['IsCheckedIn'] = data['isCheckedIn']
            guest['IsPaymentReceived'] = data['isPaymentReceived']
            guest['IsGiftReceived'] = data['isGiftReceived']
            guest['IsCarReceived'] = data['isCarReceived']
            guest['CarNumber'] = data['carNumber'] if data['isCarReceived'] else ""
            guest['IsLunchDay1'] = data['isLunchDay1']
            guest['IsDinnerDay1'] = data['isDinnerDay1']
            guest['IsLunchDay2'] = data['isLunchDay2']
            guest['IsDinnerDay2'] = data['isDinnerDay2']
            guest['IsLunchDay3'] = data['isLunchDay3']
            # Add any additional fields you need to update
            break
    else:
        return {"message": "Guest ID not found"}
    
    fieldnames = [
        "ID", "Name", "Email", "Phone", "CheckIn", "CheckOut", "AmountGiven",
        "IsCheckedIn", "IsPaymentReceived", "IsGiftReceived", "IsCarReceived", 
        "CarNumber", "IsLunchDay1", "IsDinnerDay1", "IsLunchDay2", "IsDinnerDay2", 
        "IsLunchDay3"
    ]
    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
    return RedirectResponse(url="/employee_dashboard?update_success=true", status_code=303)

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

@app.get("/report", response_class=HTMLResponse)
async def report(request: Request):
    return templates.TemplateResponse("report.html", {"request": request})

@app.get("/fetch-guest-details-by-barcode")
async def fetch_guest_details_by_barcode(barcode: str):
    print(barcode)
    guests = read_csv_data(CSV_FILE_GUESTS)
    guest_details = next((guest for guest in guests if guest['ID'] == barcode), None)

    if guest_details:
        return guest_details  # Ensure this returns JSON
    else:
        return {"error": "Guest not found"}, 404  # Returning a JSON response with error message

@app.post("/generate-report", response_class=HTMLResponse)
async def generate_report(request: Request, report_type: str = Form(...)):
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
async def generate_barcode(request: Response, user_id: str = Form(...)):
    barcode_io = io.BytesIO()
    Code128(user_id, writer=ImageWriter()).write(barcode_io)
    barcode_io.seek(0)
    headers = {
        'Content-Disposition': f'attachment; filename={user_id}.png'
    }
    return StreamingResponse(barcode_io, media_type="image/png", headers=headers)

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
                fieldnames = ['ID', 'Name', 'Email', 'Phone', 'CheckIn', 'CheckOut', 'AmountGiven', 'IsCheckedIn', 'IsPaymentReceived', 
                              'IsGiftReceived', 'IsCarReceived', 'CarNumber', 'IsLunchDay1', 'IsDinnerDay1', 'IsLunchDay2', 'IsDinnerDay2', 'IsLunchDay3']
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
        "IsLunchDay3"
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
        "IsLunchDay3"
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
        "IsLunchDay3"
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
        "IsLunchDay3"
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
        "IsLunchDay3"
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
        "IsLunchDay3"
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
        "IsLunchDay3"
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
        "IsLunchDay3"
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
        # ... include all the necessary fields ...
        "IsLunchDay3",
        # ... other fields ...
    ]
    write_csv_data(CSV_FILE_GUESTS, guests, fieldnames)
    
    return RedirectResponse(url="/lunch_day3?update_success=true", status_code=303)






# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
