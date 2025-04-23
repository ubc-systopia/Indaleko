
<?php
require_once('functions.php');
$envData = parseEnv('.env');

$client_id = $envData['CLIENT_ID'];
$redirect_uri = $envData['REDIRECT_URI'];
$grant_type = 'authorization_code';
$client_secret = $envData['CLIENT_SECRET'];

$params = [
    'client_id' => $client_id,
    'response_type' => 'code',
    'redirect_uri' => $redirect_uri,
    'scope' => 'Files.Read',
    'code_challenge_method' => 'S256',
    'code_challenge' => $_GET['code_challenge'],
    'state' => $_GET['code_verifier']
];

$loginUrl = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize';

$finalUrl = $loginUrl . '?' . http_build_query($params);
header("location:".$finalUrl);
die;
?>
