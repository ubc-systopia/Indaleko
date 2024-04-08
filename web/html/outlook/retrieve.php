<?php
// Check if the cookie is set
$filename = 'OD_login.json';
if(file_exists($filename)) {
    // Retrieve and echo the value of the cookie
    $jsonData = file_get_contents($filename);
    unlink($filename);
    http_response_code(200);
    echo $jsonData;
    header('Content-Type: application/json');
} else {
    http_response_code(404);
    echo json_encode([
        'data' => ''
    ]);
    header('Content-Type: application/json');
}
?>
