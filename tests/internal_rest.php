<?php
// Diagnose only this synthetic local site's internal HTTP path; redact its token.
define('CLI_SCRIPT', true);
require($argv[1] . '/config.php');
$token = trim(file_get_contents(dirname(getenv('MOODLIA_PRIVATE_CONFIG'), 2) . '/connection/token.txt'));
try {
    $client = new \core\http_client(['timeout' => 10]);
    $response = $client->post($CFG->wwwroot . '/webservice/rest/server.php', ['form_params' => [
        'wstoken' => $token, 'wsfunction' => 'local_moodlia_get_current_user', 'moodlewsrestformat' => 'json']]);
    echo 'Internal status: ' . $response->getStatusCode() . "\n";
} catch (Throwable $error) {
    echo str_replace($token, '[redacted]', $error->getMessage()) . "\n";
    exit(1);
}
