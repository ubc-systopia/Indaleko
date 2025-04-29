<?php
// Receive JSON data from the add-in
$data = json_decode(file_get_contents('php://input'), true);

// Check if data is received
if (!empty($data)) {


    // Generate a unique filename based on current timestamp
    $filename = 'jsons/data_' . time() . '.json';

    // Save the data as JSON in the "jsons" folder
    file_put_contents($filename, json_encode($data));

    // Send response back to the add-in
    http_response_code(200);
    echo "Data saved successfully.";
} else {
    // Send error response if no data received
    http_response_code(400);
    echo "No data received.";
}
?>
