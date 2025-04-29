<?php
require 'vendor/autoload.php';

use GuzzleHttp\Client;

function expandOneDriveUrl($shortenedUrl) {
    try {
        // Send a HEAD request to the shortened URL
        $headers = get_headers($shortenedUrl, 1);

        // Check if the Location header exists
        if (isset($headers['Location'])) {
            // Extract the expanded URL from the Location header
            $expandedUrl = is_array($headers['Location']) ? end($headers['Location']) : $headers['Location'];
            $expandedUrl = 'https://onedrive.live.com' . $expandedUrl;
            $queryString = parse_url($expandedUrl, PHP_URL_QUERY);
            parse_str($queryString, $queryParams);
            return $queryParams;
        } else {
            throw new Exception('Location header not found in response');
        }
    } catch (Exception $e) {
        // Handle any errors
        echo 'Error expanding OneDrive URL: ' . $e->getMessage();
        return null;
    }
}

function fetchOneDriveMetadata($itemId, $accessToken) {
    $client = new GuzzleHttp\Client();

    try {
        $response = $client->request('GET', "https://graph.microsoft.com/v1.0/me/drive/items/$itemId", [
            'headers' => [
                'Authorization' => "Bearer $accessToken"
            ]
        ]);

        $data = json_decode($response->getBody(), true);
        return $data;
    } catch (Exception $e) {
        return ['error' => $e->getMessage()];
    }
}

// Example usage
$shortenedUrl = $_GET['link'];
$expandedUrlData = expandOneDriveUrl($shortenedUrl);
$token = $_GET['token'];

$data = fetchOneDriveMetadata($expandedUrlData['id'], $token);
http_response_code(200);
header('Content-Type: application/json');
echo json_encode([
    'fileName' => $data['name'],
    'attachmentClass' => 'onedrive',
    'metas' => $data
]);
die();
