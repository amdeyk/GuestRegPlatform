let currentGuestId = null;

function displayGuestDetails(guest, containerId) {
    console.log("Container ID: ", containerId); // Log the container ID

    var guestDetailsSection = document.getElementById(containerId);
    console.log("Element found: ", guestDetailsSection); // Log the element

    if (guestDetailsSection === null) {
        console.error("Element not found in the DOM");
        return; // Exit the function if the element is not found
    }
    guestDetailsSection.innerHTML = `
        <div class="card">
            <div class="card-header">Guest Information</div>
            <ul class="list-group list-group-flush">
                <li class="list-group-item"><strong>ID:</strong> ${guest.ID}</li>
                <li class="list-group-item"><strong>Name:</strong> ${guest.Name}</li>
                <li class="list-group-item"><strong>Email:</strong> ${guest.Email}</li>
                <li class="list-group-item"><strong>Phone:</strong> ${guest.Phone}</li>
                <li class="list-group-item"><strong>Check-In:</strong> ${guest.CheckIn}</li>
                <li class="list-group-item"><strong>Check-Out:</strong> ${guest.CheckOut}</li>
                <!-- Additional guest details -->
            </ul>
        </div>
    `;

    guestDetailsSection.style.display = 'block';
    currentGuestId = guest.ID; // Store the current guest ID
}

function startScanning(containerId) {
    Quagga.init({
        inputStream: {
            name: "Live",
            type: "LiveStream",
            target: document.querySelector('#scanner-container'), 
            constraints: {
                width: 570 ,
                height: 480 ,
                facingMode: "environment", // Change to "user" for front camera
                aspectRatio: { min: 1, max: 9 }
            }
        },
        locator: {
            patchSize: "medium", // Try different sizes here
            halfSample: false // Set to true for faster processing but potentially less accuracy
        },
        numOfWorkers: navigator.hardwareConcurrency,
        decoder: {
            readers: ["code_128_reader"] // Add or remove readers based on your needs
        },
        locate: true
    }, function(err) {
        if (err) {
            console.error(err);
            return;
        }
        Quagga.start();
    });

    Quagga.onDetected(function(data) {
        Quagga.stop();
        const barcode = data.codeResult.code;

        fetch(`/fetch-guest-details-by-barcode?barcode=${barcode}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('No guest found for this barcode');
                }
                return response.json();
            })
            .then(guest => {
                displayGuestDetails(guest, containerId);
            })
            .catch(error => {
                console.error('Error fetching guest details:', error);
                // Update UI to display error
            });
    });
}

// Function to update guest information
// Function to update guest information
function updateGuestInfo(updateType) {
    if (!currentGuestId) {
        alert('Please scan a guest barcode first.');
        return;
    }

    const updateData = {
        guestId: currentGuestId,
        updateType: updateType
    };

    fetch('/update-guest-info-scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(updateData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to update guest information');
        }
        return response.json();
    })
    .then(data => {
        // Set the message in the modal
        document.querySelector('#alertModal .modal-body').textContent = data.message;
    
        // Display the modal
        $('#alertModal').modal('show');
    })
    .then(data => {
        alert('Guest information updated successfully.');
        // Handle successful response (e.g., update UI)
    })
    .catch(error => {
        console.error('Error updating guest information:', error);
        // Handle error (e.g., show error message)
    });
}


// Event listeners for update buttons
document.addEventListener('DOMContentLoaded', function() {
    ['paymentUpdateButton', 'checkinUpdateButton', 'giftUpdateButton', 'lunchDay1Button', 'dinnerDay1Button', 'lunchDay2Button', 'dinnerDay2Button', 'lunchDay3Button'/* Add other buttons as needed */].forEach(buttonId => {
        const button = document.getElementById(buttonId);
        if (button) {
            button.addEventListener('click', function() {
                updateGuestInfo(buttonId);
            });
        }
    });

    // Initialize barcode scanning
    if (document.getElementById('startScan')) {
        document.getElementById('startScan').addEventListener('click', function() {
            startScanning('scanned-guest-details');
        });
    }
});
