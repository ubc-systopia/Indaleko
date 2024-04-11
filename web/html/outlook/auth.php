<?php
require 'vendor/autoload.php';
require_once('functions.php');
$envData = parseEnv('.env');

$client_id = $envData['CLIENT_ID'];
$redirect_uri = $envData['REDIRECT_URI'];
$grant_type = 'authorization_code';
$client_secret = $envData['CLIENT_SECRET'];

use GuzzleHttp\Client;

if(isset($_GET['token'])) {
  try {
    $filename = 'OD_login.json';
    file_put_contents($filename, json_encode([
      'od_token' => $_GET['token']
    ]));
  } catch(Exception $e) {
    echo $e->getMessage();
  }
  die();
}

// Retrieve the authorization code from GET parameter
$code = $_GET['code'];

// Retrieve the code verifier from the cookie
$code_verifier = $_GET['state'];



// Construct the token request
$url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token';
$request_body = [
    'form_params' => [
        'client_id' => $client_id,
        'redirect_uri' => $redirect_uri,
        'code' => $code,
        'grant_type' => $grant_type,
        'code_verifier' => $code_verifier,
        'client_secret' => $client_secret
    ]
];

try {
// Initialize Guzzle client
$client = new GuzzleHttp\Client();

// Send POST request using Guzzle
$response = $client->post($url, $request_body);

// Get response body
$response_data = json_decode($response->getBody(), true);

// Extract access token from response
$access_token = $response_data['access_token'];

header("location:https://activitycontext.work/outlook/auth.php?token=".$access_token."&view=".$_GET['view']);
} catch(Exception $e) {
  die($e);
}
?>
