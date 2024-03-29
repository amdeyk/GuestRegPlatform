<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Employee Dashboard</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css">
    <style>
        /* Larger checkboxes */
        .form-check {
            padding: 10px; /* Adjust the padding size as needed */
            margin-bottom: 5px; /* Optional: Adds space between checkboxes */
            border: 1px solid #ddd; /* Optional: Adds a border around each checkbox */
            border-radius: 5px; /* Optional: Rounds the corners of the border */
            background-color: #f8f8f8; /* Optional: Adds background color */
        }
        .large-checkbox .form-check-input {
            width: 20px;  /* Adjust size as needed */
            height: 20px; /* Adjust size as needed */
            right: 15px
            cursor: pointer;
        }
    
        /* Styling for disabled checkboxes */
        .large-checkbox .form-check-input:disabled {
            border-color: red;
            background-color: lightgray;
            cursor: not-allowed;
        }
    
        .large-checkbox .form-check-input:disabled + .form-check-label {
            color: red;
            padding: 5px; /* Adjust the padding size as needed */
            font-size: larger; /* Adjust size as needed */
        }
    </style>

</head>
<body>
    <header class="bg-dark text-white py-3">
        <div class="container text-center">
            <h1>Employee Dashboard</h1>
        </div>
    </header>

    <nav class="navbar navbar-expand-lg navbar-dark bg-primary justify-content-center">
        <div class="container">
            <ul class="navbar-nav">
                <li class="nav-item"><a class="nav-link" href="/guest_registration">Guest Registration</a></li>
                <li class="nav-item"><a class="nav-link" href="/admin_dashboard">Admin Dashboard</a></li>
                <li class="nav-item"><a class="nav-link" href="/employee_dashboard">Employee Dashboard</a></li>
                <li class="nav-item"><a class="nav-link" href="/view_guest">View Guest</a></li>
                <li class="nav-item"><a class="nav-link" href="/report">Generate Report</a></li>
            </ul>
        </div>
    </nav>

    <div class="container mt-4">
        <h2 class="text-center mb-4">Guest Management</h2>
        
        <!-- Form for Guest ID Input -->
        <form action="/fetch-guest" method="get">
            <div class="form-group">
                <label for="guestIdInput">Enter Guest ID:</label>
                <input type="text" class="form-control" id="guestIdInput" name="guest_id" required>
            </div>
            <button type="submit" class="btn btn-primary">Fetch Guest Details</button>
        </form>
        
        <!-- Display Update Confirmation -->
        {% if request.query_params.get("update_success") %}
            <div class="alert alert-success mt-4">
                Record Updated Successfully
            </div>
        {% endif %}
        
        <!-- Display Guest Details for Update -->
        {% if guest %}
            <div class="card mb-4">
            <div class="card-header">Update Guest Information</div>
            <div class="card-body">
                <form action="/update-guest-info" method="post">
                    <input type="hidden" name="guest_id" value="{{ guest.ID }}">
        
                   <div class="form-group">
                        <label for="guestName">Guest Name:</label>
                        <input type="text" class="form-control" id="guestName" name="guest_name" value="{{ guest.Name }}" readonly>
                    </div>
                    
                    <!-- Guest Phone (Read-only) -->
                    <div class="form-group">
                        <label for="guestPhone">Guest Phone:</label>
                        <input type="tel" class="form-control" id="guestPhone" name="guest_phone" value="{{ guest.Phone }}" readonly>
                    </div>
        
                    <!-- Check-in Checkbox -->
                    <div class="container">
                    <div class="row">
                        <!-- Column 1 -->
                        <div class="col">
                            <!-- Check-in Checkbox -->
                            <div class="form-check large-checkbox">
                                <input type="checkbox" class="form-check-input" id="checkinCheckbox" name="isCheckedIn" {% if guest.IsCheckedIn == "True" %} checked disabled {% endif %}>
                                <label class="form-check-label" for="checkinCheckbox">Check-in Guest</label>
                            </div>
                
                            <!-- Payment Received Checkbox -->
                            <div class="form-check large-checkbox">
                                <input type="checkbox" class="form-check-input" id="paymentCheckbox" name="isPaymentReceived" {% if guest.IsPaymentReceived == "True" %} checked disabled {% endif %}>
                                <label class="form-check-label" for="paymentCheckbox">Payment Received</label>
                            </div>
                
                            <!-- Meal Coupons Day 1 - Lunch -->
                            <div class="form-check large-checkbox">
                                <input type="checkbox" class="form-check-input" id="lunchDay1Checkbox" name="isLunchDay1" {% if guest.IsLunchDay1 == "True" %} checked disabled {% endif %}>
                                <label class="form-check-label" for="lunchDay1Checkbox">Lunch Coupon Day 1 Given</label>
                            </div>
                
                            <!-- Meal Coupons Day 2 - Lunch -->
                            <div class="form-check large-checkbox">
                                <input type="checkbox" class="form-check-input" id="lunchDay2Checkbox" name="isLunchDay2" {% if guest.IsLunchDay2 == "True" %} checked disabled {% endif %}>
                                <label class="form-check-label" for="lunchDay2Checkbox">Lunch Coupon Day 2 Given</label>
                            </div>
                        </div>
                
                        <!-- Column 2 -->
                        <div class="col">
                            <!-- Gift Received Checkbox -->
                            <div class="form-check large-checkbox">
                                <input type="checkbox" class="form-check-input" id="giftCheckbox" name="isGiftReceived" {% if guest.IsGiftReceived == "True" %} checked disabled {% endif %}>
                                <label class="form-check-label" for="giftCheckbox">Gift Received</label>
                            </div>
                
                            <!-- Car Received Checkbox -->
                            <div class="form-check large-checkbox">
                                <input type="checkbox" class="form-check-input" id="carReceivedCheckbox" name="isCarReceived" {% if guest.IsCarReceived == "True" %} checked disabled {% endif %}>
                                <label class="form-check-label" for="carReceivedCheckbox">Car Received</label>
                            </div>
                
                            <!-- Meal Coupons Day 1 - Dinner -->
                            <div class="form-check large-checkbox">
                                <input type="checkbox" class="form-check-input" id="dinnerDay1Checkbox" name="isDinnerDay1" {% if guest.IsDinnerDay1 == "True" %} checked disabled {% endif %}>
                                <label class="form-check-label" for="dinnerDay1Checkbox">Dinner Coupon Day 1 Given</label>
                            </div>
                
                            <!-- Meal Coupons Day 2 - Dinner -->
                            <div class="form-check large-checkbox">
                                <input type="checkbox" class="form-check-input" id="dinnerDay2Checkbox" name="isDinnerDay2" {% if guest.IsDinnerDay2 == "True" %} checked disabled {% endif %}>
                                <label class="form-check-label" for="dinnerDay2Checkbox">Dinner Coupon Day 2 Given</label>
                            </div>
                
                            <!-- Meal Coupons Day 3 - Lunch -->
                            <div class="form-check large-checkbox">
                                <input type="checkbox" class="form-check-input" id="lunchDay3Checkbox" name="isLunchDay3" {% if guest.IsLunchDay3 == "True" %} checked disabled {% endif %}>
                                <label class="form-check-label" for="lunchDay3Checkbox">Lunch Coupon Day 3 Given</label>
                            </div>
                        </div>
                    </div>
                </div>


        
                    <div class="mt-4 text-center">
                        <button type="submit" class="btn btn-primary">Update Guest Information</button>
                    </div>
                </form>
            </div>
        </div>
        {% elif request.query_params.get("guest_id") %}
            <div class="alert alert-danger mt-4">
                    Guest ID not found.
                </div>
            {% endif %}
        </div>

                        
        
    <div style="height: 3rem;"></div> <!-- Adjust the height as needed -->
    </div>
    <!-- New Button for Barcode Updates -->
    <div class="text-center mt-4">
        <button onclick="location.href='/barcode-updates'" class="btn btn-info">Barcode Scanning & Updates</button>
    </div>
    </div>
    <footer>
        <button onclick="location.href='/'">Back to Home</button>
        <button onclick="location.href='login.html'">Login Page</button>
        <button>Help: +91-9899339005</button>
    </footer>
    <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js"></script>
</body>
</html>
