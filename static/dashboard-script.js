// Function to display the modal with a message
function showModal(message) {
    $('#responseModal .modal-body').text(message);
    $('#responseModal').modal('show');
}

document.getElementById('fetchGuestForm').addEventListener('submit', function(event) {
    event.preventDefault();
    var guestId = document.getElementById('guestId').value;

    fetch(`/fetch-guest-details-employee?guest_id=${guestId}`)
        .then(response => response.json())
        .then(data => {
            if (data.guest) {
                document.getElementById('guestIdInput').value = data.guest.ID;

                // Update checkbox statuses based on guest data
                document.getElementById('checkinCheckbox').checked = data.guest.IsCheckedIn === 'True';
                document.getElementById('paymentCheckbox').checked = data.guest.IsPaymentReceived === 'True';
                document.getElementById('giftCheckbox').checked = data.guest.IsGiftReceived === 'True';
                document.getElementById('lunchDay1Checkbox').checked = data.guest.IsLunchDay1 === 'True';
                document.getElementById('dinnerDay1Checkbox').checked = data.guest.IsDinnerDay1 === 'True';
                document.getElementById('lunchDay2Checkbox').checked = data.guest.IsLunchDay2 === 'True';
                document.getElementById('dinnerDay2Checkbox').checked = data.guest.IsDinnerDay2 === 'True';
                document.getElementById('lunchDay3Checkbox').checked = data.guest.IsLunchDay3 === 'True';
                // Add more checkboxes as necessary
            } else {
                showModal('Guest details not found.');
            }
            })
        .catch(error => {
            console.error('Error:', error);
            showModal('An error occurred while fetching guest details.');
        });
});

document.addEventListener('DOMContentLoaded', function() {
    var updateForm = document.getElementById('updateGuestForm');
    if (updateForm) {
        updateForm.addEventListener('submit', function(event) {
            event.preventDefault();

            var formData = new FormData(this);
            var object = {
                guest_id: formData.get('guest_id'), // Assuming 'guest_id' is the name attribute in your form
                isCheckedIn: formData.get('isCheckedIn') === 'on',
                isPaymentReceived: formData.get('isPaymentReceived') === 'on',
                isGiftReceived: formData.get('isGiftReceived') === 'on',
                isCarReceived: formData.get('isCarReceived') === 'on',
                carNumber: formData.get('carNumber'), // Assuming you have a field for the car number
                isLunchDay1: formData.get('isLunchDay1') === 'on',
                isDinnerDay1: formData.get('isDinnerDay1') === 'on',
                isLunchDay2: formData.get('isLunchDay2') === 'on',
                isDinnerDay2: formData.get('isDinnerDay2') === 'on',
                isLunchDay3: formData.get('isLunchDay3') === 'on',
                // Add additional fields if your form has more
            };

            fetch('/update-guest-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(object)
            })
            .then(response => response.json())
            .then(data => {
                showModal(data.message);
            })
            .catch(error => {
                console.error('Error:', error);
                showModal('An error occurred while updating guest information.');
            });
        });
    }
});


