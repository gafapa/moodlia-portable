<?php
// Moodle must see the stable loopback proxy port, not a private PHP worker port.
// The proxy validates Host; never trust arbitrary forwarded host/protocol headers.
if (PHP_SAPI === 'cli-server') {
    $requestsettings = json_decode(file_get_contents(getenv('MOODLIA_PRIVATE_CONFIG')), true, 512, JSON_THROW_ON_ERROR);
    $_SERVER['SERVER_PORT'] = (string)$requestsettings['http_port'];
    $_SERVER['HTTP_HOST'] = '127.0.0.1:' . $requestsettings['http_port'];
    $_SERVER['SERVER_NAME'] = '127.0.0.1';
    if (rawurldecode(parse_url($_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH) ?? '') === '/local/moodlia/mcp.php') {
        // This request's HTTP client may reach only this app's loopback port.
        // REST tool execution runs in other workers with Moodle's normal HTTP restrictions.
        $CFG->curlsecurityallowedport = (string)$requestsettings['http_port'];
        $CFG->curlsecurityblockedhosts = file_get_contents(__DIR__ . '/mcp-blocked-hosts.txt');
    }
}
